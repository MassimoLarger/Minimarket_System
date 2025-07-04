from django.contrib import admin
from .models import (
    Minimercado, Proveedor, Lote, Producto, LoteProducto,
    Registro_compra_proveedor, Venta, DetalleVenta,
    SeccionBodega, SeccionLote, Reporte, ReporteProducto
)

# Register your models here.

class MinimercadoAdmin(admin.ModelAdmin):
    search_fields = ['nombre_minimercado']
    list_filter = ['fecha_creacion']
    list_per_page = 15

class ProveedorAdmin(admin.ModelAdmin):
    search_fields = ['nombre_proveedor', 'direccion', 'telefono', 'rut']
    list_display = ('nombre_proveedor', 'rut', 'direccion', 'telefono')
    list_per_page = 15

class LoteProductoInline(admin.TabularInline):
    model = LoteProducto
    extra = 1

class LoteAdmin(admin.ModelAdmin):
    search_fields = ['code_lote', 'proveedor__nombre_proveedor']
    list_filter = ['proveedor', 'fecha_registro']
    list_display = ('code_lote', 'proveedor', 'fecha_registro')
    inlines = [LoteProductoInline]
    list_per_page = 15

class ProductoAdmin(admin.ModelAdmin):
    search_fields = ['nombre', 'codigo_barras']
    list_display = ('nombre', 'codigo_barras', 'stock', 'precio', 'costo', 'minimal_stock')
    list_per_page = 15

class LoteProductoAdmin(admin.ModelAdmin):
    search_fields = ['lote__code_lote', 'producto__nombre']
    list_filter = ['lote', 'producto']
    list_display = ('lote', 'producto', 'fecha_vencimiento', 'cantidad_inicial', 'cantidad_disponible')
    list_per_page = 15

class RegistroCompraProveedorAdmin(admin.ModelAdmin):
    search_fields = ['proveedor__nombre_proveedor', 'productos__nombre']
    list_filter = ['fecha_compra', 'proveedor']
    list_display = ('proveedor', 'productos', 'fecha_compra', 'cantidad', 'precio_unitario', 'valor_total')
    list_per_page = 15

class DetalleVentaInline(admin.TabularInline):
    model = DetalleVenta
    extra = 1

class VentaAdmin(admin.ModelAdmin):
    search_fields = ['empleado__username', 'id']
    list_filter = ['fecha', 'empleado']
    list_display = ('id', 'empleado', 'fecha', 'total', 'cantidad_articulos')
    inlines = [DetalleVentaInline]
    list_per_page = 15

class DetalleVentaAdmin(admin.ModelAdmin):
    search_fields = ['venta__id', 'producto__nombre']
    list_filter = ['venta', 'producto']
    list_display = ('venta', 'producto', 'cantidad', 'precio_unitario', 'subtotal')
    list_per_page = 15

admin.site.register(Minimercado, MinimercadoAdmin)
admin.site.register(Proveedor, ProveedorAdmin)
admin.site.register(Lote, LoteAdmin)
admin.site.register(Producto, ProductoAdmin)
admin.site.register(LoteProducto, LoteProductoAdmin)
admin.site.register(Registro_compra_proveedor, RegistroCompraProveedorAdmin)
admin.site.register(Venta, VentaAdmin)
admin.site.register(DetalleVenta, DetalleVentaAdmin)

class SeccionLoteInline(admin.TabularInline):
    model = SeccionLote
    extra = 1
    fields = ('lote', 'observaciones')

class SeccionBodegaAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'tipo_forma', 'posicion_x', 'posicion_y', 'ancho', 'alto', 'activa', 'fecha_creacion')
    list_filter = ('tipo_forma', 'activa', 'fecha_creacion')
    search_fields = ('nombre', 'descripcion')
    inlines = [SeccionLoteInline]
    fieldsets = (
        ('Información Básica', {
            'fields': ('nombre', 'descripcion', 'tipo_forma', 'color', 'activa')
        }),
        ('Posición y Dimensiones', {
            'fields': ('posicion_x', 'posicion_y', 'ancho', 'alto')
        }),
    )
    list_per_page = 15

class SeccionLoteAdmin(admin.ModelAdmin):
    list_display = ('seccion', 'lote', 'fecha_asignacion')
    list_filter = ('seccion', 'fecha_asignacion')
    search_fields = ('seccion__nombre', 'lote__code_lote')
    list_per_page = 15

admin.site.register(SeccionBodega, SeccionBodegaAdmin)
admin.site.register(SeccionLote, SeccionLoteAdmin)

class ReporteProductoInline(admin.TabularInline):
    model = ReporteProducto
    extra = 1
    fields = ('producto', 'cantidad')

class ReporteAdmin(admin.ModelAdmin):
    list_display = ('nombre_reporte', 'tipo', 'usuario_creador', 'fecha_creacion', 'activo')
    list_filter = ('tipo', 'activo', 'fecha_creacion', 'usuario_creador')
    search_fields = ('nombre_reporte', 'descripcion')
    inlines = [ReporteProductoInline]
    fieldsets = (
        ('Información Básica', {
            'fields': ('nombre_reporte', 'descripcion', 'tipo', 'activo')
        }),
        ('Información del Sistema', {
            'fields': ('usuario_creador', 'fecha_creacion'),
            'classes': ('collapse',)
        }),
    )
    readonly_fields = ('fecha_creacion',)
    list_per_page = 15

class ReporteProductoAdmin(admin.ModelAdmin):
    list_display = ('reporte', 'producto', 'cantidad')
    list_filter = ('reporte__tipo', 'producto')
    search_fields = ('reporte__nombre_reporte', 'producto__nombre_producto')
    list_per_page = 15

admin.site.register(Reporte, ReporteAdmin)
admin.site.register(ReporteProducto, ReporteProductoAdmin)