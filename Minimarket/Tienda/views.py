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
    if request.method == 'POST':
        try:
            with transaction.atomic():
                # Crear la venta
                venta = Venta.objects.create(
                    empleado=request.user,
                    total=request.POST.get('total', 0)
                )
                
                # Procesar los detalles de la venta
                productos_ids = request.POST.getlist('producto_id[]')
                cantidades = request.POST.getlist('cantidad[]')
                precios = request.POST.getlist('precio[]')
                
                for i in range(len(productos_ids)):
                    producto = get_object_or_404(Producto, id=productos_ids[i])
                    cantidad = int(cantidades[i])
                    precio = float(precios[i])
                    
                    # Crear detalle de venta
                    DetalleVenta.objects.create(
                        venta=venta,
                        producto=producto,
                        cantidad=cantidad,
                        precio_unitario=precio
                    )
                    
                    # Actualizar stock del producto
                    producto.stock -= cantidad
                    producto.save()
                
                messages.success(request, f'Venta #{venta.id} registrada correctamente.')
                return redirect('historial')
        except Exception as e:
            messages.error(request, f'Error al procesar la venta: {e}')
            return redirect('nueva_venta')
    
    # Para solicitudes GET
    productos = Producto.objects.all()
    return render(request, 'Tienda/nueva_venta.html', {'productos': productos})

@login_required
def obtener_detalle_venta(request, venta_id):
    venta = get_object_or_404(Venta, id=venta_id)
    detalles = DetalleVenta.objects.filter(venta=venta)
    
    # Verificar que el usuario sea el empleado que realizó la venta o un superusuario
    if request.user != venta.empleado and not request.user.is_superuser:
        messages.error(request, 'No tienes permiso para ver esta venta.')
        return redirect('historial')
    
    return render(request, 'Tienda/detalle_venta.html', {
        'venta': venta,
        'detalles': detalles
    })

@login_required
def historial(request):
    # Obtener ventas del día actual para el empleado actual
    from datetime import datetime, time
    from django.utils import timezone
    
    today = timezone.now().date()
    start_of_day = datetime.combine(today, time.min)
    end_of_day = datetime.combine(today, time.max)
    
    ventas = Venta.objects.filter(
        empleado=request.user,
        fecha__range=(start_of_day, end_of_day)
    ).order_by('-fecha')
    
    return render(request, 'Tienda/historial.html', {'ventas': ventas})

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

# API para escaneo de código de barras
@login_required
def buscar_producto_api(request):
    codigo = request.GET.get('codigo', '')
    if not codigo:
        return JsonResponse({'error': 'Código de barras no proporcionado'}, status=400)
    
    try:
        producto = Producto.objects.get(codigo_barras=codigo)
        # Verificar si tiene ofertas activas
        oferta = Oferta.objects.filter(
            producto=producto,
            activa=True,
            fecha_inicio__lte=timezone.now().date(),
            fecha_fin__gte=timezone.now().date()
        ).first()
        
        precio_oferta = None
        if oferta:
            descuento = producto.precio * (oferta.porcentaje_descuento / 100)
            precio_oferta = producto.precio - descuento
        
        return JsonResponse({
            'id': producto.id,
            'nombre': producto.nombre,
            'precio': float(producto.precio),
            'precio_oferta': float(precio_oferta) if precio_oferta else None,
            'stock': producto.stock
        })
    except Producto.DoesNotExist:
        return JsonResponse({'error': 'Producto no encontrado'}, status=404)

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
@user_passes_test(is_superuser, login_url='home') # Proteger vista de gestión
def gestionar_inventario(request):
    # Verificar si el acceso fue concedido a través de la verificación de contraseña
    if not request.session.get('inventory_access_granted', False):
        messages.warning(request, 'Debes verificar tu contraseña para acceder a la gestión de inventario.')
        request.session['inventory_access_granted'] = False
        return redirect('home')

    request.session['inventory_access_granted'] = False # Limpiar flag

    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'add_lote':
            try:
                proveedor = get_object_or_404(Proveedor, id=request.POST.get('proveedor'))
                Lote.objects.create(
                    code_lote=request.POST.get('code_lote'),
                    proveedor=proveedor,
                    fecha_vencimiento=request.POST.get('fecha_vencimiento') or None
                )
                messages.success(request, 'Lote añadido correctamente.')
            except Exception as e:
                messages.error(request, f'Error al añadir lote: {e}')
            return redirect('gestionar_inventario')

        elif action == 'edit_lote':
            try:
                lote_id = request.POST.get('lote_id')
                lote = get_object_or_404(Lote, id=lote_id)
                lote.code_lote = request.POST.get('code_lote')
                lote.proveedor = get_object_or_404(Proveedor, id=request.POST.get('proveedor'))
                lote.fecha_vencimiento = request.POST.get('fecha_vencimiento') or None
                lote.save()
                messages.success(request, f'Lote {lote.code_lote} actualizado correctamente.')
            except Exception as e:
                messages.error(request, f'Error al actualizar lote: {e}')
            return redirect('gestionar_inventario')

        elif action == 'delete_lote':
            try:
                lote_id = request.POST.get('lote_id')
                lote = get_object_or_404(Lote, id=lote_id)
                code_lote = lote.code_lote
                lote.delete()
                messages.success(request, f'Lote {code_lote} eliminado correctamente.')
            except Exception as e:
                messages.error(request, f'Error al eliminar lote: {e}')
            return redirect('gestionar_inventario')

        elif action == 'assign_productos':
            try:
                lote_id = request.POST.get('lote_id')
                productos_ids = request.POST.getlist('productos_ids')
                cantidades = request.POST.getlist('cantidades[]', [])
                
                lote = get_object_or_404(Lote, id=lote_id)
                productos_a_asignar = Producto.objects.filter(id__in=productos_ids)
                
                with transaction.atomic(): # Asegurar atomicidad
                    # Si se proporcionaron cantidades individuales para cada producto
                    if cantidades and len(cantidades) == len(productos_ids):
                        for i, producto in enumerate(productos_a_asignar):
                            cantidad = int(cantidades[i])
                            producto.stock += cantidad
                            producto.save()
                            # Guardar la relación con la cantidad específica
                            # Aquí podríamos usar una tabla intermedia personalizada si existiera
                            lote.productos.add(producto)
                    else:
                        # Usar la cantidad general para todos los productos
                        cantidad = int(request.POST.get('cantidad', 1))
                        for producto in productos_a_asignar:
                            producto.stock += cantidad
                            producto.save()
                            lote.productos.add(producto)
                
                messages.success(request, f'{len(productos_a_asignar)} producto(s) añadidos al lote {lote.code_lote} y stock actualizado.')
            except Exception as e:
                messages.error(request, f'Error al asignar productos al lote: {e}')
            return redirect('gestionar_inventario')

        elif action == 'ver_productos_lote':
            try:
                lote_id = request.POST.get('lote_id')
                lote = get_object_or_404(Lote, id=lote_id)
                productos = lote.productos.all()
                return render(request, 'Tienda/productos_lote.html', {
                    'lote': lote,
                    'productos': productos
                })
            except Exception as e:
                messages.error(request, f'Error al ver productos del lote: {e}')
                return redirect('gestionar_inventario')

    lotes = Lote.objects.all().order_by('-fecha_registro')
    proveedores = Proveedor.objects.all()
    productos_disponibles = Producto.objects.all()
    return render(request, 'Tienda/gestionar_inventario.html', {
        'lotes': lotes,
        'proveedores': proveedores,
        'productos_disponibles': productos_disponibles
    })

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