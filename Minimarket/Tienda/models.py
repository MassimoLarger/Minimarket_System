from django.db import models
from django.contrib.auth.models import User

class Minimercado(models.Model):
    nombre_minimercado = models.CharField(max_length=100, unique=True)
    fecha_creacion = models.DateField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.nombre_minimercado}"

class Proveedor(models.Model):
    nombre_proveedor = models.CharField(max_length=100, unique=True)
    rut = models.PositiveIntegerField(unique=True)
    verify_digit = models.CharField(max_length=1, choices=[(str(i), str(i)) for i in range(10)] + [('K', 'K'), ('k', 'k')])
    direccion = models.CharField(max_length=200)
    telefono = models.PositiveIntegerField()

    def __str__(self):
        return f"{self.nombre_proveedor}"

class Categoria(models.Model):
    nombre = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.nombre

class Producto(models.Model):
    nombre = models.CharField(max_length=100, unique=True)
    codigo_barras = models.PositiveIntegerField(default=0, unique=True)
    stock = models.PositiveIntegerField(default=0)
    precio = models.PositiveIntegerField(default=0)
    costo = models.PositiveIntegerField(default=0)
    minimal_stock = models.PositiveIntegerField(default=0)
    categoria = models.ForeignKey(Categoria, on_delete=models.SET_NULL, null=True, blank=True, related_name='productos')
    
    def __str__(self):
        return f"{self.nombre} - {self.codigo_barras}"

class Lote(models.Model):
    code_lote = models.CharField(max_length=50, unique=True)  # Asegurar códigos únicos
    proveedor = models.ForeignKey(Proveedor, on_delete=models.CASCADE, related_name='lotes')
    productos = models.ManyToManyField('Producto', through='LoteProducto')
    fecha_registro = models.DateTimeField(auto_now_add=True)  # Mejor usar DateTimeField
    
    class Meta:
        ordering = ['-fecha_registro']
        verbose_name = 'Lote'
        verbose_name_plural = 'Lotes'
    
    def __str__(self):
        return f"{self.code_lote} - {self.proveedor.nombre_proveedor} - {self.fecha_registro.strftime('%d/%m/%Y')}"

class LoteProducto(models.Model):
    lote = models.ForeignKey(Lote, on_delete=models.CASCADE, related_name='productos_relacionados')
    producto = models.ForeignKey(Producto, on_delete=models.CASCADE, related_name='lotes_asociados')
    fecha_vencimiento = models.DateField(null=True, blank=True)
    cantidad_inicial = models.PositiveIntegerField(default=1)
    cantidad_disponible = models.PositiveIntegerField(default=1)
    
    class Meta:
        unique_together = ('lote', 'producto')  # Evitar duplicados
        verbose_name = 'Relación Lote-Producto'
        verbose_name_plural = 'Relaciones Lote-Producto'
    
    def __str__(self):
        return f"{self.lote.code_lote} - {self.producto.nombre} x{self.cantidad_inicial} (disp: {self.cantidad_disponible})"

class SeccionBodega(models.Model):
    TIPO_FORMA_CHOICES = [
        ('cuadrado', 'Cuadrado'),
        ('rectangulo', 'Rectángulo'),
    ]
    
    nombre = models.CharField(max_length=100, unique=True)
    descripcion = models.TextField(blank=True, null=True)
    tipo_forma = models.CharField(max_length=20, choices=TIPO_FORMA_CHOICES, default='rectangulo')
    
    # Posición en el mapa (coordenadas)
    posicion_x = models.FloatField(default=0)
    posicion_y = models.FloatField(default=0)
    
    # Dimensiones
    ancho = models.FloatField(default=100)  # en píxeles
    alto = models.FloatField(default=100)   # en píxeles
    
    # Color de la sección
    color = models.CharField(max_length=7, default='#3498db', help_text='Color en formato hexadecimal')
    
    # Metadatos
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    activa = models.BooleanField(default=True)
    
    class Meta:
        verbose_name = 'Sección de Bodega'
        verbose_name_plural = 'Secciones de Bodega'
        ordering = ['nombre']
    
    def __str__(self):
        return f"{self.nombre} ({self.get_tipo_forma_display()})"
    
    def get_lotes_asignados(self):
        """Retorna los lotes asignados a esta sección"""
        return self.lotes_asignados.all()
    
    def get_capacidad_utilizada(self):
        """Calcula el porcentaje de capacidad utilizada basado en los lotes asignados"""
        total_lotes = self.lotes_asignados.count()
        # Capacidad máxima estimada basada en el área de la sección
        area = self.ancho * self.alto
        capacidad_maxima = max(1, int(area / 5000))  # Estimación: 1 lote por cada 5000 píxeles cuadrados
        
        if capacidad_maxima > 0:
            return min(100, (total_lotes / capacidad_maxima) * 100)
        return 0

class SeccionLote(models.Model):
    seccion = models.ForeignKey(SeccionBodega, on_delete=models.CASCADE, related_name='lotes_asignados')
    lote = models.ForeignKey(Lote, on_delete=models.CASCADE, related_name='seccion_asignada')
    fecha_asignacion = models.DateTimeField(auto_now_add=True)
    observaciones = models.TextField(blank=True, null=True)
    
    class Meta:
        unique_together = ('seccion', 'lote')  # Un lote solo puede estar en una sección
        verbose_name = 'Asignación Sección-Lote'
        verbose_name_plural = 'Asignaciones Sección-Lote'
        ordering = ['-fecha_asignacion']
    
    def __str__(self):
        return f"{self.seccion.nombre} - {self.lote.code_lote}"

class Registro_compra_proveedor(models.Model):
    proveedor = models.ForeignKey(Proveedor, on_delete=models.CASCADE)
    productos = models.ForeignKey(Producto, on_delete=models.CASCADE)
    fecha_compra = models.DateField(auto_now_add=True)
    cantidad = models.PositiveIntegerField(default=0)
    precio_unitario = models.PositiveIntegerField(default=0)
    valor_total = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f"{self.proveedor} - {self.productos} - {self.valor_total}"

class Venta(models.Model):
    empleado = models.ForeignKey(User, on_delete=models.PROTECT)
    fecha = models.DateTimeField(auto_now_add=True)
    total = models.PositiveIntegerField(default=0)
    cantidad_articulos = models.PositiveIntegerField(default=0) 
    
    def __str__(self):
        return f"Venta #{self.id} - {self.empleado.username} - {self.fecha.strftime('%d/%m/%Y %H:%M')}"

class DetalleVenta(models.Model):
    venta = models.ForeignKey(Venta, related_name='detalles', on_delete=models.CASCADE)
    producto = models.ForeignKey(Producto, on_delete=models.PROTECT)
    cantidad = models.PositiveIntegerField(default=0)
    precio_unitario = models.PositiveIntegerField(default=0)
    subtotal = models.PositiveIntegerField(default=0)
    
    def __str__(self):
        return f"Detalle Venta #{self.venta.id} - {self.producto.nombre} x{self.cantidad}"

class OfertaProducto(models.Model):
    nombre = models.CharField(max_length=100, unique=True)
    fecha_inicio = models.DateField()
    fecha_fin = models.DateField(null=True, blank=True)
    descuento_porcentaje = models.PositiveIntegerField(default=0)
    activa = models.BooleanField(default=True)
    productos = models.ManyToManyField(Producto, related_name='ofertas_producto')
    
    def __str__(self):
        return f"{self.nombre} - {self.descuento_porcentaje}% descuento"
    
    def precio_con_descuento(self, precio_original):
        """Calcula el precio con descuento aplicado"""
        if self.activa:
            descuento = (precio_original * self.descuento_porcentaje) // 100
            return precio_original - descuento
        return precio_original

class OfertaVencimiento(models.Model):
    nombre = models.CharField(max_length=100, unique=True)
    fecha_inicio = models.DateField()
    fecha_fin = models.DateField(null=True, blank=True)
    descuento_porcentaje = models.PositiveIntegerField(default=0)
    activa = models.BooleanField(default=True)
    dias_antes_vencimiento = models.PositiveIntegerField(default=3, help_text="Días antes del vencimiento para aplicar la oferta")
    
    def __str__(self):
        return f"{self.nombre} - {self.descuento_porcentaje}% descuento (productos próximos a vencer)"
    
    def precio_con_descuento(self, precio_original):
        """Calcula el precio con descuento aplicado"""
        if self.activa:
            descuento = (precio_original * self.descuento_porcentaje) // 100
            return precio_original - descuento
        return precio_original

class Alert(models.Model):
    TIPO_CHOICES = [
        ('stock_bajo', 'Producto Bajo en Stock'),
        ('proximo_vencer', 'Producto Próximo a Vencer'),
        ('oferta_terminando', 'Oferta Próxima a Terminar'),
    ]
    
    ESTADO_CHOICES = [
        ('activa', 'Activa'),
        ('mostrada', 'Mostrada'),
        ('desactivada', 'Desactivada'),
    ]
    
    nombre = models.CharField(max_length=200, unique=True)
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES)
    mensaje = models.TextField()
    estado = models.CharField(max_length=15, choices=ESTADO_CHOICES, default='activa')
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_mostrada = models.DateTimeField(null=True, blank=True)
    
    # Campos específicos para cada tipo de alerta
    producto = models.ForeignKey(Producto, on_delete=models.CASCADE, null=True, blank=True)
    oferta_producto = models.ForeignKey(OfertaProducto, on_delete=models.CASCADE, null=True, blank=True)
    oferta_vencimiento = models.ForeignKey(OfertaVencimiento, on_delete=models.CASCADE, null=True, blank=True)
    
    # Configuración de la alerta
    umbral_stock = models.PositiveIntegerField(null=True, blank=True, help_text="Stock mínimo para activar alerta")
    dias_anticipacion = models.PositiveIntegerField(null=True, blank=True, help_text="Días de anticipación para alertas de vencimiento")
    
    activa = models.BooleanField(default=True)
    
    class Meta:
        ordering = ['-fecha_creacion']
        verbose_name = 'Alerta'
        verbose_name_plural = 'Alertas'
    
    def __str__(self):
        return f"{self.get_tipo_display()} - {self.nombre}"
    
    def marcar_como_mostrada(self):
        """Marca la alerta como mostrada"""
        from django.utils import timezone
        self.estado = 'mostrada'
        self.fecha_mostrada = timezone.now()
        self.save()
    
    def verificar_condicion(self):
        """Verifica si la condición de la alerta se cumple"""
        from django.utils import timezone
        from datetime import timedelta
        
        if not self.activa:
            return False

class Reporte(models.Model):
    TIPO_CHOICES = [
        ('producto', 'Reporte de Producto'),
        ('perdida', 'Pérdida de Producto'),
        ('inventario', 'Reporte de Inventario'),
        ('ventas', 'Reporte de Ventas'),
    ]
    
    nombre_reporte = models.CharField(max_length=200, unique=True)
    descripcion = models.TextField()
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    usuario_creador = models.ForeignKey(User, on_delete=models.PROTECT, related_name='reportes_creados')
    
    # Para reportes de productos específicos
    productos_afectados = models.ManyToManyField(Producto, through='ReporteProducto', blank=True)
    
    activo = models.BooleanField(default=True)
    
    class Meta:
        ordering = ['-fecha_creacion']
        verbose_name = 'Reporte'
        verbose_name_plural = 'Reportes'
    
    def __str__(self):
        return f"{self.nombre_reporte} - {self.get_tipo_display()} ({self.fecha_creacion.strftime('%d/%m/%Y')})"
    
    def get_total_cantidad_afectada(self):
        """Retorna la cantidad total de productos afectados en el reporte"""
        return sum(rp.cantidad for rp in self.productos_reporte.all())

class ReporteProducto(models.Model):
    reporte = models.ForeignKey(Reporte, on_delete=models.CASCADE, related_name='productos_reporte')
    producto = models.ForeignKey(Producto, on_delete=models.CASCADE)
    cantidad = models.PositiveIntegerField(default=0, blank=True, null=True)
    observaciones = models.TextField(blank=True, null=True)
    
    class Meta:
        unique_together = ('reporte', 'producto')
        verbose_name = 'Producto en Reporte'
        verbose_name_plural = 'Productos en Reporte'
    
    def __str__(self):
        if self.reporte.tipo == 'producto':
            return f"{self.reporte.nombre_reporte} - {self.producto.nombre}"
        return f"{self.reporte.nombre_reporte} - {self.producto.nombre} x{self.cantidad}"
    
    def save(self, *args, **kwargs):
        """Al guardar, si es un reporte de pérdida, descontar del stock"""
        is_new = self.pk is None
        old_cantidad = 0
        
        if not is_new:
            old_instance = ReporteProducto.objects.get(pk=self.pk)
            old_cantidad = old_instance.cantidad or 0
        
        # Los reportes de producto ahora pueden tener cantidad
        # Solo se establece como None si no se proporciona cantidad
        if self.reporte.tipo == 'producto' and self.cantidad == 0:
            self.cantidad = None
        
        super().save(*args, **kwargs)
        
        # Si es un reporte de pérdida, descontar del stock
        if self.reporte.tipo == 'perdida' and self.cantidad:
            diferencia = self.cantidad - old_cantidad
            if diferencia > 0:
                # Descontar la diferencia del stock
                if self.producto.stock >= diferencia:
                    self.producto.stock -= diferencia
                    self.producto.save()
                else:
                    # Si no hay suficiente stock, descontar lo que se pueda
                    self.producto.stock = 0
                    self.producto.save()
            
        # Este código parece estar mezclado con el modelo Alert
        # y no pertenece al modelo ReporteProducto
        pass