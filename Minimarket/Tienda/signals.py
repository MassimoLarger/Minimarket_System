from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.utils import timezone
from datetime import timedelta
from .models import Producto, DetalleVenta, Alert, OfertaProducto, OfertaVencimiento, LoteProducto

@receiver(post_save, sender=DetalleVenta)
def verificar_stock_despues_venta(sender, instance, created, **kwargs):
    """Verifica alertas de stock bajo después de una venta"""
    if created:
        producto = instance.producto
        # Buscar alertas de stock bajo para este producto
        alertas_stock = Alert.objects.filter(
            tipo='stock_bajo',
            producto=producto,
            activa=True,
            estado='activa'
        )
        
        for alerta in alertas_stock:
            if alerta.verificar_condicion():
                # La alerta se activó, podrías enviar notificación aquí
                pass

@receiver(post_save, sender=Producto)
def verificar_stock_producto_actualizado(sender, instance, **kwargs):
    """Verifica alertas cuando se actualiza un producto"""
    # Buscar alertas de stock bajo para este producto
    alertas_stock = Alert.objects.filter(
        tipo='stock_bajo',
        producto=instance,
        activa=True,
        estado='activa'
    )
    
    for alerta in alertas_stock:
        if alerta.verificar_condicion():
            # La alerta se activó
            pass

@receiver(post_save, sender=LoteProducto)
def verificar_vencimiento_lote(sender, instance, **kwargs):
    """Verifica alertas de vencimiento cuando se crea o actualiza un lote"""
    if instance.fecha_vencimiento:
        producto = instance.producto
        # Buscar alertas de vencimiento para este producto
        alertas_vencimiento = Alert.objects.filter(
            tipo='proximo_vencer',
            producto=producto,
            activa=True,
            estado='activa'
        )
        
        for alerta in alertas_vencimiento:
            if alerta.verificar_condicion():
                # La alerta se activó
                pass

@receiver(post_save, sender=OfertaProducto)
@receiver(post_save, sender=OfertaVencimiento)
def verificar_ofertas_terminando(sender, instance, **kwargs):
    """Verifica alertas de ofertas próximas a terminar"""
    # Buscar alertas relacionadas con esta oferta
    if sender == OfertaProducto:
        alertas = Alert.objects.filter(
            tipo='oferta_terminando',
            oferta_producto=instance,
            activa=True,
            estado='activa'
        )
    else:  # OfertaVencimiento
        alertas = Alert.objects.filter(
            tipo='oferta_terminando',
            oferta_vencimiento=instance,
            activa=True,
            estado='activa'
        )
    
    for alerta in alertas:
        if alerta.verificar_condicion():
            # La alerta se activó
            pass

def crear_alertas_automaticas():
    """Función para crear alertas automáticas básicas del sistema"""
    # Crear alerta general de productos bajo stock
    if not Alert.objects.filter(nombre="Productos Bajo Stock General").exists():
        Alert.objects.create(
            nombre="Productos Bajo Stock General",
            tipo="stock_bajo",
            mensaje="Hay productos que han alcanzado su stock mínimo y necesitan reposición.",
            activa=True
        )
    
    # Crear alerta general de productos próximos a vencer
    if not Alert.objects.filter(nombre="Productos Próximos a Vencer").exists():
        Alert.objects.create(
            nombre="Productos Próximos a Vencer",
            tipo="proximo_vencer",
            mensaje="Hay productos en el inventario que están próximos a vencer.",
            dias_anticipacion=7,
            activa=True
        )
    
    # Crear alertas automáticas para ofertas activas
    ofertas_producto = OfertaProducto.objects.filter(activa=True, fecha_fin__isnull=False)
    for oferta in ofertas_producto:
        alerta_nombre = f"Oferta Terminando: {oferta.nombre}"
        if not Alert.objects.filter(nombre=alerta_nombre).exists():
            Alert.objects.create(
                nombre=alerta_nombre,
                tipo="oferta_terminando",
                mensaje=f"La oferta '{oferta.nombre}' está próxima a terminar.",
                oferta_producto=oferta,
                dias_anticipacion=3,
                activa=True
            )
    
    ofertas_vencimiento = OfertaVencimiento.objects.filter(activa=True, fecha_fin__isnull=False)
    for oferta in ofertas_vencimiento:
        alerta_nombre = f"Oferta Vencimiento Terminando: {oferta.nombre}"
        if not Alert.objects.filter(nombre=alerta_nombre).exists():
            Alert.objects.create(
                nombre=alerta_nombre,
                tipo="oferta_terminando",
                mensaje=f"La oferta de vencimiento '{oferta.nombre}' está próxima a terminar.",
                oferta_vencimiento=oferta,
                dias_anticipacion=3,
                activa=True
            )