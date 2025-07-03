from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import JsonResponse
from django.db import transaction
from django.contrib.auth import authenticate
from django.utils import timezone
from ..models import Lote, Proveedor, Producto, LoteProducto, Registro_compra_proveedor
from datetime import datetime, timedelta

def is_superuser(user):
    return user.is_superuser

@login_required
def verify_password_inventory(request):
    if not request.user.is_superuser:
        messages.error(request, 'No tienes permiso para acceder a esta sección.')
        return redirect('home')

    if request.method == 'POST':
        password = request.POST.get('password')
        user = authenticate(request, username=request.user.username, password=password)
        if user is not None:
            request.session['inventory_access_granted'] = True
            messages.success(request, 'Acceso concedido.')
            return redirect('gestionar_inventario')
        else:
            messages.error(request, 'Contraseña incorrecta.')
            return redirect('home')
    else:
        return redirect('home')

@login_required
@user_passes_test(lambda u: u.is_superuser, login_url='home')
def gestionar_inventario(request):
    if not request.session.get('inventory_access_granted', False):
        messages.warning(request, 'Debes verificar tu contraseña para acceder a la gestión de inventario.')
        return redirect('home')
    lotes = Lote.objects.all().order_by('fecha_registro')
    proveedores = Proveedor.objects.all()
    productos = Producto.objects.all()
    if request.method == 'POST':
        action = request.POST.get('action')
        lote_id = request.POST.get('lote_id')
        is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
        try:
            if action == 'add_lote':
                with transaction.atomic():
                    code_lote = request.POST.get('code_lote', '').strip()
                    if not code_lote:
                        if is_ajax:
                            return JsonResponse({'success': False, 'message': 'El código de lote no puede estar vacío o solo contener espacios.'})
                        raise ValueError('El código de lote no puede estar vacío o solo contener espacios.')
                    if Lote.objects.filter(code_lote=code_lote).exists():
                        if is_ajax:
                            return JsonResponse({'success': False, 'message': 'El código de lote ya existe'})
                        raise ValueError('El código de lote ya existe')
                    productos_ids = request.POST.getlist('productos[]')
                    cantidades = request.POST.getlist('cantidades[]')
                    fechas_vencimiento = request.POST.getlist('fechas_vencimiento[]')
                    if not productos_ids:
                        if is_ajax:
                            return JsonResponse({'success': False, 'message': 'Debe agregar al menos un producto al lote'})
                        raise ValueError('Debe agregar al menos un producto al lote')
                    # Validar fechas de vencimiento antes de crear el lote
                    for i, producto_id in enumerate(productos_ids):
                        fecha_vencimiento = fechas_vencimiento[i] if i < len(fechas_vencimiento) and fechas_vencimiento[i] else None
                        if fecha_vencimiento:
                            fecha_v = datetime.strptime(fecha_vencimiento, '%Y-%m-%d').date()
                            if fecha_v < (timezone.now().date() - timedelta(days=10)):
                                if is_ajax:
                                    return JsonResponse({'success': False, 'message': 'La fecha de vencimiento no puede ser mayor a 10 días en el pasado.'})
                                raise ValueError('La fecha de vencimiento no puede ser mayor a 10 días en el pasado.')
                    lote = Lote.objects.create(
                        code_lote=code_lote,
                        proveedor_id=request.POST.get('proveedor')
                    )
                    for i, producto_id in enumerate(productos_ids):
                        producto = Producto.objects.get(id=producto_id)
                        cantidad = int(cantidades[i]) if cantidades[i] else 1
                        fecha_vencimiento = fechas_vencimiento[i] if i < len(fechas_vencimiento) and fechas_vencimiento[i] else None
                        LoteProducto.objects.create(
                            lote=lote,
                            producto=producto,
                            cantidad_inicial=cantidad,
                            cantidad_disponible=cantidad,
                            fecha_vencimiento=fecha_vencimiento
                        )
                        producto.stock += cantidad
                        producto.save()
                        Registro_compra_proveedor.objects.create(
                            proveedor=lote.proveedor,
                            productos=producto,
                            cantidad=cantidad,
                            precio_unitario=producto.costo,
                            valor_total=producto.costo * cantidad
                        )
                    msg = f'Lote {lote.code_lote} creado con {len(productos_ids)} producto(s)'
                    if is_ajax:
                        return JsonResponse({
                            'success': True,
                            'message': msg,
                            'lote': {
                                'id': lote.id,
                                'code': lote.code_lote,
                                'proveedor': lote.proveedor.nombre_proveedor,
                                'fecha': lote.fecha_registro.strftime('%d/%m/%Y')
                            }
                        })
                    messages.success(request, msg)
            elif action == 'edit_lote' and lote_id:
                with transaction.atomic():
                    lote = get_object_or_404(Lote, id=lote_id)
                    code_lote = request.POST.get('code_lote', '').strip()
                    if not code_lote:
                        if is_ajax:
                            return JsonResponse({'success': False, 'message': 'El código de lote no puede estar vacío o solo contener espacios.'})
                        raise ValueError('El código de lote no puede estar vacío o solo contener espacios.')
                    lote.code_lote = code_lote
                    lote.proveedor_id = request.POST.get('proveedor')
                    lote.save()
                    msg = f'Lote {lote.code_lote} actualizado correctamente'
                    if is_ajax:
                        return JsonResponse({'success': True, 'message': msg})
                    messages.success(request, msg)
            elif action == 'delete_lote' and lote_id:
                with transaction.atomic():
                    lote = get_object_or_404(Lote, id=lote_id)
                    code_lote = lote.code_lote

                    for relacion in lote.productos_relacionados.all():
                        producto = relacion.producto
                        producto.stock -= relacion.cantidad_disponible
                        producto.save()

                    lote.delete()

                    msg = f'Lote {code_lote} eliminado correctamente'
                    messages.success(request, msg)
                    if is_ajax:
                        return JsonResponse({
                            'success': True,
                            'message': msg
                        })

            elif action == 'get_lote' and lote_id:
                lote = get_object_or_404(Lote, id=lote_id)
                productos_lote = [{
                    'id': lp.producto.id,
                    'nombre': lp.producto.nombre,
                    'cantidad': lp.cantidad_inicial,
                    'fecha_vencimiento': lp.fecha_vencimiento.strftime('%Y-%m-%d') if lp.fecha_vencimiento else None
                } for lp in lote.productos_relacionados.all()]

                return JsonResponse({
                    'id': lote.id,
                    'code_lote': lote.code_lote,
                    'proveedor_id': lote.proveedor.id,
                    'productos': productos_lote
                })

            elif action == 'assign_productos' and lote_id:
                with transaction.atomic():
                    lote = get_object_or_404(Lote, id=lote_id)
                    productos_ids = request.POST.getlist('productos_ids[]')
                    cantidades = request.POST.getlist('cantidades[]')
                    fechas_vencimiento = request.POST.getlist('fechas_vencimiento[]')
                    productos_a_eliminar = request.POST.getlist('productos_eliminar[]')
                    if productos_a_eliminar:
                        for prod_id in productos_a_eliminar:
                            try:
                                relacion = LoteProducto.objects.get(lote=lote, producto_id=prod_id)
                                producto = relacion.producto
                                producto.stock -= relacion.cantidad_disponible
                                producto.save()
                                relacion.delete()
                            except LoteProducto.DoesNotExist:
                                pass
                    if not productos_ids and not productos_a_eliminar:
                        if is_ajax:
                            return JsonResponse({'success': False, 'message': 'Debe seleccionar al menos un producto'})
                        raise ValueError('Debe seleccionar al menos un producto')
                    for i, producto_id in enumerate(productos_ids):
                        producto = Producto.objects.get(id=producto_id)
                        cantidad = int(cantidades[i]) if cantidades[i] else 1
                        fecha_vencimiento = fechas_vencimiento[i] if i < len(fechas_vencimiento) and fechas_vencimiento[i] else None
                        if fecha_vencimiento:
                            fecha_v = datetime.strptime(fecha_vencimiento, '%Y-%m-%d').date()
                            if fecha_v < (timezone.now().date() - timedelta(days=10)):
                                if is_ajax:
                                    return JsonResponse({'success': False, 'message': 'La fecha de vencimiento no puede ser mayor a 10 días en el pasado.'})
                                raise ValueError('La fecha de vencimiento no puede ser mayor a 10 días en el pasado.')
                        relacion, created = LoteProducto.objects.get_or_create(
                            lote=lote,
                            producto=producto,
                            defaults={
                                'cantidad_inicial': cantidad,
                                'cantidad_disponible': cantidad,
                                'fecha_vencimiento': fecha_vencimiento
                            }
                        )
                        if not created:
                            relacion.cantidad_inicial += cantidad
                            relacion.cantidad_disponible += cantidad
                            relacion.save()
                        producto.stock += cantidad
                        producto.save()
                        Registro_compra_proveedor.objects.create(
                            proveedor=lote.proveedor,
                            productos=producto,
                            cantidad=cantidad,
                            precio_unitario=producto.costo,
                            valor_total=producto.costo * cantidad
                        )
                    msg = 'Productos asignados correctamente al lote.'
                    if is_ajax:
                        return JsonResponse({'success': True, 'message': msg})
                    messages.success(request, msg)
        except Exception as e:
            if is_ajax:
                return JsonResponse({'success': False, 'message': str(e)})
            messages.error(request, str(e))
            if is_ajax:
                return JsonResponse({
                    'success': False,
                    'message': str(e)
                }, status=400)
        if is_ajax:
            return JsonResponse({
                'success': False,
                'message': 'Acción no válida'
            }, status=400)
    lotes = Lote.objects.all().order_by('fecha_registro')
    context = {
        'lotes': lotes,
        'proveedores': proveedores,
        'productos_disponibles': productos,
        'now': timezone.now().date()
    }
    return render(request, 'Tienda/gestionar_inventario.html', context)