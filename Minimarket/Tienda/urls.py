from django.urls import path
from . import views

urlpatterns = [
    path('', views.login_view, name='login'),
    path('home/', views.home, name='home'),
    path('logout/', views.logout_view, name='logout'),
    path('nueva-venta/', views.nueva_venta, name='nueva_venta'),
    path('historial/', views.historial, name='historial'),
    path('ofertas/', views.ofertas, name='ofertas'),
    path('gestionar_productos/', views.gestionar_productos, name='gestionar_productos'),
    # URLs de Gestión (Admin)
    path('gestionar-inventario/', views.gestionar_inventario, name='gestionar_inventario'),
    path('gestionar-proveedores/', views.gestionar_proveedores, name='gestionar_proveedores'),
    path('verify-password-inventory/', views.verify_password_inventory, name='verify_password_inventory'), # Añadido para verificar contraseña de inventario
    path('verify-password-providers/', views.verify_password_providers, name='verify_password_providers'), # Añadido para verificar contraseña de proveedores
    path('registro-compra-proveedores/', views.registro_compra_proveedores, name='registro_compra_proveedores'),
]