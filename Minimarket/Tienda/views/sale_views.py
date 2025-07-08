from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.utils import timezone
from django.db import transaction
from datetime import datetime, timedelta
from django.db.models import Q
from ..models import Producto, Venta, DetalleVenta, LoteProducto, OfertaProducto, OfertaVencimiento

def calcular_precio_con_ofertas(producto):
    """
    Calcula el precio final de un producto considerando las ofertas activas.
    Prioriza ofertas de vencimiento sobre ofertas de producto.
    """
    precio_original = producto.precio
    precio_final = precio_original
    oferta_aplicada = None
    
    # Verificar ofertas de vencimiento (mayor prioridad)
    ofertas_vencimiento = OfertaVencimiento.objects.filter(
        activa=True,
        fecha_inicio__lte=timezone.now().date()
    ).filter(
        Q(fecha_fin__isnull=True) | Q(fecha_fin__gte=timezone.now().date())
    )
    
    for oferta_venc in ofertas_vencimiento:
        # Verificar si el producto tiene lotes próximos a vencer
        fecha_limite = timezone.now().date() + timedelta(days=oferta_venc.dias_antes_vencimiento)
        lotes_proximos = LoteProducto.objects.filter(
            producto=producto,
            fecha_vencimiento__lte=fecha_limite,
            cantidad_disponible__gt=0
        )
        
        if lotes_proximos.exists():
            precio_con_descuento = oferta_venc.precio_con_descuento(precio_original)
            if precio_con_descuento < precio_final:
                precio_final = precio_con_descuento
                oferta_aplicada = f"{oferta_venc.nombre} ({oferta_venc.descuento_porcentaje}% desc.)"
    
    # Si no hay ofertas de vencimiento, verificar ofertas de producto
    if precio_final == precio_original:
        ofertas_producto = OfertaProducto.objects.filter(
            activa=True,
            productos=producto,
            fecha_inicio__lte=timezone.now().date()
        ).filter(
            Q(fecha_fin__isnull=True) | Q(fecha_fin__gte=timezone.now().date())
        )
        
        for oferta_prod in ofertas_producto:
            precio_con_descuento = oferta_prod.precio_con_descuento(precio_original)
            if precio_con_descuento < precio_final:
                precio_final = precio_con_descuento
                oferta_aplicada = f"{oferta_prod.nombre} ({oferta_prod.descuento_porcentaje}% desc.)"
    
    return {
        'precio_original': precio_original,
        'precio_final': precio_final,
        'oferta_aplicada': oferta_aplicada,
        'tiene_descuento': precio_final < precio_original
    }

@login_required
def nueva_venta(request):
    producto_encontrado = None
    error_busqueda = None
    venta_actual = request.session.get('venta_actual', [])
    total = sum(item['subtotal'] for item in venta_actual) if venta_actual else 0
    venta_confirmada = False
    venta_id = None
    venta_fecha = None
    total_articulos = sum(item['cantidad'] for item in venta_actual) if venta_actual else 0

    if request.method == 'POST':
        if 'buscar_codigo' in request.POST:
            codigo_barras = request.POST.get('codigo_barras', '').strip()
            try:
                # Validar que el código de barras sea un número entero válido
                if not codigo_barras:
                    error_busqueda = "Debe ingresar un código de barras"
                elif not codigo_barras.isdigit():
                    error_busqueda = "El código de barras debe ser un número entero válido"
                else:
                    codigo_barras_int = int(codigo_barras)
                    producto = Producto.objects.get(codigo_barras=codigo_barras_int)
                    precio_info = calcular_precio_con_ofertas(producto)
                    
                    producto_encontrado = {
                        'id': producto.id,
                        'nombre': producto.nombre,
                        'precio': precio_info['precio_final'],
                        'precio_original': precio_info['precio_original'],
                        'stock': producto.stock,
                        'tiene_descuento': precio_info['tiene_descuento'],
                        'oferta_aplicada': precio_info['oferta_aplicada']
                    }
            except Producto.DoesNotExist:
                error_busqueda = "Producto no encontrado"
            except ValueError:
                error_busqueda = "El código de barras debe ser un número entero válido"
        
        elif 'agregar_producto' in request.POST:
            producto_id = request.POST.get('producto_id')
            cantidad = int(request.POST.get('cantidad', 1))
            
            try:
                producto = Producto.objects.get(id=producto_id)
                precio_info = calcular_precio_con_ofertas(producto)
                precio_final = precio_info['precio_final']
                
                if cantidad > producto.stock:
                    error_busqueda = "No hay suficiente stock disponible"
                else:
                    item_existente = next((item for item in venta_actual if item['id'] == producto.id), None)
                    
                    if item_existente:
                        nueva_cantidad = item_existente['cantidad'] + cantidad
                        if nueva_cantidad > producto.stock:
                            error_busqueda = "No hay suficiente stock disponible"
                        else:
                            item_existente['cantidad'] = nueva_cantidad
                            item_existente['subtotal'] = item_existente['precio'] * item_existente['cantidad']
                    else:
                        venta_actual.append({
                            'id': producto.id,
                            'nombre': producto.nombre,
                            'cantidad': cantidad,
                            'precio': precio_final,
                            'precio_original': precio_info['precio_original'],
                            'subtotal': precio_final * cantidad,
                            'tiene_descuento': precio_info['tiene_descuento'],
                            'oferta_aplicada': precio_info['oferta_aplicada']
                        })
                    
                    request.session['venta_actual'] = venta_actual
                    total = sum(item['subtotal'] for item in venta_actual)
                    total_articulos = sum(item['cantidad'] for item in venta_actual)
            
            except Producto.DoesNotExist:
                error_busqueda = "Producto no encontrado"
        
        elif 'eliminar_producto' in request.POST:
            producto_id = int(request.POST.get('producto_id'))
            venta_actual = [item for item in venta_actual if item['id'] != producto_id]
            request.session['venta_actual'] = venta_actual
            total = sum(item['subtotal'] for item in venta_actual) if venta_actual else 0
            total_articulos = sum(item['cantidad'] for item in venta_actual) if venta_actual else 0
            return redirect('nueva_venta')
        
        elif 'cancelar' in request.GET:
            if 'venta_actual' in request.session:
                del request.session['venta_actual']
            return redirect('nueva_venta')
        
        elif 'confirmar_venta' in request.POST:
            if request.POST.get('confirmar_venta') == 'si' and venta_actual:
                try:
                    with transaction.atomic():
                        venta = Venta.objects.create(
                            empleado=request.user,
                            total=total,
                            cantidad_articulos=total_articulos
                        )
                        
                        for item in venta_actual:
                            producto = Producto.objects.get(id=item['id'])
                            DetalleVenta.objects.create(
                                venta=venta,
                                producto=producto,
                                cantidad=item['cantidad'],
                                precio_unitario=item['precio'],
                                subtotal=item['subtotal']
                            )
                            
                            cantidad_restante = item['cantidad']
                            lotes = LoteProducto.objects.filter(
                                producto=producto, 
                                cantidad_disponible__gt=0
                            ).order_by('fecha_vencimiento')
                            
                            for lote_producto in lotes:
                                if cantidad_restante <= 0:
                                    break
                                if lote_producto.cantidad_disponible >= cantidad_restante:
                                    lote_producto.cantidad_disponible -= cantidad_restante
                                    lote_producto.save()
                                    cantidad_restante = 0
                                else:
                                    cantidad_restante -= lote_producto.cantidad_disponible
                                    lote_producto.cantidad_disponible = 0
                                    lote_producto.save()
                            
                            producto.stock -= item['cantidad']
                            producto.save()
                        
                        venta_confirmada = True
                        venta_id = venta.id
                        venta_fecha = venta.fecha
                        messages.success(request, f'Venta #{venta.id} registrada correctamente.')
                        del request.session['venta_actual']
                
                except Exception as e:
                    messages.error(request, f'Error al procesar la venta: {e}')
                    return redirect('nueva_venta')

    context = {
        'producto_encontrado': producto_encontrado,
        'error_busqueda': error_busqueda,
        'venta_actual': venta_actual,
        'total': total,
        'venta_confirmada': venta_confirmada,
        'venta_id': venta_id,
        'venta_fecha': venta_fecha,
        'total_articulos': total_articulos
    }
    return render(request, 'Tienda/nueva_venta.html', context)

@login_required
def historial_ventas(request):
    
    fecha_inicio = request.GET.get('fecha_inicio')
    fecha_fin = request.GET.get('fecha_fin')
    filtro_dia = request.GET.get('dia')
    
    ventas = Venta.objects.filter(empleado=request.user).order_by('-fecha')
    
    if fecha_inicio and fecha_fin:
        try:
            fecha_inicio = datetime.strptime(fecha_inicio, '%Y-%m-%d').date()
            fecha_fin = datetime.strptime(fecha_fin, '%Y-%m-%d').date() + timedelta(days=1)
            ventas = ventas.filter(fecha__range=[fecha_inicio, fecha_fin])
        except ValueError:
            messages.error(request, "Formato de fecha incorrecto. Use YYYY-MM-DD")
    
    elif filtro_dia:
        if filtro_dia == 'hoy':
            hoy = timezone.now().date()
            ventas = ventas.filter(fecha__date=hoy)
        elif filtro_dia == 'ayer':
            ayer = timezone.now().date() - timedelta(days=1)
            ventas = ventas.filter(fecha__date=ayer)
        elif filtro_dia == 'semana':
            semana_pasada = timezone.now().date() - timedelta(days=7)
            ventas = ventas.filter(fecha__date__gte=semana_pasada)
    
    ventas_con_detalles = []
    for venta in ventas:
        detalles = DetalleVenta.objects.filter(venta=venta).select_related('producto')
        ventas_con_detalles.append({
            'venta': venta,
            'detalles': detalles
        })
    
    total_ventas = sum(venta.total for venta in ventas)
    total_articulos = sum(venta.cantidad_articulos for venta in ventas)
    
    context = {
        'ventas_con_detalles': ventas_con_detalles,
        'total_ventas': total_ventas,
        'total_articulos': total_articulos,
        'fecha_inicio': fecha_inicio.strftime('%Y-%m-%d') if fecha_inicio else '',
        'fecha_fin': (datetime.strptime(fecha_fin, '%Y-%m-%d').date() - timedelta(days=1)).strftime('%Y-%m-%d') if fecha_fin else '',
        'filtro_dia': filtro_dia
    }
    
    return render(request, 'Tienda/historial.html', context)

@login_required
def buscar_producto_api(request):
    if request.method == 'GET':
        codigo_barras = request.GET.get('codigo_barras', '').strip()
        if not codigo_barras:
            return JsonResponse({'error': 'Código de barras no proporcionado'}, status=400)
        
        # Validar que el código de barras sea un número entero válido
        if not codigo_barras.isdigit():
            return JsonResponse({'error': 'El código de barras debe ser un número entero válido'}, status=400)

        try:
            codigo_barras_int = int(codigo_barras)
            producto = Producto.objects.get(codigo_barras=codigo_barras_int)
            precio_info = calcular_precio_con_ofertas(producto)
    
            return JsonResponse({
                'id': producto.id,
                'nombre': producto.nombre,
                'precio': precio_info['precio_final'],
                'precio_original': precio_info['precio_original'],
                'stock': producto.stock,
                'tiene_descuento': precio_info['tiene_descuento'],
                'oferta_aplicada': precio_info['oferta_aplicada']
            })
        except Producto.DoesNotExist:
            return JsonResponse({'error': 'Producto no encontrado'}, status=404)
        except ValueError:
            return JsonResponse({'error': 'El código de barras debe ser un número entero válido'}, status=400)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    return JsonResponse({'error': 'Método no permitido'}, status=405)