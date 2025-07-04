from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth import authenticate
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
import json
from ..models import SeccionBodega, SeccionLote, Lote

def is_superuser(user):
    return user.is_superuser

@login_required
def verify_password_warehouse(request):
    if not request.user.is_superuser:
        messages.error(request, 'No tienes permiso para realizar esta acción.')
        return redirect('home')

    if request.method == 'POST':
        password = request.POST.get('password')
        user = authenticate(request, username=request.user.username, password=password)
        if user is not None:
            request.session['warehouse_access_granted'] = True
            messages.success(request, 'Contraseña verificada. Accediendo a gestión de bodega.')
            return redirect('gestionar_bodega')
        else:
            messages.error(request, 'Contraseña incorrecta. Inténtalo de nuevo.')
            return redirect('home')
    else:
        return redirect('home')

@login_required
@user_passes_test(is_superuser, login_url='home')
def gestionar_bodega(request):
    if not request.session.get('warehouse_access_granted', False):
        messages.warning(request, 'Debes verificar tu contraseña para acceder a la gestión de bodega.')
        return redirect('home')
    
    # Obtener todas las secciones de bodega
    secciones = SeccionBodega.objects.filter(activa=True)
    # Obtener lotes que no están asignados a ninguna sección
    lotes_asignados_ids = SeccionLote.objects.values_list('lote_id', flat=True)
    lotes_disponibles = Lote.objects.select_related('proveedor').exclude(id__in=lotes_asignados_ids)
    
    context = {
        'secciones': secciones,
        'lotes_disponibles': lotes_disponibles,
    }
    
    return render(request, 'Tienda/gestionar_bodega.html', context)

@login_required
@user_passes_test(is_superuser, login_url='home')
@csrf_exempt
@require_http_methods(["POST"])
def crear_seccion(request):
    """Crear una nueva sección de bodega"""
    try:
        data = json.loads(request.body)
        
        seccion = SeccionBodega.objects.create(
            nombre=data.get('nombre', 'Nueva Sección'),
            descripcion=data.get('descripcion', ''),
            tipo_forma='rectangulo',  # Todas las secciones son auto-ajustables
            posicion_x=data.get('posicion_x', 50),
            posicion_y=data.get('posicion_y', 50),
            ancho=data.get('ancho', 120),
            alto=data.get('alto', 80),
            color=data.get('color', '#3498db')
        )
        
        return JsonResponse({
            'success': True,
            'seccion': {
                'id': seccion.id,
                'nombre': seccion.nombre,
                'descripcion': seccion.descripcion,
                'tipo_forma': seccion.tipo_forma,
                'posicion_x': seccion.posicion_x,
                'posicion_y': seccion.posicion_y,
                'ancho': seccion.ancho,
                'alto': seccion.alto,
                'color': seccion.color
            }
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

@login_required
@user_passes_test(is_superuser, login_url='home')
def obtener_secciones(request):
    """Obtener todas las secciones de bodega en formato JSON"""
    try:
        secciones = SeccionBodega.objects.filter(activa=True)
        secciones_data = []
        
        for seccion in secciones:
            secciones_data.append({
                'id': seccion.id,
                'nombre': seccion.nombre,
                'descripcion': seccion.descripcion,
                'tipo_forma': seccion.tipo_forma,
                'posicion_x': seccion.posicion_x,
                'posicion_y': seccion.posicion_y,
                'ancho': seccion.ancho,
                'alto': seccion.alto,
                'color': seccion.color
            })
        
        return JsonResponse({
            'success': True,
            'secciones': secciones_data
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

@login_required
@user_passes_test(is_superuser, login_url='home')
@csrf_exempt
@require_http_methods(["POST"])
def actualizar_seccion(request, seccion_id):
    """Actualizar una sección de bodega existente"""
    try:
        print(f"[DEBUG] Actualizando sección {seccion_id}")
        seccion = get_object_or_404(SeccionBodega, id=seccion_id)
        data = json.loads(request.body)
        
        print(f"[DEBUG] Datos recibidos: {data}")
        print(f"[DEBUG] Valores antes del cambio - ancho: {seccion.ancho}, alto: {seccion.alto}")
        
        # Guardar valores anteriores para comparación
        valores_anteriores = {
            'nombre': seccion.nombre,
            'ancho': seccion.ancho,
            'alto': seccion.alto,
            'posicion_x': seccion.posicion_x,
            'posicion_y': seccion.posicion_y
        }
        
        seccion.nombre = data.get('nombre', seccion.nombre)
        seccion.descripcion = data.get('descripcion', seccion.descripcion)
        seccion.tipo_forma = data.get('tipo_forma', seccion.tipo_forma)
        seccion.posicion_x = data.get('posicion_x', seccion.posicion_x)
        seccion.posicion_y = data.get('posicion_y', seccion.posicion_y)
        seccion.ancho = data.get('ancho', seccion.ancho)
        seccion.alto = data.get('alto', seccion.alto)
        seccion.color = data.get('color', seccion.color)
        
        print(f"[DEBUG] Valores después del cambio - ancho: {seccion.ancho}, alto: {seccion.alto}")
        
        # Forzar el guardado con update_fields específicos
        seccion.save(update_fields=['nombre', 'descripcion', 'tipo_forma', 'posicion_x', 'posicion_y', 'ancho', 'alto', 'color'])
        print(f"[DEBUG] Sección guardada exitosamente")
        
        # Verificar que los cambios se guardaron
        seccion.refresh_from_db()
        print(f"[DEBUG] Valores después de refresh_from_db - ancho: {seccion.ancho}, alto: {seccion.alto}")
        
        # Verificar si realmente cambió algo
        cambios_detectados = {
            'nombre': valores_anteriores['nombre'] != seccion.nombre,
            'ancho': valores_anteriores['ancho'] != seccion.ancho,
            'alto': valores_anteriores['alto'] != seccion.alto,
            'posicion_x': valores_anteriores['posicion_x'] != seccion.posicion_x,
            'posicion_y': valores_anteriores['posicion_y'] != seccion.posicion_y
        }
        print(f"[DEBUG] Cambios detectados: {cambios_detectados}")
        
        return JsonResponse({
            'success': True,
            'debug_info': {
                'valores_anteriores': valores_anteriores,
                'valores_actuales': {
                    'nombre': seccion.nombre,
                    'ancho': seccion.ancho,
                    'alto': seccion.alto,
                    'posicion_x': seccion.posicion_x,
                    'posicion_y': seccion.posicion_y
                },
                'cambios_detectados': cambios_detectados
            },
            'seccion': {
                'id': seccion.id,
                'nombre': seccion.nombre,
                'descripcion': seccion.descripcion,
                'tipo_forma': seccion.tipo_forma,
                'posicion_x': seccion.posicion_x,
                'posicion_y': seccion.posicion_y,
                'ancho': seccion.ancho,
                'alto': seccion.alto,
                'color': seccion.color
            }
        })
    except Exception as e:
        print(f"[DEBUG] Error actualizando sección: {str(e)}")
        return JsonResponse({'success': False, 'error': str(e)})

@login_required
@user_passes_test(is_superuser, login_url='home')
@csrf_exempt
@require_http_methods(["DELETE"])
def eliminar_seccion(request, seccion_id):
    """Eliminar una sección de bodega"""
    try:
        seccion = get_object_or_404(SeccionBodega, id=seccion_id)
        seccion.delete()
        
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

@login_required
@user_passes_test(is_superuser, login_url='home')
@csrf_exempt
@require_http_methods(["POST"])
def asignar_lote_seccion(request):
    """Asignar un lote a una sección de bodega"""
    try:
        data = json.loads(request.body)
        seccion_id = data.get('seccion_id')
        lote_id = data.get('lote_id')
        observaciones = data.get('observaciones', '')
        
        seccion = get_object_or_404(SeccionBodega, id=seccion_id)
        lote = get_object_or_404(Lote, id=lote_id)
        
        # Verificar si el lote ya está asignado a otra sección
        asignacion_existente = SeccionLote.objects.filter(lote=lote).first()
        if asignacion_existente:
            return JsonResponse({
                'success': False, 
                'error': f'El lote ya está asignado a la sección: {asignacion_existente.seccion.nombre}'
            })
        
        # Crear la asignación
        asignacion = SeccionLote.objects.create(
            seccion=seccion,
            lote=lote,
            observaciones=observaciones
        )
        
        return JsonResponse({
            'success': True,
            'asignacion': {
                'id': asignacion.id,
                'seccion_nombre': seccion.nombre,
                'lote_codigo': lote.code_lote,
                'fecha_asignacion': asignacion.fecha_asignacion.strftime('%d/%m/%Y %H:%M')
            }
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

@login_required
@user_passes_test(is_superuser, login_url='home')
@csrf_exempt
@require_http_methods(["DELETE"])
def desasignar_lote_seccion(request, asignacion_id):
    """Desasignar un lote de una sección de bodega"""
    try:
        asignacion = get_object_or_404(SeccionLote, id=asignacion_id)
        asignacion.delete()
        
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

@login_required
@user_passes_test(is_superuser, login_url='home')
def obtener_lotes_seccion(request, seccion_id):
    """Obtener los lotes asignados a una sección específica"""
    try:
        seccion = get_object_or_404(SeccionBodega, id=seccion_id)
        asignaciones = SeccionLote.objects.filter(seccion=seccion)
        
        lotes_data = []
        for asignacion in asignaciones:
            lotes_data.append({
                'asignacion_id': asignacion.id,
                'lote_id': asignacion.lote.id,
                'lote_codigo': asignacion.lote.code_lote,
                'proveedor': asignacion.lote.proveedor.nombre_proveedor,
                'fecha_registro': asignacion.lote.fecha_registro.strftime('%d/%m/%Y'),
                'fecha_asignacion': asignacion.fecha_asignacion.strftime('%d/%m/%Y %H:%M'),
                'observaciones': asignacion.observaciones or ''
            })
        
        return JsonResponse({
            'success': True,
            'seccion_nombre': seccion.nombre,
            'lotes': lotes_data
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})