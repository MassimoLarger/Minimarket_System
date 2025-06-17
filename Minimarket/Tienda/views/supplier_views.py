from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import JsonResponse
from django.contrib.auth import authenticate
from ..models import Proveedor, Lote, Registro_compra_proveedor

def is_superuser(user):
    return user.is_superuser

@login_required
def verify_password_providers(request):
    if not request.user.is_superuser:
        messages.error(request, 'No tienes permiso para realizar esta acción.')
        return redirect('home')

    if request.method == 'POST':
        password = request.POST.get('password')
        user = authenticate(request, username=request.user.username, password=password)
        if user is not None:
            request.session['providers_access_granted'] = True
            messages.success(request, 'Contraseña verificada. Accediendo a gestión de proveedores.')
            return redirect('gestionar_proveedores')
        else:
            messages.error(request, 'Contraseña incorrecta. Inténtalo de nuevo.')
            return redirect('home')
    else:
        return redirect('home')

@login_required
@user_passes_test(is_superuser, login_url='home')
def registro_compra_proveedores(request):
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
@user_passes_test(is_superuser, login_url='home')
def gestionar_proveedores(request):
    if not request.session.get('providers_access_granted', False):
        messages.warning(request, 'Debes verificar tu contraseña para acceder a la gestión de proveedores.')
        request.session['providers_access_granted'] = False
        return redirect('home')
    
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
        
        if is_ajax:
            return JsonResponse({
                'success': False,
                'message': 'Acción no válida'
            }, status=400)
    
    proveedores = Proveedor.objects.all().order_by('nombre_proveedor')
    context = {
        'proveedores': proveedores
    }
    return render(request, 'Tienda/gestionar_proveedores.html', context)