from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import JsonResponse
from django.db import transaction, IntegrityError
from ..models import Producto, DetalleVenta, LoteProducto, Categoria

def is_superuser(user):
    return user.is_superuser

@login_required
@user_passes_test(is_superuser, login_url='home')
def gestionar_productos(request):
    productos = Producto.objects.all().order_by('nombre')
    if request.method == 'POST':
        action = request.POST.get('action')
        producto_id = request.POST.get('producto_id')
        is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
        if action == 'add_producto':
            try:
                nombre = request.POST.get('nombre', '').strip()
                if not nombre:
                    raise ValueError('El nombre del producto no puede estar vacío o solo contener espacios.')
                codigo_barras = request.POST.get('codigo_barras', '').strip()
                if not codigo_barras.isdigit():
                    raise ValueError('El código de barras debe ser un número entero.')
                producto = Producto.objects.create(
                    nombre=nombre,
                    codigo_barras=int(codigo_barras),
                    stock=int(request.POST.get('stock', 0)),
                    precio=float(request.POST.get('precio', 0)),
                    costo=float(request.POST.get('costo', 0)),
                    minimal_stock=int(request.POST.get('minimal_stock', 0)),
                    categoria_id=request.POST.get('categoria') if request.POST.get('categoria') else None
                )
                if is_ajax:
                    return JsonResponse({
                        'success': True,
                        'message': 'Producto añadido correctamente.',
                        'producto': {
                            'id': producto.id,
                            'nombre': producto.nombre
                        }
                    })
                messages.success(request, 'Producto añadido correctamente.')
            except IntegrityError as e:
                error_message = str(e)
                if 'UNIQUE constraint failed' in error_message:
                    if 'nombre' in error_message:
                        custom_message = 'Ya existe un producto con este nombre. Por favor, ingrese un nombre diferente.'
                        field = 'nombre'
                    elif 'codigo_barras' in error_message:
                        custom_message = 'Ya existe un producto con este código de barras. Por favor, ingrese un código diferente.'
                        field = 'codigo_barras'
                    else:
                        custom_message = 'Este valor ya existe. Por favor, ingrese un valor diferente.'
                        field = 'unknown'
                    
                    if is_ajax:
                        return JsonResponse({
                            'success': False,
                            'message': custom_message,
                            'error_type': 'unique_constraint',
                            'field': field
                        }, status=400)
                    else:
                        messages.error(request, custom_message)
                else:
                    if is_ajax:
                        return JsonResponse({
                            'success': False,
                            'message': str(e)
                        }, status=400)
                    messages.error(request, f'Error al añadir producto: {e}')
            except Exception as e:
                if is_ajax:
                    return JsonResponse({
                        'success': False,
                        'message': str(e)
                    }, status=400)
                messages.error(request, f'Error al añadir producto: {e}')
        elif action == 'edit_producto' and producto_id:
            try:
                producto = get_object_or_404(Producto, id=producto_id)
                nombre = request.POST.get('nombre', '').strip()
                if not nombre:
                    raise ValueError('El nombre del producto no puede estar vacío o solo contener espacios.')
                codigo_barras = request.POST.get('codigo_barras', '').strip()
                if not codigo_barras.isdigit():
                    raise ValueError('El código de barras debe ser un número entero.')
                producto.nombre = nombre
                producto.codigo_barras = int(codigo_barras)
                producto.stock = int(request.POST.get('stock', 0))
                producto.precio = float(request.POST.get('precio', 0))
                producto.costo = float(request.POST.get('costo', 0))
                producto.minimal_stock = int(request.POST.get('minimal_stock', 0))
                producto.categoria_id = request.POST.get('categoria') if request.POST.get('categoria') else None
                producto.save()
                if is_ajax:
                    return JsonResponse({
                        'success': True,
                        'message': f'Producto "{producto.nombre}" actualizado correctamente.'
                    })
                messages.success(request, f'Producto "{producto.nombre}" actualizado correctamente.')
            except IntegrityError as e:
                error_message = str(e)
                if 'UNIQUE constraint failed' in error_message:
                    if 'nombre' in error_message:
                        custom_message = 'Ya existe un producto con este nombre. Por favor, ingrese un nombre diferente.'
                        field = 'nombre'
                    elif 'codigo_barras' in error_message:
                        custom_message = 'Ya existe un producto con este código de barras. Por favor, ingrese un código diferente.'
                        field = 'codigo_barras'
                    else:
                        custom_message = 'Este valor ya existe. Por favor, ingrese un valor diferente.'
                        field = 'unknown'
                    
                    if is_ajax:
                        return JsonResponse({
                            'success': False,
                            'message': custom_message,
                            'error_type': 'unique_constraint',
                            'field': field
                        }, status=400)
                    else:
                        messages.error(request, custom_message)
                else:
                    if is_ajax:
                        return JsonResponse({
                            'success': False,
                            'message': str(e)
                        }, status=400)
                    messages.error(request, f'Error al actualizar producto: {e}')
            except Exception as e:
                if is_ajax:
                    return JsonResponse({
                        'success': False,
                        'message': str(e)
                    }, status=400)
                messages.error(request, f'Error al actualizar producto: {e}')
        elif action == 'delete_producto' and producto_id:
            try:
                producto = get_object_or_404(Producto, id=producto_id)
                nombre_producto = producto.nombre
                en_ventas = DetalleVenta.objects.filter(producto=producto).exists()
                en_lotes = LoteProducto.objects.filter(producto=producto).exists()
                if en_ventas or en_lotes:
                    mensaje = f'No se puede eliminar "{nombre_producto}" porque tiene registros relacionados.'
                    if is_ajax:
                        return JsonResponse({'success': False, 'message': mensaje}, status=400)
                    messages.error(request, mensaje)
                    return redirect('gestionar_productos')
                producto.delete()
                mensaje = f'Producto "{nombre_producto}" eliminado correctamente.'
                if is_ajax:
                    return JsonResponse({'success': True, 'message': mensaje})
                messages.success(request, mensaje)
            except Exception as e:
                mensaje = f'Error al eliminar producto: {str(e)}'
                if is_ajax:
                    return JsonResponse({'success': False, 'message': mensaje}, status=400)
                messages.error(request, mensaje)
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
        if is_ajax:
            return JsonResponse({
                'success': False,
                'message': 'Acción no válida'
            }, status=400)
    productos = Producto.objects.all().order_by('nombre')
    context = {
        'productos': productos,
        'es_superadmin': request.user.is_superuser,
        'categorias': Categoria.objects.all().order_by('nombre')
    }
    return render(request, 'Tienda/productos.html', context)