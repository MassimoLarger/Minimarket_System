from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.http import JsonResponse
from django.utils import timezone
from django.db import transaction
from django.contrib.auth import authenticate
from datetime import timedelta
from ..models import Alert, Producto, OfertaProducto, OfertaVencimiento, LoteProducto

@login_required
def verify_password_alerts(request):
    if not request.user.is_superuser:
        messages.error(request, 'No tienes permiso para realizar esta acción.')
        return redirect('home')

    if request.method == 'POST':
        password = request.POST.get('password')
        user = authenticate(request, username=request.user.username, password=password)
        if user is not None:
            request.session['alerts_access_granted'] = True
            messages.success(request, 'Contraseña verificada. Accediendo a gestión de alertas.')
            return redirect('gestionar_alertas')
        else:
            messages.error(request, 'Contraseña incorrecta. Inténtalo de nuevo.')
            return redirect('home')
    else:
        return redirect('home')

@login_required
@user_passes_test(lambda u: u.is_superuser, login_url='home')
def gestionar_alertas(request):
    """Vista principal para gestionar alertas del sistema"""
    
    if not request.session.get('alerts_access_granted', False):
        messages.warning(request, 'Debes verificar tu contraseña para acceder a la gestión de alertas.')
        return redirect('home')
    
    if request.method == 'POST':
        action = request.POST.get('action')
        is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
        
        try:
            if action == 'crear_alerta':
                with transaction.atomic():
                    nombre = request.POST.get('nombre', '').strip()
                    tipo = request.POST.get('tipo')
                    mensaje = request.POST.get('mensaje', '').strip()
                    producto_id = request.POST.get('producto_id')
                    oferta_producto_id = request.POST.get('oferta_producto_id')
                    oferta_vencimiento_id = request.POST.get('oferta_vencimiento_id')
                    umbral_stock = request.POST.get('umbral_stock')
                    dias_anticipacion = request.POST.get('dias_anticipacion')
                    
                    if not nombre or not tipo or not mensaje:
                        raise ValueError("Todos los campos obligatorios deben estar completos")
                    
                    # Validar campos obligatorios según el tipo
                    if tipo == 'stock_bajo' and not umbral_stock and not alerta.umbral_stock:
                        raise ValueError("El umbral de stock es obligatorio para alertas de stock bajo")
                    if tipo in ['proximo_vencer', 'oferta_terminando'] and not dias_anticipacion and not alerta.dias_anticipacion:
                        raise ValueError("Los días de anticipación son obligatorios para este tipo de alerta")
                    
                    # Crear la alerta
                    alerta = Alert(
                        nombre=nombre,
                        tipo=tipo,
                        mensaje=mensaje
                    )
                    
                    # Asignar campos específicos según el tipo
                    if umbral_stock:
                        try:
                            alerta.umbral_stock = int(umbral_stock)
                        except ValueError:
                            raise ValueError("El umbral de stock debe ser un número válido")
                    if dias_anticipacion:
                         try:
                             dias_anticipacion_int = int(dias_anticipacion)
                             if dias_anticipacion_int <= 0 or dias_anticipacion_int > 365:
                                 raise ValueError("Los días de anticipación deben estar entre 1 y 365")
                             alerta.dias_anticipacion = dias_anticipacion_int
                         except ValueError as e:
                             if "invalid literal" in str(e):
                                 raise ValueError("Los días de anticipación deben ser un número válido")
                             else:
                                 raise e
                    
                    alerta.save()
                    
                    if is_ajax:
                        return JsonResponse({
                            'success': True,
                            'message': 'Alerta creada exitosamente',
                            'alerta': {
                                'id': alerta.id,
                                'nombre': alerta.nombre,
                                'tipo': alerta.get_tipo_display(),
                                'estado': alerta.get_estado_display(),
                                'fecha_creacion': alerta.fecha_creacion.strftime('%d/%m/%Y %H:%M')
                            }
                        })
                    else:
                        messages.success(request, 'Alerta creada exitosamente')
                        return redirect('gestionar_alertas')
            
            elif action == 'activar_alerta':
                alerta_id = request.POST.get('alerta_id')
                alerta = get_object_or_404(Alert, id=alerta_id)
                alerta.estado = 'activa'
                alerta.activa = True
                alerta.save()
                
                if is_ajax:
                    return JsonResponse({'success': True, 'message': 'Alerta activada'})
                else:
                    messages.success(request, 'Alerta activada exitosamente')
                    return redirect('gestionar_alertas')
            
            elif action == 'desactivar_alerta':
                alerta_id = request.POST.get('alerta_id')
                alerta = get_object_or_404(Alert, id=alerta_id)
                alerta.estado = 'desactivada'
                alerta.activa = False
                alerta.save()
                
                if is_ajax:
                    return JsonResponse({'success': True, 'message': 'Alerta desactivada'})
                else:
                    messages.success(request, 'Alerta desactivada exitosamente')
                    return redirect('gestionar_alertas')
            
            elif action == 'eliminar_alerta':
                alerta_id = request.POST.get('alerta_id')
                alerta = get_object_or_404(Alert, id=alerta_id)
                alerta.delete()
                
                if is_ajax:
                    return JsonResponse({'success': True, 'message': 'Alerta eliminada'})
                else:
                    messages.success(request, 'Alerta eliminada exitosamente')
                    return redirect('gestionar_alertas')
            
            elif action == 'marcar_mostrada':
                alerta_id = request.POST.get('alerta_id')
                alerta = get_object_or_404(Alert, id=alerta_id)
                alerta.marcar_como_mostrada()
                
                if is_ajax:
                    return JsonResponse({'success': True, 'message': 'Alerta marcada como mostrada'})
                else:
                    messages.success(request, 'Alerta marcada como mostrada')
                    return redirect('gestionar_alertas')
            
            elif action == 'editar_alerta':
                with transaction.atomic():
                    alerta_id = request.POST.get('alerta_id')
                    alerta = get_object_or_404(Alert, id=alerta_id)
                    
                    nombre = request.POST.get('nombre', '').strip()
                    tipo = request.POST.get('tipo')
                    mensaje = request.POST.get('mensaje', '').strip()
                    umbral_stock = request.POST.get('umbral_stock')
                    
                    # Manejar días de anticipación - buscar en los campos específicos
                    dias_anticipacion = None
                    
                    # Buscar en el campo de vencimiento
                    dias_venc = request.POST.get('dias_anticipacion_venc', '').strip()
                    if dias_venc:
                        dias_anticipacion = dias_venc
                    
                    # Buscar en el campo de oferta si no se encontró en vencimiento
                    if not dias_anticipacion:
                        dias_oferta = request.POST.get('dias_anticipacion_oferta', '').strip()
                        if dias_oferta:
                            dias_anticipacion = dias_oferta
                    else:
                        dias_oferta = request.POST.get('dias_anticipacion_oferta', '').strip()
                    
                    if not nombre or not tipo or not mensaje:
                        raise ValueError("Todos los campos obligatorios deben estar completos")
                    
                    # Actualizar los campos de la alerta
                    alerta.nombre = nombre
                    alerta.tipo = tipo
                    alerta.mensaje = mensaje
                    
                    # Asignar campos específicos según el tipo ANTES de limpiar
                    if tipo == 'stock_bajo':
                        if umbral_stock:
                            try:
                                alerta.umbral_stock = int(umbral_stock)
                            except ValueError:
                                raise ValueError("El umbral de stock debe ser un número válido")
                        # Validar que tenga umbral_stock (del formulario o existente)
                        if not umbral_stock and not alerta.umbral_stock:
                            raise ValueError("El umbral de stock es obligatorio para alertas de stock bajo")
                    elif tipo in ['proximo_vencer', 'oferta_terminando']:
                        if dias_anticipacion:
                            try:
                                dias_anticipacion_int = int(dias_anticipacion)
                                if dias_anticipacion_int <= 0 or dias_anticipacion_int > 365:
                                    raise ValueError("Los días de anticipación deben estar entre 1 y 365")
                                alerta.dias_anticipacion = dias_anticipacion_int
                            except ValueError as e:
                                if "invalid literal" in str(e):
                                    raise ValueError("Los días de anticipación deben ser un número válido")
                                else:
                                    raise e
                        # Validar que tenga dias_anticipacion (del formulario o existente)
                        if not dias_anticipacion and not alerta.dias_anticipacion:
                            raise ValueError("Los días de anticipación son obligatorios para este tipo de alerta")
                    
                    # Limpiar campos específicos que no corresponden al tipo actual DESPUÉS de asignar
                    if tipo != 'stock_bajo':
                        alerta.umbral_stock = None
                    if tipo not in ['proximo_vencer', 'oferta_terminando']:
                        alerta.dias_anticipacion = None
                    
                    alerta.save()
                    
                    if is_ajax:
                        return JsonResponse({
                            'success': True,
                            'message': 'Alerta editada exitosamente',
                            'alerta': {
                                'id': alerta.id,
                                'nombre': alerta.nombre,
                                'tipo': alerta.get_tipo_display(),
                                'estado': alerta.get_estado_display(),
                                'fecha_creacion': alerta.fecha_creacion.strftime('%d/%m/%Y %H:%M'),
                                'umbral_stock': alerta.umbral_stock,
                                'dias_anticipacion': alerta.dias_anticipacion
                            }
                        })
                    else:
                        messages.success(request, 'Alerta editada exitosamente')
                        return redirect('gestionar_alertas')
            
            elif action == 'obtener_alerta':
                # Obtener datos de una alerta específica para edición
                alerta_id = request.POST.get('alerta_id')
                try:
                    alerta = Alert.objects.get(id=alerta_id)
                    return JsonResponse({
                        'success': True,
                        'alerta': {
                            'id': alerta.id,
                            'nombre': alerta.nombre,
                            'tipo': alerta.tipo,
                            'mensaje': alerta.mensaje,
                            'umbral_stock': alerta.umbral_stock,
                            'dias_anticipacion': alerta.dias_anticipacion
                        }
                    })
                except Alert.DoesNotExist:
                    return JsonResponse({'success': False, 'message': 'Alerta no encontrada'})
            
            elif action == 'verificar_alertas':
                # Verificar todas las alertas activas
                alertas_activadas = verificar_alertas_automaticas()
                
                if is_ajax:
                    return JsonResponse({
                        'success': True, 
                        'message': f'{len(alertas_activadas)} alertas verificadas',
                        'alertas_activadas': alertas_activadas
                    })
                else:
                    messages.info(request, f'{len(alertas_activadas)} alertas verificadas')
                    return redirect('gestionar_alertas')
        
        except Exception as e:
            if is_ajax:
                return JsonResponse({'success': False, 'message': str(e)})
            else:
                messages.error(request, f'Error: {str(e)}')
                return redirect('gestionar_alertas')
    
    # GET request - mostrar la página
    alertas = Alert.objects.all().order_by('-fecha_creacion')
    productos = Producto.objects.all().order_by('nombre')
    ofertas_producto = OfertaProducto.objects.filter(activa=True).order_by('nombre')
    ofertas_vencimiento = OfertaVencimiento.objects.filter(activa=True).order_by('nombre')
    
    # Verificar alertas automáticamente al cargar la página
    alertas_activas = verificar_alertas_automaticas()
    
    context = {
        'alertas': alertas,
        'productos': productos,
        'ofertas_producto': ofertas_producto,
        'ofertas_vencimiento': ofertas_vencimiento,
        'alertas_activas': alertas_activas,
    }
    
    return render(request, 'Tienda/gestionar_alertas.html', context)

def verificar_alertas_automaticas():
    """Función para verificar automáticamente las condiciones de las alertas"""
    from django.utils import timezone
    from datetime import timedelta
    
    alertas_activadas = []
    alertas_procesadas = set()  # Para evitar duplicados por tipo
    
    # Obtener todas las alertas activas
    alertas = Alert.objects.filter(activa=True, estado='activa')
    
    for alerta in alertas:
        productos_afectados = []
        
        if alerta.tipo == 'stock_bajo':
            # Verificar productos con stock bajo usando el umbral específico de esta alerta
            umbral = alerta.umbral_stock if alerta.umbral_stock else 10
            productos_bajo_stock = Producto.objects.filter(stock__lte=umbral)
            
            if productos_bajo_stock.exists():
                detalles_productos = []
                for producto in productos_bajo_stock[:5]:
                    # Buscar lotes del producto
                    lotes = LoteProducto.objects.filter(
                        producto=producto,
                        cantidad_disponible__gt=0
                    ).order_by('fecha_vencimiento')
                    
                    if lotes.exists():
                        lotes_info = [f"Lote {lote.lote.code_lote} ({lote.cantidad_disponible} unidades)" for lote in lotes[:2]]
                        detalle = f"{producto.nombre} (Stock: {producto.stock}) - Lotes: {', '.join(lotes_info)}"
                        if lotes.count() > 2:
                            detalle += f" y {lotes.count() - 2} lotes más"
                    else:
                        detalle = f"{producto.nombre} (Stock: {producto.stock}) - Sin lotes registrados"
                    
                    detalles_productos.append(detalle)
                
                mensaje_detallado = f"{alerta.mensaje}\n\nProductos afectados (umbral ≤ {umbral}):\n" + "\n".join(detalles_productos)
                if productos_bajo_stock.count() > 5:
                    mensaje_detallado += f"\n\nY {productos_bajo_stock.count() - 5} productos más con stock bajo."
                
                alertas_activadas.append({
                    'id': alerta.id,
                    'nombre': alerta.nombre,
                    'tipo': alerta.get_tipo_display(),
                    'mensaje': mensaje_detallado,
                    'fecha_creacion': alerta.fecha_creacion.strftime('%d/%m/%Y %H:%M'),
                    'productos_count': productos_bajo_stock.count()
                })
        
        elif alerta.tipo == 'proximo_vencer':
            # Verificar productos próximos a vencer usando el mayor número de días de todas las alertas activas de este tipo
            alertas_vencimiento = alertas.filter(tipo='proximo_vencer')
            dias_maximo = max([a.dias_anticipacion if a.dias_anticipacion else 7 for a in alertas_vencimiento])
            fecha_limite = timezone.now().date() + timedelta(days=dias_maximo)
            
            lotes_venciendo = LoteProducto.objects.filter(
                fecha_vencimiento__lte=fecha_limite,
                fecha_vencimiento__gte=timezone.now().date(),
                cantidad_disponible__gt=0
            ).order_by('fecha_vencimiento')
            
            if lotes_venciendo.exists():
                detalles_lotes = []
                for lote in lotes_venciendo[:5]:
                    dias_restantes = (lote.fecha_vencimiento - timezone.now().date()).days
                    detalle = f"{lote.producto.nombre} - Lote {lote.lote.code_lote} ({lote.cantidad_disponible} unidades) - Vence en {dias_restantes} días ({lote.fecha_vencimiento.strftime('%d/%m/%Y')})"
                    detalles_lotes.append(detalle)
                
                mensaje_detallado = f"{alerta.mensaje}\n\nLotes próximos a vencer:\n" + "\n".join(detalles_lotes)
                if lotes_venciendo.count() > 5:
                    mensaje_detallado += f"\n\nY {lotes_venciendo.count() - 5} lotes más próximos a vencer."
                
                alertas_activadas.append({
                    'id': alerta.id,
                    'nombre': alerta.nombre,
                    'tipo': alerta.get_tipo_display(),
                    'mensaje': mensaje_detallado,
                    'fecha_creacion': alerta.fecha_creacion.strftime('%d/%m/%Y %H:%M'),
                    'lotes_count': lotes_venciendo.count()
                })
                
                alertas_procesadas.add(alerta.tipo)
        
        elif alerta.tipo == 'oferta_terminando':
            # Verificar ofertas próximas a terminar usando el mayor número de días de todas las alertas activas de este tipo
            alertas_ofertas = alertas.filter(tipo='oferta_terminando')
            dias_maximo = max([a.dias_anticipacion if a.dias_anticipacion else 3 for a in alertas_ofertas])
            fecha_limite = timezone.now().date() + timedelta(days=dias_maximo)
            
            ofertas_terminando = []
            
            # Verificar ofertas de producto
            ofertas_producto = OfertaProducto.objects.filter(
                activa=True,
                fecha_fin__lte=fecha_limite,
                fecha_fin__gte=timezone.now().date()
            )
            ofertas_terminando.extend([f"Producto: {o.nombre}" for o in ofertas_producto[:3]])
            
            # Verificar ofertas de vencimiento
            ofertas_vencimiento = OfertaVencimiento.objects.filter(
                activa=True,
                fecha_fin__lte=fecha_limite,
                fecha_fin__gte=timezone.now().date()
            )
            ofertas_terminando.extend([f"Vencimiento: {o.nombre}" for o in ofertas_vencimiento[:3]])
            
            if ofertas_terminando:
                mensaje_detallado = f"{alerta.mensaje} Ofertas terminando: {', '.join(ofertas_terminando[:5])}"
                total_ofertas = ofertas_producto.count() + ofertas_vencimiento.count()
                if total_ofertas > 5:
                    mensaje_detallado += f" y {total_ofertas - 5} más."
                
                alertas_activadas.append({
                    'id': alerta.id,
                    'nombre': alerta.nombre,
                    'tipo': alerta.get_tipo_display(),
                    'mensaje': mensaje_detallado,
                    'fecha_creacion': alerta.fecha_creacion.strftime('%d/%m/%Y %H:%M'),
                    'ofertas_count': total_ofertas
                })
                
                alertas_procesadas.add(alerta.tipo)
    
    return alertas_activadas

@login_required
def obtener_alertas_activas(request):
    """API endpoint para obtener alertas activas (para mostrar notificaciones)"""
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        alertas_activas = verificar_alertas_automaticas()
        return JsonResponse({
            'success': True,
            'alertas': alertas_activas,
            'count': len(alertas_activas)
        })
    
    return JsonResponse({'success': False, 'message': 'Acceso no autorizado'})