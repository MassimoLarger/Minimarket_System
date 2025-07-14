from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import JsonResponse
from django.db import transaction, IntegrityError
from django.contrib.auth import authenticate
from django.utils import timezone
from ..models import Reporte, ReporteProducto, Producto
from datetime import datetime

def is_superuser(user):
    return user.is_superuser

@login_required
def verify_password_reports(request):
    if not request.user.is_superuser:
        messages.error(request, 'No tienes permiso para acceder a esta sección.')
        return redirect('home')
    
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        
        user = authenticate(request, username=username, password=password)
        if user is not None and user.is_superuser:
            request.session['reports_access_granted'] = True
            messages.success(request, 'Acceso concedido a la gestión de reportes.')
            return redirect('gestionar_reportes')
        else:
            messages.error(request, 'Contraseña incorrecta.')
    
    return redirect('home')

@login_required
@user_passes_test(lambda u: u.is_superuser, login_url='home')
def gestionar_reportes(request):
    if not request.session.get('reports_access_granted', False):
        messages.warning(request, 'Debes verificar tu contraseña para acceder a la gestión de reportes.')
        return redirect('home')
    
    reportes = Reporte.objects.all().order_by('-fecha_creacion')
    productos = Producto.objects.all().order_by('nombre')
    
    # Manejar peticiones GET para obtener datos del reporte
    if request.method == 'GET':
        action = request.GET.get('action')
        if action == 'get':
            try:
                reporte_id = request.GET.get('id')
                reporte = get_object_or_404(Reporte, id=reporte_id)
                productos_reporte = reporte.productos_reporte.all()
                
                productos_data = []
                for rp in productos_reporte:
                    productos_data.append({
                        'id': rp.producto.id,
                        'producto_id': rp.producto.id,
                        'producto_nombre': rp.producto.nombre,
                        'nombre': rp.producto.nombre,
                        'cantidad': rp.cantidad if rp.cantidad is not None else '',
                        'observaciones': rp.observaciones or ''
                    })
                
                return JsonResponse({
                    'success': True,
                    'reporte': {
                        'id': reporte.id,
                        'nombre': reporte.nombre_reporte,
                        'descripcion': reporte.descripcion,
                        'tipo': reporte.tipo,
                        'fecha_creacion': reporte.fecha_creacion.strftime('%d/%m/%Y %H:%M'),
                        'usuario_creador': reporte.usuario_creador.username,
                        'activo': reporte.activo
                    },
                    'productos': productos_data
                })
            except Exception as e:
                return JsonResponse({
                    'success': False,
                    'message': f'Error al obtener el reporte: {str(e)}'
                })
    
    if request.method == 'POST':
        is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
        
        # Manejar datos JSON para AJAX
        if is_ajax and request.content_type == 'application/json':
            import json
            data = json.loads(request.body)
            action = data.get('action', 'crear_reporte')
        else:
            data = request.POST
            action = data.get('action')
        
        if action == 'crear_reporte' or (is_ajax and not action):
            try:
                with transaction.atomic():
                    nombre_reporte = data.get('nombre_reporte', '').strip()
                    descripcion = data.get('descripcion', '').strip()
                    tipo = data.get('tipo')
                    
                    # Validaciones específicas
                    if not nombre_reporte:
                        raise ValueError('El nombre del reporte no puede estar vacío o solo contener espacios.')
                    if not descripcion:
                        raise ValueError('La descripción del reporte es obligatoria.')
                    if not tipo:
                        raise ValueError('Debe seleccionar un tipo de reporte.')
                    
                    # La validación de unicidad se manejará con IntegrityError
                    
                    # Crear el reporte
                    reporte = Reporte.objects.create(
                        nombre_reporte=nombre_reporte,
                        descripcion=descripcion,
                        tipo=tipo,
                        usuario_creador=request.user
                    )
                    
                    # Agregar productos si se especificaron
                    if is_ajax and request.content_type == 'application/json':
                        # Para datos JSON de AJAX
                        productos_data = data.get('productos', [])
                        if not productos_data:
                            # Compatibilidad con formato anterior
                            producto_id = data.get('producto_id')
                            cantidad = data.get('cantidad')
                            if producto_id:
                                productos_data = [{'producto_id': producto_id, 'cantidad': cantidad, 'observaciones': ''}]
                        
                        # Validar que se hayan seleccionado productos para reportes que los requieren
                        if tipo in ['producto', 'perdida'] and not productos_data:
                            raise ValueError('Debe seleccionar al menos un producto para este tipo de reporte.')
                        
                        # Validar productos duplicados
                        productos_ids = [p.get('producto_id') for p in productos_data if p.get('producto_id')]
                        if len(productos_ids) != len(set(productos_ids)):
                            raise ValueError('No puede agregar el mismo producto múltiples veces.')
                        
                        for producto_data in productos_data:
                            producto_id = producto_data.get('producto_id')
                            if producto_id:
                                try:
                                    producto = Producto.objects.get(id=producto_id)
                                except Producto.DoesNotExist:
                                    raise ValueError(f'El producto con ID {producto_id} no existe.')
                                    
                                cantidad = producto_data.get('cantidad', '')
                                observaciones = producto_data.get('observaciones', '')
                                
                                # Validar cantidad según el tipo de reporte
                                if tipo == 'perdida':
                                    if not cantidad or cantidad == '':
                                        raise ValueError('La cantidad es obligatoria para reportes de pérdida.')
                                    try:
                                        cantidad_final = int(cantidad)
                                    except ValueError:
                                        raise ValueError('La cantidad debe ser un número válido.')
                                    if cantidad_final <= 0:
                                        raise ValueError('La cantidad debe ser mayor a 0.')
                                elif tipo == 'producto':
                                    # Para reportes de producto, la cantidad es obligatoria
                                    if not cantidad or cantidad == '':
                                        raise ValueError('La cantidad es obligatoria para reportes de producto.')
                                    try:
                                        cantidad_final = int(cantidad)
                                    except ValueError:
                                        raise ValueError('La cantidad debe ser un número válido.')
                                    if cantidad_final <= 0:
                                        raise ValueError('La cantidad debe ser mayor a 0.')
                                else:
                                    # Para tipos inventario y ventas, la cantidad es opcional
                                    try:
                                        cantidad_final = int(cantidad) if cantidad and cantidad != '' else None
                                    except ValueError:
                                        raise ValueError('La cantidad debe ser un número válido.')
                                
                                ReporteProducto.objects.create(
                                    reporte=reporte,
                                    producto=producto,
                                    cantidad=cantidad_final,
                                    observaciones=observaciones or 'N/A'
                                )
                    else:
                        # Para datos de formulario tradicional
                        productos_ids = data.getlist('productos[]')
                        cantidades = data.getlist('cantidades[]')
                        observaciones_list = data.getlist('observaciones[]')
                        
                        # Validar que se hayan seleccionado productos para reportes que los requieren
                        if tipo in ['producto', 'perdida'] and not any(productos_ids):
                            raise ValueError('Debe seleccionar al menos un producto para este tipo de reporte.')
                        
                        for i, producto_id in enumerate(productos_ids):
                            if producto_id:
                                producto = Producto.objects.get(id=producto_id)
                                cantidad = cantidades[i] if i < len(cantidades) else ''
                                observaciones = observaciones_list[i] if i < len(observaciones_list) else ''
                                
                                # Validar cantidad según el tipo de reporte
                                if tipo == 'perdida':
                                    if not cantidad or cantidad == '':
                                        raise ValueError('La cantidad es obligatoria para reportes de pérdida.')
                                    cantidad_final = int(cantidad)
                                    if cantidad_final <= 0:
                                        raise ValueError('La cantidad debe ser mayor a 0.')
                                elif tipo == 'producto':
                                    # Para reportes de producto, la cantidad es obligatoria
                                    if not cantidad or cantidad == '':
                                        raise ValueError('La cantidad es obligatoria para reportes de producto.')
                                    cantidad_final = int(cantidad)
                                    if cantidad_final <= 0:
                                        raise ValueError('La cantidad debe ser mayor a 0.')
                                else:
                                    # Para tipos inventario y ventas, la cantidad es opcional
                                    try:
                                        cantidad_final = int(cantidad) if cantidad and cantidad != '' else None
                                    except ValueError:
                                        raise ValueError('La cantidad debe ser un número válido.')
                                
                                ReporteProducto.objects.create(
                                    reporte=reporte,
                                    producto=producto,
                                    cantidad=cantidad_final,
                                    observaciones=observaciones or 'N/A'
                                )
                    
                    if is_ajax:
                        return JsonResponse({
                            'success': True,
                            'message': f'Reporte "{nombre_reporte}" creado exitosamente.'
                        })
                    else:
                        messages.success(request, f'Reporte "{nombre_reporte}" creado exitosamente.')
                        
            except IntegrityError as e:
                error_message = str(e)
                if 'UNIQUE constraint failed' in error_message and 'nombre_reporte' in error_message:
                    custom_message = 'Ya existe un reporte con este nombre. Por favor, ingrese un nombre diferente.'
                    if is_ajax:
                        return JsonResponse({
                            'success': False,
                            'message': custom_message,
                            'error_type': 'unique_constraint',
                            'field': 'nombre_reporte'
                        })
                    else:
                        messages.error(request, custom_message)
                else:
                    if is_ajax:
                        return JsonResponse({
                            'success': False,
                            'message': f'Error al crear el reporte: {str(e)}'
                        })
                    else:
                        messages.error(request, f'Error al crear el reporte: {str(e)}')
            except Exception as e:
                if is_ajax:
                    return JsonResponse({
                        'success': False,
                        'message': f'Error al crear el reporte: {str(e)}'
                    })
                else:
                    messages.error(request, f'Error al crear el reporte: {str(e)}')
        
        elif action == 'editar_reporte' or action == 'edit':
            try:
                with transaction.atomic():
                    reporte_id = data.get('reporte_id') or data.get('id')
                    reporte = get_object_or_404(Reporte, id=reporte_id)
                    
                    nombre_reporte = data.get('nombre_reporte', '').strip()
                    descripcion = data.get('descripcion', '').strip()
                    tipo = data.get('tipo')
                    
                    # Validaciones específicas
                    if not nombre_reporte:
                        raise ValueError('El nombre del reporte no puede estar vacío o solo contener espacios.')
                    if not descripcion:
                        raise ValueError('La descripción del reporte es obligatoria.')
                    if not tipo:
                        raise ValueError('Debe seleccionar un tipo de reporte.')
                    
                    # La validación de unicidad se manejará con IntegrityError
                    
                    reporte.nombre = nombre_reporte
                    reporte.descripcion = descripcion
                    reporte.tipo = tipo
                    reporte.save()
                    
                    # Eliminar productos existentes y agregar los nuevos
                    reporte.productos_reporte.all().delete()
                    
                    if is_ajax and request.content_type == 'application/json':
                        # Para datos JSON de AJAX
                        productos_data = data.get('productos', [])
                        if not productos_data:
                            # Compatibilidad con formato anterior
                            producto_id = data.get('producto_id')
                            cantidad = data.get('cantidad')
                            if producto_id:
                                productos_data = [{'producto_id': producto_id, 'cantidad': cantidad, 'observaciones': ''}]
                        
                        # Validar que se hayan seleccionado productos para reportes que los requieren
                        if tipo in ['producto', 'perdida'] and not productos_data:
                            raise ValueError('Debe seleccionar al menos un producto para este tipo de reporte.')
                        
                        # Validar productos duplicados
                        productos_ids = [p.get('producto_id') for p in productos_data if p.get('producto_id')]
                        if len(productos_ids) != len(set(productos_ids)):
                            raise ValueError('No puede agregar el mismo producto múltiples veces.')
                        
                        for producto_data in productos_data:
                            producto_id = producto_data.get('producto_id')
                            if producto_id:
                                try:
                                    producto = Producto.objects.get(id=producto_id)
                                except Producto.DoesNotExist:
                                    raise ValueError(f'El producto con ID {producto_id} no existe.')
                                    
                                cantidad = producto_data.get('cantidad', '')
                                observaciones = producto_data.get('observaciones', '')
                                
                                # Validar cantidad según el tipo de reporte
                                if tipo == 'perdida':
                                    if not cantidad or cantidad == '':
                                        raise ValueError('La cantidad es obligatoria para reportes de pérdida.')
                                    try:
                                        cantidad_final = int(cantidad)
                                    except ValueError:
                                        raise ValueError('La cantidad debe ser un número válido.')
                                    if cantidad_final <= 0:
                                        raise ValueError('La cantidad debe ser mayor a 0.')
                                elif tipo == 'producto':
                                    # Para reportes de producto, la cantidad es obligatoria
                                    if not cantidad or cantidad == '':
                                        raise ValueError('La cantidad es obligatoria para reportes de producto.')
                                    try:
                                        cantidad_final = int(cantidad)
                                    except ValueError:
                                        raise ValueError('La cantidad debe ser un número válido.')
                                    if cantidad_final <= 0:
                                        raise ValueError('La cantidad debe ser mayor a 0.')
                                else:
                                    # Para tipos inventario y ventas, la cantidad es opcional
                                    try:
                                        cantidad_final = int(cantidad) if cantidad and cantidad != '' else None
                                    except ValueError:
                                        raise ValueError('La cantidad debe ser un número válido.')
                                
                                ReporteProducto.objects.create(
                                    reporte=reporte,
                                    producto=producto,
                                    cantidad=cantidad_final,
                                    observaciones=observaciones or 'N/A'
                                )
                    else:
                        # Para datos de formulario tradicional
                        productos_ids = data.getlist('productos[]')
                        cantidades = data.getlist('cantidades[]')
                        observaciones_list = data.getlist('observaciones[]')
                        
                        # Validar que se hayan seleccionado productos para reportes que los requieren
                        if tipo in ['producto', 'perdida'] and not any(productos_ids):
                            raise ValueError('Debe seleccionar al menos un producto para este tipo de reporte.')
                        
                        for i, producto_id in enumerate(productos_ids):
                            if producto_id:
                                producto = Producto.objects.get(id=producto_id)
                                cantidad = cantidades[i] if i < len(cantidades) else ''
                                observaciones = observaciones_list[i] if i < len(observaciones_list) else ''
                                
                                # Validar cantidad según el tipo de reporte
                                if tipo == 'perdida':
                                    if not cantidad or cantidad == '':
                                        raise ValueError('La cantidad es obligatoria para reportes de pérdida.')
                                    cantidad_final = int(cantidad)
                                    if cantidad_final <= 0:
                                        raise ValueError('La cantidad debe ser mayor a 0.')
                                elif tipo == 'producto':
                                    # Para reportes de producto, la cantidad es obligatoria
                                    if not cantidad or cantidad == '':
                                        raise ValueError('La cantidad es obligatoria para reportes de producto.')
                                    cantidad_final = int(cantidad)
                                    if cantidad_final <= 0:
                                        raise ValueError('La cantidad debe ser mayor a 0.')
                                else:
                                    # Para tipos inventario y ventas, la cantidad es opcional
                                    try:
                                        cantidad_final = int(cantidad) if cantidad and cantidad != '' else None
                                    except ValueError:
                                        raise ValueError('La cantidad debe ser un número válido.')
                                
                                ReporteProducto.objects.create(
                                    reporte=reporte,
                                    producto=producto,
                                    cantidad=cantidad_final,
                                    observaciones=observaciones or 'N/A'
                                )
                    
                    if is_ajax:
                        return JsonResponse({
                            'success': True,
                            'message': f'Reporte "{nombre_reporte}" actualizado exitosamente.'
                        })
                    else:
                        messages.success(request, f'Reporte "{nombre_reporte}" actualizado exitosamente.')
                        
            except IntegrityError as e:
                error_message = str(e)
                if 'UNIQUE constraint failed' in error_message and 'nombre_reporte' in error_message:
                    custom_message = 'Ya existe un reporte con este nombre. Por favor, ingrese un nombre diferente.'
                    if is_ajax:
                        return JsonResponse({
                            'success': False,
                            'message': custom_message,
                            'error_type': 'unique_constraint',
                            'field': 'nombre_reporte'
                        })
                    else:
                        messages.error(request, custom_message)
                else:
                    if is_ajax:
                        return JsonResponse({
                            'success': False,
                            'message': f'Error al actualizar el reporte: {str(e)}'
                        })
                    else:
                        messages.error(request, f'Error al actualizar el reporte: {str(e)}')
            except Exception as e:
                if is_ajax:
                    return JsonResponse({
                        'success': False,
                        'message': f'Error al actualizar el reporte: {str(e)}'
                    })
                else:
                    messages.error(request, f'Error al actualizar el reporte: {str(e)}')
        
        elif action == 'eliminar_reporte':
            try:
                reporte_id = data.get('reporte_id')
                reporte = get_object_or_404(Reporte, id=reporte_id)
                nombre_reporte = reporte.nombre_reporte
                reporte.delete()
                
                if is_ajax:
                    return JsonResponse({
                        'success': True,
                        'message': f'Reporte "{nombre_reporte}" eliminado exitosamente.'
                    })
                else:
                    messages.success(request, f'Reporte "{nombre_reporte}" eliminado exitosamente.')
                    
            except Exception as e:
                if is_ajax:
                    return JsonResponse({
                        'success': False,
                        'message': f'Error al eliminar el reporte: {str(e)}'
                    })
                else:
                    messages.error(request, f'Error al eliminar el reporte: {str(e)}')
        
        elif action == 'toggle_activo' or action == 'toggle':
            try:
                reporte_id = data.get('reporte_id') or data.get('id')
                reporte = get_object_or_404(Reporte, id=reporte_id)
                reporte.activo = not reporte.activo
                reporte.save()
                
                estado = 'activado' if reporte.activo else 'desactivado'
                
                if is_ajax:
                    return JsonResponse({
                        'success': True,
                        'message': f'Reporte "{reporte.nombre_reporte}" {estado} exitosamente.',
                        'activo': reporte.activo
                    })
                else:
                    messages.success(request, f'Reporte "{reporte.nombre_reporte}" {estado} exitosamente.')
                    
            except Exception as e:
                if is_ajax:
                    return JsonResponse({
                        'success': False,
                        'message': f'Error al cambiar el estado del reporte: {str(e)}'
                    })
                else:
                    messages.error(request, f'Error al cambiar el estado del reporte: {str(e)}')
        
        elif action == 'get':
            try:
                reporte_id = data.get('reporte_id') or data.get('id')
                reporte = get_object_or_404(Reporte, id=reporte_id)
                productos_reporte = reporte.productos_reporte.all()
                
                productos_data = []
                for rp in productos_reporte:
                    productos_data.append({
                        'id': rp.producto.id,
                        'nombre': rp.producto.nombre,
                        'producto_nombre': rp.producto.nombre,
                        'cantidad': rp.cantidad if rp.cantidad is not None else '',
                        'observaciones': rp.observaciones or ''
                    })
                
                return JsonResponse({
                    'success': True,
                    'reporte': {
                        'id': reporte.id,
                        'nombre': reporte.nombre_reporte,
                        'descripcion': reporte.descripcion,
                        'tipo': reporte.tipo,
                        'fecha_creacion': reporte.fecha_creacion.strftime('%d/%m/%Y %H:%M'),
                        'creador': reporte.usuario_creador.username
                    },
                    'productos': productos_data
                })
                
            except Exception as e:
                return JsonResponse({
                    'success': False,
                    'message': f'Error al obtener los datos del reporte: {str(e)}'
                })
        
        if not is_ajax:
            return redirect('gestionar_reportes')
    
    context = {
        'reportes': reportes,
        'productos': productos,
    }
    
    return render(request, 'Tienda/gestionar_reportes.html', context)

@login_required
@user_passes_test(lambda u: u.is_superuser, login_url='home')
def obtener_reporte_detalle(request, reporte_id):
    """Vista AJAX para obtener los detalles de un reporte"""
    try:
        reporte = get_object_or_404(Reporte, id=reporte_id)
        productos_reporte = reporte.productos_reporte.all()
        
        productos_data = []
        for rp in productos_reporte:
            productos_data.append({
                'producto_id': rp.producto.id,
                'producto_nombre': rp.producto.nombre,
                'nombre': rp.producto.nombre,
                'cantidad': rp.cantidad if rp.cantidad is not None else '',
                'observaciones': rp.observaciones or ''
            })
        
        return JsonResponse({
            'success': True,
            'reporte': {
                'id': reporte.id,
                'nombre': reporte.nombre_reporte,
                'nombre_reporte': reporte.nombre_reporte,
                'descripcion': reporte.descripcion,
                'tipo': reporte.tipo,
                'productos': productos_data
            }
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Error al obtener los detalles del reporte: {str(e)}'
        })