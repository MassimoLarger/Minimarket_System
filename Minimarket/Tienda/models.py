from django.db import models
from django.contrib.auth.models import User

class Minimercado(models.Model):
    nombre_minimercado = models.CharField(max_length=100)
    fecha_creacion = models.DateField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.nombre_minimercado}"

class Proveedor(models.Model):
    nombre_proveedor = models.CharField(max_length=100)
    rut = models.CharField(unique=True, max_length=30)
    direccion = models.CharField(max_length=200)
    telefono = models.PositiveIntegerField()
    
    def __str__(self):
        return f"{self.nombre_proveedor}"

class Producto(models.Model):
    nombre = models.CharField(max_length=100)
    codigo_barras = models.CharField(max_length=50, unique=True)
    stock = models.PositiveIntegerField(default=0)
    precio = models.PositiveIntegerField(default=0)
    costo = models.PositiveIntegerField(default=0)
    minimal_stock = models.PositiveIntegerField(default=0)
    
    def __str__(self):
        return f"{self.nombre} - {self.codigo_barras}"

class Lote(models.Model):
    code_lote = models.CharField(max_length=50)
    proveedor = models.ForeignKey(Proveedor, on_delete=models.CASCADE)
    productos = models.ManyToManyField('Producto', through='LoteProducto')
    fecha_registro = models.DateField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.code_lote} - {self.proveedor} - {self.fecha_registro}"

class LoteProducto(models.Model):
    lote = models.ForeignKey(Lote, on_delete=models.CASCADE)
    producto = models.ForeignKey(Producto, on_delete=models.CASCADE)
    fecha_vencimiento = models.DateField(null=True, blank=True)
    cantidad_inicial = models.PositiveIntegerField(default=1)
    cantidad_disponible = models.PositiveIntegerField(default=1)
    
    def __str__(self):
        return f"{self.lote.code_lote} - {self.producto.nombre} x {self.cantidad_inicial} - {self.cantidad_disponible}"

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
    empleado = models.ForeignKey(User, on_delete=models.CASCADE)
    fecha = models.DateTimeField(auto_now_add=True)
    total = models.PositiveIntegerField(default=0)
    
    def __str__(self):
        return f"Venta #{self.id} - {self.empleado.username} - {self.fecha.strftime('%d/%m/%Y %H:%M')}"

class DetalleVenta(models.Model):
    venta = models.ForeignKey(Venta, on_delete=models.CASCADE, related_name='detalles')
    producto = models.ForeignKey(Producto, on_delete=models.CASCADE)
    cantidad = models.PositiveIntegerField(default=1)
    precio_unitario = models.PositiveIntegerField(default=0)
    
    def __str__(self):
        return f"Detalle Venta #{self.venta.id} - {self.producto.nombre} x{self.cantidad}"

class Registro_Venta(models.Model):
    minimarket = models.ForeignKey(Minimercado, on_delete=models.CASCADE)
    descripcion = models.CharField(max_length=100, default='')
    fecha_venta = models.DateField(auto_now_add=True)
    total_venta = models.PositiveIntegerField(default=0)
    
    def __str__(self):
        return f"Registro Venta {self.id} - {self.minimarket.nombre_minimercado} - {self.total_venta}"

class Oferta(models.Model):
    tipo_oferta = models.CharField(max_length=100, default='')
    fecha_inicio = models.DateField()
    fecha_fin = models.DateField()
    descuento_porcetaje = models.PositiveIntegerField(default=0)
    
    def __str__(self):
        return f"{self.tipo_oferta} - {self.descuento_porcetaje}% descuento"

class Oferta_vencimiento(models.Model):
    producto_id = models.ForeignKey(Producto, on_delete=models.CASCADE, related_name='ofertas_vencimiento')
    oferta_id = models.ForeignKey(Oferta, on_delete=models.CASCADE, related_name='ofertas_vencimiento')
    cantidad = models.PositiveIntegerField(default=1)
    new_code_bar = models.CharField(max_length=50)
    
    def __str__(self):
        return f"{self.producto_id.nombre} - {self.oferta_id.descuento_porcetaje}"

class Oferta_producto(models.Model):
    producto_id = models.ForeignKey(Producto, on_delete=models.CASCADE, related_name='ofertas_producto')
    oferta_id = models.ForeignKey(Oferta, on_delete=models.CASCADE, related_name='ofertas_producto')

    def __str__(self):
        return f"{self.producto_id.nombre} - {self.oferta_id.descuento_porcetaje}"