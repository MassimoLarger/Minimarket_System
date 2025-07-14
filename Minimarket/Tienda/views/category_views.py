from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import JsonResponse
from django.db import IntegrityError
from ..models import Categoria, Producto

def is_superuser(user):
    return user.is_superuser

@login_required
@user_passes_test(is_superuser, login_url='home')
def gestionar_categorias(request):
    if request.method == 'POST':
        action = request.POST.get('action')
        categoria_id = request.POST.get('categoria_id')
        is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
        if action == 'add_categoria':
            try:
                nombre = request.POST.get('nombre', '').strip()
                if not nombre:
                    raise ValueError('El nombre de la categoría no puede estar vacío o solo contener espacios.')
                categoria = Categoria.objects.create(nombre=nombre)
                if is_ajax:
                    return JsonResponse({'success': True, 'message': 'Categoría añadida correctamente.', 'categoria': {'id': categoria.id, 'nombre': categoria.nombre}})
                messages.success(request, 'Categoría añadida correctamente.')
            except IntegrityError as e:
                error_message = str(e)
                if 'UNIQUE constraint failed' in error_message and 'nombre' in error_message:
                    custom_message = 'Ya existe una categoría con este nombre. Por favor, ingrese un nombre diferente.'
                    if is_ajax:
                        return JsonResponse({
                            'success': False,
                            'message': custom_message,
                            'error_type': 'unique_constraint',
                            'field': 'nombre'
                        }, status=400)
                    else:
                        messages.error(request, custom_message)
                else:
                    if is_ajax:
                        return JsonResponse({'success': False, 'message': str(e)}, status=400)
                    messages.error(request, f'Error al añadir categoría: {e}')
            except Exception as e:
                if is_ajax:
                    return JsonResponse({'success': False, 'message': str(e)}, status=400)
                messages.error(request, f'Error al añadir categoría: {e}')
        elif action == 'edit_categoria' and categoria_id:
            try:
                categoria = get_object_or_404(Categoria, id=categoria_id)
                nombre = request.POST.get('nombre', '').strip()
                if not nombre:
                    raise ValueError('El nombre de la categoría no puede estar vacío o solo contener espacios.')
                categoria.nombre = nombre
                categoria.save()
                if is_ajax:
                    return JsonResponse({'success': True, 'message': f'Categoría "{categoria.nombre}" actualizada correctamente.'})
                messages.success(request, f'Categoría "{categoria.nombre}" actualizada correctamente.')
            except IntegrityError as e:
                error_message = str(e)
                if 'UNIQUE constraint failed' in error_message and 'nombre' in error_message:
                    custom_message = 'Ya existe una categoría con este nombre. Por favor, ingrese un nombre diferente.'
                    if is_ajax:
                        return JsonResponse({
                            'success': False,
                            'message': custom_message,
                            'error_type': 'unique_constraint',
                            'field': 'nombre'
                        }, status=400)
                    else:
                        messages.error(request, custom_message)
                else:
                    if is_ajax:
                        return JsonResponse({'success': False, 'message': str(e)}, status=400)
                    messages.error(request, f'Error al actualizar categoría: {e}')
            except Exception as e:
                if is_ajax:
                    return JsonResponse({'success': False, 'message': str(e)}, status=400)
                messages.error(request, f'Error al actualizar categoría: {e}')
        elif action == 'delete_categoria' and categoria_id:
            try:
                categoria = get_object_or_404(Categoria, id=categoria_id)
                nombre_categoria = categoria.nombre
                if Producto.objects.filter(categoria=categoria).exists():
                    mensaje = f'No se puede eliminar "{nombre_categoria}" porque tiene productos asociados.'
                    if is_ajax:
                        return JsonResponse({'success': False, 'message': mensaje}, status=400)
                    messages.error(request, mensaje)
                    return redirect('gestionar_categorias')
                categoria.delete()
                mensaje = f'Categoría "{nombre_categoria}" eliminada correctamente.'
                if is_ajax:
                    return JsonResponse({'success': True, 'message': mensaje})
                messages.success(request, mensaje)
            except Exception as e:
                mensaje = f'Error al eliminar categoría: {str(e)}'
                if is_ajax:
                    return JsonResponse({'success': False, 'message': mensaje}, status=400)
                messages.error(request, mensaje)
        
        elif action == 'get_categoria':
            try:
                categoria = get_object_or_404(Categoria, id=categoria_id)
                return JsonResponse({
                    'id': categoria.id,
                    'nombre': categoria.nombre
                })
            except Exception as e:
                return JsonResponse({'error': str(e)}, status=400)

        if is_ajax:
            return JsonResponse({'success': False, 'message': 'Acción no válida'}, status=400)
    categorias = Categoria.objects.all().order_by('nombre')
    context = {
        'categorias': categorias,
        'es_superadmin': request.user.is_superuser
    }
    return render(request, 'Tienda/categorias.html', context)