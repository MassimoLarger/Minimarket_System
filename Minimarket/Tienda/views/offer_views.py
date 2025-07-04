from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import JsonResponse
from django.db import transaction
from datetime import datetime
from ..models import OfertaProducto, OfertaVencimiento, Producto

def is_superuser(user):
    return user.is_superuser

@login_required
@user_passes_test(is_superuser, login_url='home')
def gestionar_ofertas(request):
    ofertas_producto = OfertaProducto.objects.all().order_by('-fecha_inicio')
    ofertas_vencimiento = OfertaVencimiento.objects.all().order_by('-fecha_inicio')
    productos = Producto.objects.all().order_by('nombre')
    
    if request.method == 'POST':
        action = request.POST.get('action')
        oferta_id = request.POST.get('oferta_id')
        tipo_oferta = request.POST.get('tipo_oferta')
        is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
        
        try:
            if action == 'add_oferta':
                with transaction.atomic():
                    nombre = request.POST.get('nombre', '').strip()
                    if not nombre:
                        raise ValueError('El nombre de la oferta no puede estar vacío.')
                    
                    fecha_inicio = request.POST.get('fecha_inicio')
                    fecha_fin = request.POST.get('fecha_fin') or None
                    descuento_porcentaje = int(request.POST.get('descuento_porcentaje', 0))
                    activa = request.POST.get('activa') == 'on'
                    
                    if descuento_porcentaje <= 0 or descuento_porcentaje > 100:
                        raise ValueError('El descuento debe estar entre 1 y 100%.')
                    
                    if fecha_fin and fecha_inicio >= fecha_fin:
                        raise ValueError('La fecha de fin debe ser posterior a la fecha de inicio.')
                    
                    if tipo_oferta == 'producto':
                        productos_ids = request.POST.getlist('productos[]')
                        if not productos_ids:
                            raise ValueError('Debe seleccionar al menos un producto.')
                        
                        oferta = OfertaProducto.objects.create(
                            nombre=nombre,
                            fecha_inicio=fecha_inicio,
                            fecha_fin=fecha_fin,
                            descuento_porcentaje=descuento_porcentaje,
                            activa=activa
                        )
                        oferta.productos.set(productos_ids)
                        
                    elif tipo_oferta == 'vencimiento':
                        dias_antes_vencimiento = int(request.POST.get('dias_antes_vencimiento', 3))
                        if dias_antes_vencimiento <= 0:
                            raise ValueError('Los días antes del vencimiento deben ser mayor a 0.')
                        
                        oferta = OfertaVencimiento.objects.create(
                            nombre=nombre,
                            fecha_inicio=fecha_inicio,
                            fecha_fin=fecha_fin,
                            descuento_porcentaje=descuento_porcentaje,
                            activa=activa,
                            dias_antes_vencimiento=dias_antes_vencimiento
                        )
                    
                    mensaje = f'Oferta "{nombre}" creada correctamente.'
                    if is_ajax:
                        return JsonResponse({'success': True, 'message': mensaje})
                    messages.success(request, mensaje)
            
            elif action == 'edit_oferta' and oferta_id:
                with transaction.atomic():
                    nombre = request.POST.get('nombre', '').strip()
                    if not nombre:
                        raise ValueError('El nombre de la oferta no puede estar vacío.')
                    
                    fecha_inicio = request.POST.get('fecha_inicio')
                    fecha_fin = request.POST.get('fecha_fin') or None
                    descuento_porcentaje = int(request.POST.get('descuento_porcentaje', 0))
                    activa = request.POST.get('activa') == 'on'
                    
                    if descuento_porcentaje <= 0 or descuento_porcentaje > 100:
                        raise ValueError('El descuento debe estar entre 1 y 100%.')
                    
                    if fecha_fin and fecha_inicio >= fecha_fin:
                        raise ValueError('La fecha de fin debe ser posterior a la fecha de inicio.')
                    
                    if tipo_oferta == 'producto':
                        oferta = get_object_or_404(OfertaProducto, id=oferta_id)
                        productos_ids = request.POST.getlist('productos[]')
                        if not productos_ids:
                            raise ValueError('Debe seleccionar al menos un producto.')
                        
                        oferta.nombre = nombre
                        oferta.fecha_inicio = fecha_inicio
                        oferta.fecha_fin = fecha_fin
                        oferta.descuento_porcentaje = descuento_porcentaje
                        oferta.activa = activa
                        oferta.save()
                        oferta.productos.set(productos_ids)
                        
                    elif tipo_oferta == 'vencimiento':
                        oferta = get_object_or_404(OfertaVencimiento, id=oferta_id)
                        dias_antes_vencimiento = int(request.POST.get('dias_antes_vencimiento', 3))
                        if dias_antes_vencimiento <= 0:
                            raise ValueError('Los días antes del vencimiento deben ser mayor a 0.')
                        
                        oferta.nombre = nombre
                        oferta.fecha_inicio = fecha_inicio
                        oferta.fecha_fin = fecha_fin
                        oferta.descuento_porcentaje = descuento_porcentaje
                        oferta.activa = activa
                        oferta.dias_antes_vencimiento = dias_antes_vencimiento
                        oferta.save()
                    
                    mensaje = f'Oferta "{nombre}" actualizada correctamente.'
                    if is_ajax:
                        return JsonResponse({'success': True, 'message': mensaje})
                    messages.success(request, mensaje)
            
            elif action == 'delete_oferta' and oferta_id:
                with transaction.atomic():
                    if tipo_oferta == 'producto':
                        oferta = get_object_or_404(OfertaProducto, id=oferta_id)
                    elif tipo_oferta == 'vencimiento':
                        oferta = get_object_or_404(OfertaVencimiento, id=oferta_id)
                    
                    nombre_oferta = oferta.nombre
                    oferta.delete()
                    
                    mensaje = f'Oferta "{nombre_oferta}" eliminada correctamente.'
                    if is_ajax:
                        return JsonResponse({'success': True, 'message': mensaje})
                    messages.success(request, mensaje)
            
            elif action == 'get_oferta' and oferta_id:
                if tipo_oferta == 'producto':
                    oferta = get_object_or_404(OfertaProducto, id=oferta_id)
                    productos_ids = list(oferta.productos.values_list('id', flat=True))
                    return JsonResponse({
                        'id': oferta.id,
                        'nombre': oferta.nombre,
                        'fecha_inicio': oferta.fecha_inicio.strftime('%Y-%m-%d'),
                        'fecha_fin': oferta.fecha_fin.strftime('%Y-%m-%d') if oferta.fecha_fin else '',
                        'descuento_porcentaje': oferta.descuento_porcentaje,
                        'activa': oferta.activa,
                        'productos': productos_ids,
                        'tipo': 'producto'
                    })
                elif tipo_oferta == 'vencimiento':
                    oferta = get_object_or_404(OfertaVencimiento, id=oferta_id)
                    return JsonResponse({
                        'id': oferta.id,
                        'nombre': oferta.nombre,
                        'fecha_inicio': oferta.fecha_inicio.strftime('%Y-%m-%d'),
                        'fecha_fin': oferta.fecha_fin.strftime('%Y-%m-%d') if oferta.fecha_fin else '',
                        'descuento_porcentaje': oferta.descuento_porcentaje,
                        'activa': oferta.activa,
                        'dias_antes_vencimiento': oferta.dias_antes_vencimiento,
                        'tipo': 'vencimiento'
                    })
        
        except Exception as e:
            if is_ajax:
                return JsonResponse({'success': False, 'message': str(e)}, status=400)
            messages.error(request, f'Error: {e}')
    
    context = {
        'ofertas_producto': ofertas_producto,
        'ofertas_vencimiento': ofertas_vencimiento,
        'productos': productos,
        'es_superadmin': request.user.is_superuser
    }
    return render(request, 'Tienda/ofertas.html', context)