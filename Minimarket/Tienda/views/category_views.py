from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import JsonResponse
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
                nombre = request.POST.get('nombre')
                categoria = Categoria.objects.create(nombre=nombre)
                messages.success(request, 'Categoría añadida correctamente.')
                if is_ajax:
                    return JsonResponse({'success': True, 'message': 'Categoría añadida correctamente.', 'categoria': {'id': categoria.id, 'nombre': categoria.nombre}})
            except Exception as e:
                messages.error(request, f'Error al añadir categoría: {e}')
                if is_ajax:
                    return JsonResponse({'success': False, 'message': f'Error al añadir categoría: {e}'}, status=400)

        elif action == 'edit_categoria' and categoria_id:
            try:
                categoria = get_object_or_404(Categoria, id=categoria_id)
                categoria.nombre = request.POST.get('nombre')
                categoria.save()
                messages.success(request, f'Categoría "{categoria.nombre}" actualizada correctamente.')
                if is_ajax:
                    return JsonResponse({'success': True, 'message': f'Categoría "{categoria.nombre}" actualizada correctamente.'})
            except Exception as e:
                messages.error(request, f'Error al actualizar categoría: {e}')
                if is_ajax:
                    return JsonResponse({'success': False, 'message': f'Error al actualizar categoría: {e}'}, status=400)
        
        elif action == 'delete_categoria' and categoria_id:
            try:
                categoria = get_object_or_404(Categoria, id=categoria_id)
                nombre_categoria = categoria.nombre
                
                if Producto.objects.filter(categoria=categoria).exists():
                    mensaje = f'No se puede eliminar "{nombre_categoria}" porque tiene productos asociados.'
                    messages.error(request, mensaje)
                    return JsonResponse({'success': False, 'message': mensaje}, status=400)
                
                categoria.delete()
                mensaje = f'Categoría "{nombre_categoria}" eliminada correctamente.'
                messages.success(request, mensaje)
                return JsonResponse({'success': True, 'message': mensaje})
                
            except Exception as e:
                mensaje = f'Error al eliminar categoría: {str(e)}'
                messages.error(request, mensaje)
                return JsonResponse({'success': False, 'message': mensaje}, status=400)
        
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