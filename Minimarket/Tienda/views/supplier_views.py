from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import JsonResponse
from django.contrib.auth import authenticate
from ..models import Proveedor, Lote, Registro_compra_proveedor
import re
from datetime import datetime, timedelta

def is_superuser(user):
    return user.is_superuser

def validar_rut_chileno(rut_completo):
    import re
    # Solo acepta formato XXXXXXXX-X
    if not re.match(r"^[0-9]+[-|‐]{1}[0-9kK]{1}$", rut_completo):
        return False
    tmp = rut_completo.split('-')
    if len(tmp) != 2:
        return False
    rut = tmp[0]
    digv = tmp[1].upper()
    def dv(T):
        M = 0
        S = 1
        T = int(T)
        while T:
            S = (S + T % 10 * (9 - M % 6)) % 11
            M += 1
            T //= 10
        return str(S - 1) if S != 1 else 'K'
    return dv(rut).upper() == digv

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
                nombre = request.POST.get('nombre_proveedor', '').strip()
                direccion = request.POST.get('direccion', '').strip()
                telefono = request.POST.get('telefono', '').strip()
                rut = request.POST.get('rut', '').strip()
                verify_digit = request.POST.get('verify_digit', '').strip().upper()
                # Validaciones
                if not nombre:
                    raise ValueError('El nombre no puede estar vacío o solo contener espacios.')
                if not rut or not verify_digit:
                    raise ValueError('El RUT y el dígito verificador no pueden estar vacíos.')
                if not rut.isdigit():
                    raise ValueError('El RUT debe ser numérico.')
                if not re.match(r'^[0-9kK]$', verify_digit):
                    raise ValueError('El dígito verificador debe ser un número o "K".')
                rut_int = int(rut)
                # Validar RUT chileno
                def dv(T):
                    M = 0
                    S = 1
                    T = int(T)
                    while T:
                        S = (S + T % 10 * (9 - M % 6)) % 11
                        M += 1
                        T //= 10
                    if S == 0:
                        return 'K'
                    elif S == 1:
                        return '0'
                    else:
                        return str(11 - S)
                dv_result = dv(rut_int).upper()
                verify_digit_upper = verify_digit.upper()
                if not ((dv_result == verify_digit_upper) or (dv_result == 'K' and verify_digit_upper == 'K') or (dv_result == '0' and verify_digit_upper == '0')):
                    raise ValueError('El RUT ingresado no es válido para Chile.')
                direccion = request.POST.get('direccion', '').strip()
                direccion_is_null = not direccion
                if direccion == '':
                    raise ValueError('No puedes ingresar solo espacios en la dirección.')
                    telefono_is_null = not telefono
                if telefono and (not telefono.isdigit() or not (7 <= len(telefono) <= 10)):
                    raise ValueError('El teléfono debe tener entre 7 y 10 dígitos numéricos.')
                if direccion_is_null and telefono_is_null:
                    raise ValueError('Debe ingresar al menos dirección o teléfono (uno puede ser nulo, pero no ambos).')
                proveedor = Proveedor.objects.create(
                    nombre_proveedor=nombre,
                    direccion=direccion if direccion else None,
                    telefono=int(telefono) if telefono else None,
                    rut=rut_int,
                    verify_digit=verify_digit
                )
                if is_ajax:
                    return JsonResponse({
                        'success': True,
                        'message': 'Proveedor añadido correctamente.',
                        'proveedor': {
                            'id': proveedor.id,
                            'nombre_proveedor': proveedor.nombre_proveedor
                        }
                    })
                messages.success(request, 'Proveedor añadido correctamente.')
            except Exception as e:
                if is_ajax:
                    return JsonResponse({
                        'success': False,
                        'message': str(e)
                    }, status=400)
                messages.error(request, f'Error al añadir proveedor: {e}')
                if is_ajax:
                    return JsonResponse({
                        'success': False,
                        'message': f'Error al añadir proveedor: {e}'
                    }, status=400)
        elif action == 'edit_proveedor' and proveedor_id:
            try:
                proveedor = get_object_or_404(Proveedor, id=proveedor_id)
                nombre = request.POST.get('nombre_proveedor', '').strip()
                direccion = request.POST.get('direccion', '').strip()
                if direccion == '':
                    raise ValueError('No puedes ingresar solo espacios en la dirección.')
                telefono = request.POST.get('telefono', '').strip()
                rut = request.POST.get('rut', '').strip()
                verify_digit = request.POST.get('verify_digit', '').strip().upper()
                # Validaciones
                if not nombre:
                    raise ValueError('El nombre no puede estar vacío o solo contener espacios.')
                if not rut or not verify_digit:
                    raise ValueError('El RUT y el dígito verificador no pueden estar vacíos.')
                if not rut.isdigit():
                    raise ValueError('El RUT debe ser numérico.')
                if not re.match(r'^[0-9kK]$', verify_digit):
                    raise ValueError('El dígito verificador debe ser un número o "K".')
                rut_int = int(rut)
                def dv(T):
                    M = 0
                    S = 1
                    T = int(T)
                    while T:
                        S = (S + T % 10 * (9 - M % 6)) % 11
                        M += 1
                        T //= 10
                    if S == 0:
                        return 'K'
                    elif S == 1:
                        return '0'
                    else:
                        return str(11 - S)
                dv_result = dv(rut_int).upper()
                verify_digit_upper = verify_digit.upper()
                if not ((dv_result == verify_digit_upper) or (dv_result == 'K' and verify_digit_upper == 'K') or (dv_result == '0' and verify_digit_upper == '0')):
                    raise ValueError('El RUT ingresado no es válido para Chile.')
                direccion_is_null = not direccion
                telefono_is_null = not telefono
                if direccion and direccion.isspace():
                    raise ValueError('La dirección no puede contener solo espacios.')
                if telefono and (not telefono.isdigit() or not (7 <= len(telefono) <= 10)):
                    raise ValueError('El teléfono debe tener entre 7 y 10 dígitos numéricos.')
                if direccion_is_null and telefono_is_null:
                    raise ValueError('Debe ingresar al menos dirección o teléfono (uno puede ser nulo, pero no ambos).')
                proveedor.nombre_proveedor = nombre
                proveedor.direccion = direccion if direccion else None
                proveedor.telefono = int(telefono) if telefono else None
                proveedor.rut = rut_int
                proveedor.verify_digit = verify_digit
                proveedor.save()
                if is_ajax:
                    return JsonResponse({
                        'success': True,
                        'message': f'Proveedor "{proveedor.nombre_proveedor}" actualizado correctamente.'
                    })
                messages.success(request, f'Proveedor "{proveedor.nombre_proveedor}" actualizado correctamente.')
            except Exception as e:
                if is_ajax:
                    return JsonResponse({
                        'success': False,
                        'message': str(e)
                    }, status=400)
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