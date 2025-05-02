from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.utils import timezone
from django.contrib.auth.decorators import user_passes_test # Para restringir vistas a admin
from django.db import transaction # Para operaciones atómicas
from .forms import LoginForm
from .models import Producto, Oferta, Venta, DetalleVenta, Proveedor, Lote, Oferta_vencimiento, Oferta_producto
from django.db.models import Q
from django.contrib.auth import update_session_auth_hash # Para mantener sesión tras cambio de contraseña

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
def nueva_venta(request):
    productos = Producto.objects.all()
    return render(request, 'Tienda/nueva_venta.html', {'productos': productos})

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
                        oferta.descuento_porcentaje = request.POST.get('descuento_porcentaje')
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
                            descuento_porcentaje=request.POST.get('descuento_porcentaje'),
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

                    # Gestionar Oferta_vencimiento (simplificado, asume un solo item por ahora)
                    # Se necesitaría JS para manejar múltiples items dinámicamente
                    producto_vencimiento_id = request.POST.get('producto_vencimiento_1')
                    cantidad_vencimiento = request.POST.get('cantidad_vencimiento_1')
                    new_code_bar = request.POST.get('new_code_bar_1')

                    if producto_vencimiento_id and cantidad_vencimiento:
                        producto_venc = get_object_or_404(Producto, id=producto_vencimiento_id)
                        Oferta_vencimiento.objects.create(
                            oferta_id=oferta,
                            producto_id=producto_venc,
                            cantidad=cantidad_vencimiento,
                            new_code_bar=new_code_bar if new_code_bar else None
                        )
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

    # Lógica GET (común para admin y empleado)
    ofertas_activas = Oferta.objects.filter(fecha_inicio__lte=timezone.now().date(), fecha_fin__gte=timezone.now().date())
    context = {
        'ofertas_activas': ofertas_activas,
        'es_admin': request.user.is_superuser
    }

    # Añadir datos extra para admin en GET
    if request.user.is_superuser:
        context['todas_ofertas'] = Oferta.objects.all().order_by('-fecha_creacion')
        context['productos'] = Producto.objects.all()

    return render(request, 'Tienda/ofertas.html', context)

@login_required
def productos(request):
    if request.method == 'POST' and request.user.is_superuser:
        action = request.POST.get('action')
        if action == 'add_producto':
            try:
                Producto.objects.create(
                    nombre=request.POST.get('nombre'),
                    codigo_barras=request.POST.get('codigo_barras'),
                    precio=request.POST.get('precio'),
                    costo=request.POST.get('costo'),
                    stock=request.POST.get('stock', 0),
                    minimal_stock=request.POST.get('minimal_stock', 0),
                    descripcion=request.POST.get('descripcion', '')
                )
                messages.success(request, 'Producto añadido correctamente.')
            except Exception as e:
                # Considerar validación de código de barras único
                if 'UNIQUE constraint failed' in str(e):
                     messages.error(request, f'Error al añadir producto: Ya existe un producto con el código de barras {request.POST.get("codigo_barras")}.')
                else:
                    messages.error(request, f'Error al añadir producto: {e}')
            return redirect('productos')
        # Aquí iría la lógica para editar o eliminar si se implementa en esta vista

    # Lógica GET existente
    query = request.GET.get('q', '')
    codigo_barras = request.GET.get('codigo', '')
    
    if codigo_barras:
        productos_lista = Producto.objects.filter(codigo_barras=codigo_barras)
    elif query:
        productos_lista = Producto.objects.filter(
            Q(nombre__icontains=query) | 
            Q(descripcion__icontains=query) | 
            Q(codigo_barras__icontains=query)
        )
    else:
        productos_lista = Producto.objects.all()
    
    return render(request, 'Tienda/productos.html', {
        'productos': productos_lista,
        'query': query,
        'es_admin': request.user.is_superuser
    })

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

        elif action == 'assign_productos':
            try:
                lote_id = request.POST.get('lote_id')
                productos_ids = request.POST.getlist('productos_ids')
                cantidad = int(request.POST.get('cantidad', 1))
                
                lote = get_object_or_404(Lote, id=lote_id)
                productos_a_asignar = Producto.objects.filter(id__in=productos_ids)
                
                with transaction.atomic(): # Asegurar atomicidad
                    for producto in productos_a_asignar:
                        producto.stock += cantidad
                        producto.save()
                        lote.productos.add(producto) # Añadir a la relación M2M
                
                messages.success(request, f'{len(productos_a_asignar)} producto(s) añadidos al lote {lote.code_lote} y stock actualizado.')
            except Exception as e:
                messages.error(request, f'Error al asignar productos al lote: {e}')
            return redirect('gestionar_inventario')

    lotes = Lote.objects.all().order_by('-fecha_registro') # Corregido orden
    proveedores = Proveedor.objects.all()
    productos_disponibles = Producto.objects.all() # Para el modal
    return render(request, 'Tienda/gestionar_inventario.html', {
        'lotes': lotes,
        'proveedores': proveedores,
        'productos_disponibles': productos_disponibles # Pasar productos al template
    })

@login_required
@user_passes_test(is_superuser, login_url='home') # Proteger y redirigir si no es superuser
def gestionar_proveedores(request):
    # Verificar si el acceso fue concedido a través de la verificación de contraseña
    if not request.session.get('providers_access_granted', False):
        messages.warning(request, 'Debes verificar tu contraseña para acceder a la gestión de proveedores.')
        # Asegurarse de limpiar el flag si existe por alguna razón
        request.session['providers_access_granted'] = False
        return redirect('home')

    # Limpiar el flag de sesión después de verificarlo para requerir verificación la próxima vez
    request.session['providers_access_granted'] = False
    if request.method == 'POST':
        action = request.POST.get('action')
        proveedor_id = request.POST.get('proveedor_id')

        if action == 'add_proveedor':
            try:
                Proveedor.objects.create(
                    nombre_proveedor=request.POST.get('nombre_proveedor'),
                    direccion=request.POST.get('direccion'),
                    telefono=request.POST.get('telefono'),
                    email=request.POST.get('email') or None
                )
                messages.success(request, 'Proveedor añadido correctamente.')
            except Exception as e:
                messages.error(request, f'Error al añadir proveedor: {e}')

        elif action == 'edit_proveedor' and proveedor_id:
            try:
                proveedor = get_object_or_404(Proveedor, id=proveedor_id)
                proveedor.nombre_proveedor = request.POST.get('nombre_proveedor')
                proveedor.direccion = request.POST.get('direccion')
                proveedor.telefono = request.POST.get('telefono')
                proveedor.email = request.POST.get('email') or None
                proveedor.save()
                messages.success(request, 'Proveedor actualizado correctamente.')
            except Exception as e:
                messages.error(request, f'Error al actualizar proveedor: {e}')

        elif action == 'delete_proveedor' and proveedor_id:
            try:
                proveedor = get_object_or_404(Proveedor, id=proveedor_id)
                nombre_proveedor = proveedor.nombre_proveedor
                proveedor.delete()
                messages.success(request, f'Proveedor "{nombre_proveedor}" eliminado.')
            except Exception as e:
                # Considerar protección de eliminación si hay lotes asociados
                messages.error(request, f'Error al eliminar proveedor: {e}')
        
        return redirect('gestionar_proveedores') # Redirigir después de cualquier acción POST

    proveedores = Proveedor.objects.all().order_by('nombre_proveedor')
    context = {
        'proveedores': proveedores
    }
    return render(request, 'Tienda/gestionar_proveedores.html', context)
