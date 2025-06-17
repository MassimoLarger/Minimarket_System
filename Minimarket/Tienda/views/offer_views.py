from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import JsonResponse
from django.utils import timezone
from django.db import transaction
from ..models import Oferta, Producto, Oferta_producto, Oferta_vencimiento

def is_superuser(user):
    return user.is_superuser

@login_required
def ofertas(request):
    if request.method == 'POST' and request.user.is_superuser:
        action = request.POST.get('action')
        oferta_id = request.POST.get('oferta_id')

        if action == 'save_oferta':
            try:
                with transaction.atomic():
                    if oferta_id:
                        oferta = get_object_or_404(Oferta, id=oferta_id)
                        oferta.tipo_oferta = request.POST.get('tipo_oferta')
                        oferta.descuento_porcetaje = float(request.POST.get('descuento_porcentaje'))
                        oferta.fecha_inicio = request.POST.get('fecha_inicio')
                        oferta.fecha_fin = request.POST.get('fecha_fin')
                        oferta.save()
                        messages.success(request, f'Oferta "{oferta.tipo_oferta}" actualizada.')
                        Oferta_producto.objects.filter(oferta_id=oferta).delete()
                        Oferta_vencimiento.objects.filter(oferta_id=oferta).delete()
                    else:
                        oferta = Oferta.objects.create(
                            tipo_oferta=request.POST.get('tipo_oferta'),
                            descuento_porcetaje=float(request.POST.get('descuento_porcentaje')),
                            fecha_inicio=request.POST.get('fecha_inicio'),
                            fecha_fin=request.POST.get('fecha_fin'),
                            creado_por=request.user
                        )
                        messages.success(request, f'Oferta "{oferta.tipo_oferta}" creada.')

                    productos_oferta_ids = request.POST.getlist('productos_oferta')
                    for producto_id in productos_oferta_ids:
                        producto = get_object_or_404(Producto, id=producto_id)
                        Oferta_producto.objects.create(oferta_id=oferta, producto_id=producto)

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
                        
                return redirect('ofertas')

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

    ofertas_activas = Oferta.objects.filter(fecha_inicio__lte=timezone.now().date(), fecha_fin__gte=timezone.now().date())
    context = {
        'ofertas_activas': ofertas_activas,
        'es_admin': request.user.is_superuser
    }

    if request.user.is_superuser:
        context['todas_ofertas'] = Oferta.objects.all().order_by('-fecha_inicio')
        context['productos'] = Producto.objects.all()

    return render(request, 'Tienda/ofertas.html', context)