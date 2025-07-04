from django.urls import path
from .views import auth_views, product_views, category_views, sale_views, inventory_views, supplier_views, offer_views, alert_views, warehouse_views, report_views

urlpatterns = [
    path('', auth_views.login_view, name='login'),
    path('home/', auth_views.home, name='home'),
    path('logout/', auth_views.logout_view, name='logout'),
    path('nueva-venta/', sale_views.nueva_venta, name='nueva_venta'),
    path('historial/', sale_views.historial_ventas, name='historial'),
    path('gestionar_productos/', product_views.gestionar_productos, name='gestionar_productos'),
    path('gestionar_categorias/', category_views.gestionar_categorias, name='gestionar_categorias'),
    path('gestionar_ofertas/', offer_views.gestionar_ofertas, name='gestionar_ofertas'),
    path('gestionar_alertas/', alert_views.gestionar_alertas, name='gestionar_alertas'),
    path('api/alertas-activas/', alert_views.obtener_alertas_activas, name='obtener_alertas_activas'),
    # URLs de Gestión (Admin)
    path('gestionar-inventario/', inventory_views.gestionar_inventario, name='gestionar_inventario'),
    path('gestionar-proveedores/', supplier_views.gestionar_proveedores, name='gestionar_proveedores'),
    path('verify-password-inventory/', inventory_views.verify_password_inventory, name='verify_password_inventory'), # Añadido para verificar contraseña de inventario
    path('verify-password-providers/', supplier_views.verify_password_providers, name='verify_password_providers'), # Añadido para verificar contraseña de proveedores
    path('verify-password-warehouse/', warehouse_views.verify_password_warehouse, name='verify_password_warehouse'), # Añadido para verificar contraseña de bodega
    path('verify-password-alerts/', alert_views.verify_password_alerts, name='verify_password_alerts'), # Añadido para verificar contraseña de alertas
    path('gestionar-bodega/', warehouse_views.gestionar_bodega, name='gestionar_bodega'),
    
    # URLs para gestión de secciones de bodega
    path('bodega/crear-seccion/', warehouse_views.crear_seccion, name='crear_seccion'),
    path('bodega/actualizar-seccion/<int:seccion_id>/', warehouse_views.actualizar_seccion, name='actualizar_seccion'),
    path('bodega/eliminar-seccion/<int:seccion_id>/', warehouse_views.eliminar_seccion, name='eliminar_seccion'),
    path('bodega/asignar-lote/', warehouse_views.asignar_lote_seccion, name='asignar_lote_seccion'),
    path('bodega/desasignar-lote/<int:asignacion_id>/', warehouse_views.desasignar_lote_seccion, name='desasignar_lote_seccion'),
    path('bodega/lotes-seccion/<int:seccion_id>/', warehouse_views.obtener_lotes_seccion, name='obtener_lotes_seccion'),
    path('bodega/obtener-secciones/', warehouse_views.obtener_secciones, name='obtener_secciones'),
    path('registro-compra-proveedores/', supplier_views.registro_compra_proveedores, name='registro_compra_proveedores'),
    
    # URLs para gestión de reportes
    path('verify-password-reports/', report_views.verify_password_reports, name='verify_password_reports'),
    path('gestionar-reportes/', report_views.gestionar_reportes, name='gestionar_reportes'),
    path('reportes/obtener-detalle/<int:reporte_id>/', report_views.obtener_reporte_detalle, name='obtener_reporte_detalle'),
]