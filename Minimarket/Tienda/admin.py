from django.contrib import admin
from .models import Minimercado, Proveedor, Lote, Producto, Oferta, Oferta_vencimiento, Oferta_producto, Venta, DetalleVenta

# Register your models here.

class MinimercadoAdmin(admin.ModelAdmin):
    search_fields = ['nombre_minimercado']
    list_filter = ['fecha_creacion']
    list_per_page = 15

class ProveedorAdmin(admin.ModelAdmin):
    search_fields = ['nombre_proveedor', 'direccion', 'telefono', 'rut']
    list_display = ('nombre_proveedor', 'rut', 'direccion', 'telefono')
    list_per_page = 15

class LoteAdmin(admin.ModelAdmin):
    search_fields = ['code_lote', 'proveedor__nombre_proveedor']
    list_filter = ['proveedor']
    list_per_page = 15

class ProductoAdmin(admin.ModelAdmin):
    search_fields = ['nombre', 'codigo_barras']
    list_display = ('nombre', 'codigo_barras', 'stock', 'precio', 'costo', 'minimal_stock') # Mostrar campos relevantes
    list_per_page = 15

class OfertaAdmin(admin.ModelAdmin):
    search_fields = ['tipo_oferta']
    list_filter = ['fecha_inicio', 'fecha_fin']
    list_display = ('tipo_oferta', 'fecha_inicio', 'fecha_fin', 'descuento_porcetaje')
    list_per_page = 15

class OfertaVencimientoAdmin(admin.ModelAdmin):
    search_fields = ['producto_id__nombre', 'new_code_bar']
    list_filter = ['oferta_id']
    list_display = ('producto_id', 'oferta_id', 'cantidad', 'new_code_bar')
    list_per_page = 15

class OfertaProductoAdmin(admin.ModelAdmin):
    search_fields = ['producto_id__nombre']
    list_filter = ['oferta_id']
    list_display = ('producto_id', 'oferta_id')
    list_per_page = 15

class VentaAdmin(admin.ModelAdmin):
    search_fields = ['empleado__username', 'id']
    list_filter = ['fecha', 'empleado']
    list_display = ('id', 'empleado', 'fecha', 'total')
    list_per_page = 15

class DetalleVentaAdmin(admin.ModelAdmin):
    search_fields = ['venta__id', 'producto__nombre']
    list_filter = ['venta', 'producto']
    list_display = ('venta', 'producto', 'cantidad', 'precio_unitario')
    list_per_page = 15

admin.site.register(Minimercado, MinimercadoAdmin)
admin.site.register(Proveedor, ProveedorAdmin)
admin.site.register(Lote, LoteAdmin)
admin.site.register(Producto, ProductoAdmin)
admin.site.register(Oferta, OfertaAdmin)
admin.site.register(Oferta_vencimiento, OfertaVencimientoAdmin)
admin.site.register(Oferta_producto, OfertaProductoAdmin)
admin.site.register(Venta, VentaAdmin)
admin.site.register(DetalleVenta, DetalleVentaAdmin)
