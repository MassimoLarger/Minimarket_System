from django.urls import path
from .views import auth_views, product_views, category_views, sale_views, offer_views, inventory_views, supplier_views

urlpatterns = [
    path('', auth_views.login_view, name='login'),
    path('home/', auth_views.home, name='home'),
    path('logout/', auth_views.logout_view, name='logout'),
    path('nueva-venta/', sale_views.nueva_venta, name='nueva_venta'),
    path('historial/', sale_views.historial_ventas, name='historial'),
    path('ofertas/', offer_views.ofertas, name='ofertas'),
    path('gestionar_productos/', product_views.gestionar_productos, name='gestionar_productos'),
    path('gestionar_categorias/', category_views.gestionar_categorias, name='gestionar_categorias'),
    # URLs de Gestión (Admin)
    path('gestionar-inventario/', inventory_views.gestionar_inventario, name='gestionar_inventario'),
    path('gestionar-proveedores/', supplier_views.gestionar_proveedores, name='gestionar_proveedores'),
    path('verify-password-inventory/', inventory_views.verify_password_inventory, name='verify_password_inventory'), # Añadido para verificar contraseña de inventario
    path('verify-password-providers/', supplier_views.verify_password_providers, name='verify_password_providers'), # Añadido para verificar contraseña de proveedores
    path('registro-compra-proveedores/', supplier_views.registro_compra_proveedores, name='registro_compra_proveedores'),
]