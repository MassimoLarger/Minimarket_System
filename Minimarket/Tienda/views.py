from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.utils import timezone
from django.contrib.auth.decorators import user_passes_test # Para restringir vistas a admin
from django.db import transaction # Para operaciones atómicas
from .forms import LoginForm
from .models import Producto, Oferta, Venta, DetalleVenta, Proveedor, Lote, Oferta_vencimiento, Oferta_producto, LoteProducto
from django.db.models import Q
from django.contrib.auth import update_session_auth_hash # Para mantener sesión tras cambio de contraseña
from django.views.decorators.csrf import csrf_exempt

# Helper para verificar si es superusuario
def is_superuser(user):
    return user.is_superuser

def home(request):
    return render(request, 'Tienda/home.html')

def login_view(request):
    # Si el usuario ya está autenticado, redirigir directamente a home
    if request.user.is_authenticated:
        return redirect('home')
        
    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']
            user = authenticate(request, username=username, password=password)
            if user is not None:
                login(request, user)
                messages.success(request, f'Bienvenido, {username}!')
                return redirect('home')
            else:
                messages.error(request, 'Nombre de usuario o contraseña incorrectos')
    else:
        form = LoginForm()
    
    return render(request, 'Tienda/login.html', {'form': form})

def logout_view(request):
    logout(request)
    messages.info(request, 'Has cerrado sesión correctamente')
    return redirect('login')

@login_required
@user_passes_test(is_superuser, login_url='home') # Proteger y redirigir si no es superuser
def gestionar_productos(request):
    # Obtener todos los productos para mostrar en la tabla
    productos = Producto.objects.all().order_by('nombre')
    
    if request.method == 'POST':
        action = request.POST.get('action')
        producto_id = request.POST.get('producto_id')
        is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'

        if action == 'add_producto':
            try:
                producto = Producto.objects.create(
                    nombre=request.POST.get('nombre'),
                    codigo_barras=request.POST.get('codigo_barras'),
                    stock=int(request.POST.get('stock', 0)),
                    precio=float(request.POST.get('precio', 0)),
                    costo=float(request.POST.get('costo', 0)),
                    minimal_stock=int(request.POST.get('minimal_stock', 0))
                )
                messages.success(request, 'Producto añadido correctamente.')
                if is_ajax:
                    return JsonResponse({
                        'success': True,
                        'message': 'Producto añadido correctamente.',
                        'producto': {
                            'id': producto.id,
                            'nombre': producto.nombre
                        }
                    })
            except Exception as e:
                messages.error(request, f'Error al añadir producto: {e}')
                if is_ajax:
                    return JsonResponse({
                        'success': False,
                        'message': f'Error al añadir producto: {e}'
                    }, status=400)

        elif action == 'edit_producto' and producto_id:
            try:
                producto = get_object_or_404(Producto, id=producto_id)
                producto.nombre = request.POST.get('nombre')
                producto.codigo_barras = request.POST.get('codigo_barras')
                producto.stock = int(request.POST.get('stock', 0))
                producto.precio = float(request.POST.get('precio', 0))
                producto.costo = float(request.POST.get('costo', 0))
                producto.minimal_stock = int(request.POST.get('minimal_stock', 0))
                producto.save()
                messages.success(request, f'Producto "{producto.nombre}" actualizado correctamente.')
                if is_ajax:
                    return JsonResponse({
                        'success': True,
                        'message': f'Producto "{producto.nombre}" actualizado correctamente.'
                    })
            except Exception as e:
                messages.error(request, f'Error al actualizar producto: {e}')
                if is_ajax:
                    return JsonResponse({
                        'success': False,
                        'message': f'Error al actualizar producto: {e}'
                    }, status=400)
        
        elif action == 'delete_producto' and producto_id:
            try:
                producto = get_object_or_404(Producto, id=producto_id)
                nombre_producto = producto.nombre
                
                # Verificar si el producto está en uso
                en_ventas = DetalleVenta.objects.filter(producto=producto).exists()
                en_ofertas = Oferta_producto.objects.filter(producto_id=producto).exists()
                en_lotes = LoteProducto.objects.filter(producto=producto).exists()
                
                if en_ventas or en_ofertas or en_lotes:
                    mensaje = f'No se puede eliminar "{nombre_producto}" porque tiene registros relacionados.'
                    messages.error(request, mensaje)
                    return JsonResponse({
                        'success': False,
                        'message': mensaje
                    }, status=400)
                
                producto.delete()
                mensaje = f'Producto "{nombre_producto}" eliminado correctamente.'
                messages.success(request, mensaje)
                return JsonResponse({
                    'success': True,
                    'message': mensaje
                })
                
            except Exception as e:
                mensaje = f'Error al eliminar producto: {str(e)}'
                messages.error(request, mensaje)
                return JsonResponse({
                    'success': False,
                    'message': mensaje
                }, status=400)
        
        elif action == 'get_producto':
            try:
                producto = get_object_or_404(Producto, id=producto_id)
                return JsonResponse({
                    'id': producto.id,
                    'nombre': producto.nombre,
                    'codigo_barras': producto.codigo_barras,
                    'stock': producto.stock,
                    'precio': float(producto.precio),
                    'costo': float(producto.costo),
                    'minimal_stock': producto.minimal_stock
                })
            except Exception as e:
                return JsonResponse({'error': str(e)}, status=400)
        
        # Si llegamos aquí y es una solicitud AJAX, devolver un error
        if is_ajax:
            return JsonResponse({
                'success': False,
                'message': 'Acción no válida'
            }, status=400)
    
    # Recargar la lista actualizada de productos
    productos = Producto.objects.all().order_by('nombre')
    context = {
        'productos': productos,
        'es_superadmin': request.user.is_superuser
    }
    return render(request, 'Tienda/productos.html', context)

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
        # Manejar búsqueda de producto
        if 'buscar_codigo' in request.POST:
            codigo_barras = request.POST.get('codigo_barras', '').strip()
            try:
                producto = Producto.objects.get(codigo_barras=codigo_barras)
                producto_encontrado = {
                    'id': producto.id,
                    'nombre': producto.nombre,
                    'precio': float(producto.precio),
                    'stock': producto.stock
                }
            except Producto.DoesNotExist:
                error_busqueda = "Producto no encontrado"
        
        # Manejar agregar producto a la venta
        elif 'agregar_producto' in request.POST:
            producto_id = request.POST.get('producto_id')
            cantidad = int(request.POST.get('cantidad', 1))
            
            try:
                producto = Producto.objects.get(id=producto_id)
                if cantidad > producto.stock:
                    error_busqueda = "No hay suficiente stock disponible"
                else:
                    # Buscar si el producto ya está en la venta
                    item_existente = next((item for item in venta_actual if item['id'] == producto.id), None)
                    
                    if item_existente:
                        # Actualizar cantidad si ya existe
                        nueva_cantidad = item_existente['cantidad'] + cantidad
                        if nueva_cantidad > producto.stock:
                            error_busqueda = "No hay suficiente stock disponible"
                        else:
                            item_existente['cantidad'] = nueva_cantidad
                            item_existente['subtotal'] = item_existente['precio'] * item_existente['cantidad']
                    else:
                        # Agregar nuevo producto
                        venta_actual.append({
                            'id': producto.id,
                            'nombre': producto.nombre,
                            'cantidad': cantidad,
                            'precio': float(producto.precio),
                            'subtotal': float(producto.precio) * cantidad
                        })
                    
                    request.session['venta_actual'] = venta_actual
                    total = sum(item['subtotal'] for item in venta_actual)
                    total_articulos = sum(item['cantidad'] for item in venta_actual)
            
            except Producto.DoesNotExist:
                error_busqueda = "Producto no encontrado"
        
        # Manejar eliminación de producto
        elif 'eliminar_producto' in request.POST:
            producto_id = int(request.POST.get('producto_id'))
            venta_actual = [item for item in venta_actual if item['id'] != producto_id]
            request.session['venta_actual'] = venta_actual
            total = sum(item['subtotal'] for item in venta_actual) if venta_actual else 0
            total_articulos = sum(item['cantidad'] for item in venta_actual) if venta_actual else 0
            return redirect('nueva_venta')
        
        # Manejar cancelación de venta
        elif 'cancelar' in request.GET:
            if 'venta_actual' in request.session:
                del request.session['venta_actual']
            return redirect('nueva_venta')
        
        # Manejar confirmación de venta
        elif 'confirmar_venta' in request.POST:
            if request.POST.get('confirmar_venta') == 'si' and venta_actual:
                try:
                    with transaction.atomic():
                        # Crear la venta
                        venta = Venta.objects.create(
                            empleado=request.user,
                            total=total,
                            cantidad_articulos=total_articulos  # Nuevo campo para almacenar el total de artículos
                        )
                        
                        # Crear detalles de venta y actualizar stock
                        for item in venta_actual:
                            producto = Producto.objects.get(id=item['id'])
                            DetalleVenta.objects.create(
                                venta=venta,
                                producto=producto,
                                cantidad=item['cantidad'],
                                precio_unitario=item['precio'],
                                subtotal=item['subtotal']
                            )
                            
                            # Descontar stock
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
                        
                        # Configurar variables para mostrar venta exitosa
                        venta_confirmada = True
                        venta_id = venta.id
                        venta_fecha = venta.fecha
                        messages.success(request, f'Venta #{venta.id} registrada correctamente.')
                        del request.session['venta_actual']  # Limpiar la venta temporal
                
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
def historial(request):
    from datetime import datetime, timedelta
    from django.utils import timezone
    
    # Obtener parámetros de filtrado
    fecha_inicio = request.GET.get('fecha_inicio')
    fecha_fin = request.GET.get('fecha_fin')
    filtro_dia = request.GET.get('dia')
    
    # Consulta base
    ventas = Venta.objects.filter(empleado=request.user).order_by('-fecha')
    
    # Aplicar filtros
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
    
    # Obtener detalles para cada venta
    ventas_con_detalles = []
    for venta in ventas:
        detalles = DetalleVenta.objects.filter(venta=venta).select_related('producto')
        ventas_con_detalles.append({
            'venta': venta,
            'detalles': detalles
        })
    
    # Calcular totales
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
def ofertas(request):
    # Lógica POST para admin
    if request.method == 'POST' and request.user.is_superuser:
        action = request.POST.get('action')
        oferta_id = request.POST.get('oferta_id')

        if action == 'save_oferta':
            try:
                with transaction.atomic(): # Asegurar atomicidad
                    if oferta_id: # Editar oferta existente
                        oferta = get_object_or_404(Oferta, id=oferta_id)
                        oferta.tipo_oferta = request.POST.get('tipo_oferta')
                        oferta.descuento_porcetaje = float(request.POST.get('descuento_porcentaje'))
                        oferta.fecha_inicio = request.POST.get('fecha_inicio')
                        oferta.fecha_fin = request.POST.get('fecha_fin')
                        oferta.save()
                        messages.success(request, f'Oferta "{oferta.tipo_oferta}" actualizada.')
                        # Limpiar relaciones antiguas antes de añadir nuevas (simplificado)
                        Oferta_producto.objects.filter(oferta_id=oferta).delete()
                        Oferta_vencimiento.objects.filter(oferta_id=oferta).delete()
                    else: # Crear nueva oferta
                        oferta = Oferta.objects.create(
                            tipo_oferta=request.POST.get('tipo_oferta'),
                            descuento_porcetaje=float(request.POST.get('descuento_porcentaje')),
                            fecha_inicio=request.POST.get('fecha_inicio'),
                            fecha_fin=request.POST.get('fecha_fin'),
                            creado_por=request.user
                        )
                        messages.success(request, f'Oferta "{oferta.tipo_oferta}" creada.')

                    # Gestionar Oferta_producto (relación muchos a muchos)
                    productos_oferta_ids = request.POST.getlist('productos_oferta')
                    for producto_id in productos_oferta_ids:
                        producto = get_object_or_404(Producto, id=producto_id)
                        Oferta_producto.objects.create(oferta_id=oferta, producto_id=producto)

                    # Gestionar múltiples Oferta_vencimiento
                    # Obtener todos los productos de vencimiento dinámicamente
                    i = 1
                    while True:
                        producto_vencimiento_id = request.POST.get(f'producto_vencimiento_{i}')
                        cantidad_vencimiento = request.POST.get(f'cantidad_vencimiento_{i}')
                        new_code_bar = request.POST.get(f'new_code_bar_{i}')
                        
                        if not producto_vencimiento_id or not cantidad_vencimiento:
                            break
                            
                        producto_venc = get_object_or_404(Producto, id=producto_vencimiento_id)
                        Oferta_vencimiento.objects.create(
                            oferta_id=oferta,
                            producto_id=producto_venc,
                            cantidad=cantidad_vencimiento,
                            new_code_bar=new_code_bar if new_code_bar else None
                        )
                        i += 1
                        
                return redirect('ofertas') # Redirigir después de guardar

            except Exception as e:
                messages.error(request, f'Error al guardar la oferta: {e}')

        elif action == 'delete_oferta' and oferta_id:
             try:
                 oferta = get_object_or_404(Oferta, id=oferta_id)
                 nombre_oferta = oferta.tipo_oferta
                 oferta.delete()
                 messages.success(request, f'Oferta "{nombre_oferta}" eliminada.')
             except Exception as e:
                 messages.error(request, f'Error al eliminar la oferta: {e}')
             return redirect('ofertas')
             
        elif action == 'get_oferta':
            try:
                oferta = get_object_or_404(Oferta, id=oferta_id)
                productos_oferta = [op.producto_id.id for op in Oferta_producto.objects.filter(oferta_id=oferta)]
                productos_vencimiento = [{
                    'producto_id': ov.producto_id.id,
                    'cantidad': ov.cantidad,
                    'new_code_bar': ov.new_code_bar or ''
                } for ov in Oferta_vencimiento.objects.filter(oferta_id=oferta)]
                
                return JsonResponse({
                    'id': oferta.id,
                    'tipo_oferta': oferta.tipo_oferta,
                    'descuento_porcentaje': float(oferta.descuento_porcetaje),
                    'fecha_inicio': oferta.fecha_inicio.strftime('%Y-%m-%d'),
                    'fecha_fin': oferta.fecha_fin.strftime('%Y-%m-%d'),
                    'productos_oferta': productos_oferta,
                    'productos_vencimiento': productos_vencimiento
                })
            except Exception as e:
                return JsonResponse({'error': str(e)}, status=400)

    # Lógica GET (común para admin y empleado)
    ofertas_activas = Oferta.objects.filter(fecha_inicio__lte=timezone.now().date(), fecha_fin__gte=timezone.now().date())
    context = {
        'ofertas_activas': ofertas_activas,
        'es_admin': request.user.is_superuser
    }

    # Añadir datos extra para admin en GET
    if request.user.is_superuser:
        context['todas_ofertas'] = Oferta.objects.all().order_by('-fecha_inicio')
        context['productos'] = Producto.objects.all()

    return render(request, 'Tienda/ofertas.html', context)

# Vista para verificar contraseña antes de acceder a gestión de proveedores
@login_required
def verify_password_providers(request):
    if not request.user.is_superuser:
        messages.error(request, 'No tienes permiso para realizar esta acción.')
        return redirect('home')

    if request.method == 'POST':
        password = request.POST.get('password')
        # Usar authenticate para verificar la contraseña del usuario actual
        user = authenticate(request, username=request.user.username, password=password)
        if user is not None:
            # Contraseña correcta, marcar sesión como verificada para proveedores
            request.session['providers_access_granted'] = True
            messages.success(request, 'Contraseña verificada. Accediendo a gestión de proveedores.')
            return redirect('gestionar_proveedores')
        else:
            # Contraseña incorrecta
            messages.error(request, 'Contraseña incorrecta. Inténtalo de nuevo.')
            return redirect('home') # Redirigir de vuelta a home si falla
    else:
        # Si no es POST, redirigir a home
        return redirect('home')

# --- Vistas de Gestión (Admin) ---

@login_required
@user_passes_test(is_superuser, login_url='home')
def registro_compra_proveedores(request):
    from .models import Registro_compra_proveedor
    if request.method == 'POST':
        action = request.POST.get('action')
        registro_id = request.POST.get('registro_id')
        if action == 'delete_registro' and registro_id:
            try:
                registro = Registro_compra_proveedor.objects.get(id=registro_id)
                registro.delete()
                messages.success(request, 'Registro eliminado correctamente.')
            except Registro_compra_proveedor.DoesNotExist:
                messages.error(request, 'Registro no encontrado.')
        return redirect('registro_compra_proveedores')
    registros = Registro_compra_proveedor.objects.all().order_by('-fecha_compra')
    return render(request, 'Tienda/registro_compra_proveedores.html', {'registros': registros})

@login_required
def verify_password_inventory(request):
    if not request.user.is_superuser:
        messages.error(request, 'No tienes permiso para acceder a esta sección.')
        return redirect('home')

    if request.method == 'POST':
        password = request.POST.get('password')
        user = authenticate(request, username=request.user.username, password=password)
        if user is not None:
            # Contraseña correcta, redirigir a la gestión de inventario
            # Guardar un flag en la sesión para indicar que se verificó
            request.session['inventory_access_granted'] = True
            messages.success(request, 'Acceso concedido.')
            return redirect('gestionar_inventario')
        else:
            messages.error(request, 'Contraseña incorrecta.')
            # Permanecer en home o redirigir a home, mostrando el modal de nuevo si es posible
            # O simplemente mostrar el error y dejar que el usuario intente de nuevo desde home
            return redirect('home') # Redirigir a home para que el modal pueda reabrirse
    else:
        # Si se accede por GET, simplemente redirigir a home
        return redirect('home')

@login_required
@user_passes_test(lambda u: u.is_superuser, login_url='home')
def gestionar_inventario(request):
    # Verificación de acceso adicional
    if not request.session.get('inventory_access_granted', False):
        messages.warning(request, 'Debes verificar tu contraseña para acceder a la gestión de inventario.')
        return redirect('home')

    # Obtener datos iniciales
    # Ordenar lotes del más viejo al más nuevo por defecto
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
                    # Validar código único
                    code_lote = request.POST.get('code_lote')
                    if Lote.objects.filter(code_lote=code_lote).exists():
                        raise ValueError('El código de lote ya existe')

                    # Crear el lote
                    lote = Lote.objects.create(
                        code_lote=code_lote,
                        proveedor_id=request.POST.get('proveedor')
                    )

                    # Procesar productos
                    productos_ids = request.POST.getlist('productos[]')
                    cantidades = request.POST.getlist('cantidades[]')
                    fechas_vencimiento = request.POST.getlist('fechas_vencimiento[]')

                    if not productos_ids:
                        raise ValueError('Debe agregar al menos un producto al lote')

                    for i, producto_id in enumerate(productos_ids):
                        producto = Producto.objects.get(id=producto_id)
                        cantidad = int(cantidades[i]) if cantidades[i] else 1
                        fecha_vencimiento = fechas_vencimiento[i] if i < len(fechas_vencimiento) and fechas_vencimiento[i] else None

                        # Crear relación Lote-Producto
                        LoteProducto.objects.create(
                            lote=lote,
                            producto=producto,
                            cantidad_inicial=cantidad,
                            cantidad_disponible=cantidad,
                            fecha_vencimiento=fecha_vencimiento
                        )

                        # Actualizar stock del producto
                        producto.stock += cantidad
                        producto.save()

                        # Crear respaldo en Registro_compra_proveedor
                        from .models import Registro_compra_proveedor
                        Registro_compra_proveedor.objects.create(
                            proveedor=lote.proveedor,
                            productos=producto,
                            cantidad=cantidad,
                            precio_unitario=producto.costo,
                            valor_total=producto.costo * cantidad
                        )

                    msg = f'Lote {lote.code_lote} creado con {len(productos_ids)} producto(s)'
                    messages.success(request, msg)
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

            elif action == 'edit_lote' and lote_id:
                with transaction.atomic():
                    lote = get_object_or_404(Lote, id=lote_id)
                    lote.code_lote = request.POST.get('code_lote')
                    lote.proveedor_id = request.POST.get('proveedor')
                    lote.save()

                    msg = f'Lote {lote.code_lote} actualizado correctamente'
                    messages.success(request, msg)
                    if is_ajax:
                        return JsonResponse({
                            'success': True,
                            'message': msg
                        })

            elif action == 'delete_lote' and lote_id:
                with transaction.atomic():
                    lote = get_object_or_404(Lote, id=lote_id)
                    code_lote = lote.code_lote

                    # Actualizar stocks antes de eliminar
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

                    # Eliminar productos del lote si corresponde
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
                        raise ValueError('Debe seleccionar al menos un producto')

                    for i, producto_id in enumerate(productos_ids):
                        producto = Producto.objects.get(id=producto_id)
                        cantidad = int(cantidades[i]) if cantidades[i] else 1
                        fecha_vencimiento = fechas_vencimiento[i] if i < len(fechas_vencimiento) and fechas_vencimiento[i] else None

                        # Crear o actualizar relación
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

                        # Actualizar stock
                        producto.stock += cantidad
                        producto.save()

                        # Crear respaldo en Registro_compra_proveedor
                        from .models import Registro_compra_proveedor
                        Registro_compra_proveedor.objects.create(
                            proveedor=lote.proveedor,
                            productos=producto,
                            cantidad=cantidad,
                            precio_unitario=producto.costo,
                            valor_total=producto.costo * cantidad
                        )

                    msg = f'{len(productos_ids)} producto(s) agregados/eliminados del lote {lote.code_lote}'
                    messages.success(request, msg)
                    if is_ajax:
                        return JsonResponse({
                            'success': True,
                            'message': msg
                        })

        except Exception as e:
            messages.error(request, f'Error: {str(e)}')
            if is_ajax:
                return JsonResponse({
                    'success': False,
                    'message': str(e)
                }, status=400)

        # Si es AJAX y no se manejó antes
        if is_ajax:
            return JsonResponse({
                'success': False,
                'message': 'Acción no válida'
            }, status=400)

    # Recargar datos actualizados para el template
    # Ordenar lotes del más viejo al más nuevo por defecto
    lotes = Lote.objects.all().order_by('fecha_registro')

    context = {
        'lotes': lotes,
        'proveedores': proveedores,
        'productos_disponibles': productos,
        'now': timezone.now().date()  # Para comparar con fechas de vencimiento
    }
    return render(request, 'Tienda/gestionar_inventario.html', context)

@login_required
@user_passes_test(is_superuser, login_url='home') # Proteger y redirigir si no es superuser
def gestionar_proveedores(request):
    # Verificar si el acceso fue concedido a través de la verificación de contraseña
    if not request.session.get('providers_access_granted', False):
        messages.warning(request, 'Debes verificar tu contraseña para acceder a la gestión de proveedores.')
        request.session['providers_access_granted'] = False
        return redirect('home')
    
    # No limpiar el flag de sesión en ningún caso para mantener el acceso durante operaciones CRUD
    
    # Obtener todos los proveedores para mostrar en la tabla
    proveedores = Proveedor.objects.all().order_by('nombre_proveedor')
    
    if request.method == 'POST':
        action = request.POST.get('action')
        proveedor_id = request.POST.get('proveedor_id')
        is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'

        if action == 'add_proveedor':
            try:
                proveedor = Proveedor.objects.create(
                    nombre_proveedor=request.POST.get('nombre_proveedor'),
                    direccion=request.POST.get('direccion'),
                    telefono=request.POST.get('telefono'),
                    rut=request.POST.get('rut')
                )
                messages.success(request, 'Proveedor añadido correctamente.')
                if is_ajax:
                    return JsonResponse({
                        'success': True,
                        'message': 'Proveedor añadido correctamente.',
                        'proveedor': {
                            'id': proveedor.id,
                            'nombre_proveedor': proveedor.nombre_proveedor
                        }
                    })
            except Exception as e:
                messages.error(request, f'Error al añadir proveedor: {e}')
                if is_ajax:
                    return JsonResponse({
                        'success': False,
                        'message': f'Error al añadir proveedor: {e}'
                    }, status=400)

        elif action == 'edit_proveedor' and proveedor_id:
            try:
                proveedor = get_object_or_404(Proveedor, id=proveedor_id)
                proveedor.nombre_proveedor = request.POST.get('nombre_proveedor')
                proveedor.direccion = request.POST.get('direccion')
                proveedor.telefono = request.POST.get('telefono')
                proveedor.save()
                messages.success(request, f'Proveedor "{proveedor.nombre_proveedor}" actualizado correctamente.')
                if is_ajax:
                    return JsonResponse({
                        'success': True,
                        'message': f'Proveedor "{proveedor.nombre_proveedor}" actualizado correctamente.'
                    })
            except Exception as e:
                messages.error(request, f'Error al actualizar proveedor: {e}')
                if is_ajax:
                    return JsonResponse({
                        'success': False,
                        'message': f'Error al actualizar proveedor: {e}'
                    }, status=400)
        
        elif action == 'delete_proveedor' and proveedor_id:
            try:
                proveedor = Proveedor.objects.filter(id=proveedor_id).first()
                if not proveedor:
                    mensaje = f'No se encontró el proveedor con ID {proveedor_id}.'
                    messages.error(request, mensaje)
                    if is_ajax:
                        return JsonResponse({
                            'success': False,
                            'message': mensaje
                        }, status=400)
                    return redirect('gestionar_proveedores')
                nombre_proveedor = proveedor.nombre_proveedor
                lotes_asociados = Lote.objects.filter(proveedor=proveedor).exists()
                if lotes_asociados:
                    mensaje = f'No se puede eliminar el proveedor "{nombre_proveedor}" porque tiene lotes asociados.'
                    messages.error(request, mensaje)
                    if is_ajax:
                        return JsonResponse({
                            'success': False,
                            'message': mensaje
                        }, status=400)
                else:
                    proveedor.delete()
                    mensaje = f'Proveedor "{nombre_proveedor}" eliminado correctamente.'
                    messages.success(request, mensaje)
                    if is_ajax:
                        return JsonResponse({
                            'success': True,
                            'message': mensaje
                        })
            except Exception as e:
                mensaje = f'Error al eliminar proveedor: {e}'
                messages.error(request, mensaje)
                if is_ajax:
                    return JsonResponse({
                        'success': False,
                        'message': mensaje
                    }, status=400)
        
        elif action == 'get_proveedor':
            try:
                proveedor = get_object_or_404(Proveedor, id=proveedor_id)
                return JsonResponse({
                    'id': proveedor.id,
                    'nombre_proveedor': proveedor.nombre_proveedor,
                    'direccion': proveedor.direccion,
                    'telefono': proveedor.telefono,
                    'rut': proveedor.rut
                })
            except Exception as e:
                return JsonResponse({'error': str(e)}, status=400)
        
        # Si llegamos aquí y es una solicitud AJAX, devolver un error
        if is_ajax:
            return JsonResponse({
                'success': False,
                'message': 'Acción no válida'
            }, status=400)
    
    # Recargar la lista actualizada de proveedores
    proveedores = Proveedor.objects.all().order_by('nombre_proveedor')
    context = {
        'proveedores': proveedores
    }
    return render(request, 'Tienda/gestionar_proveedores.html', context)