from django.apps import AppConfig


class TiendaConfig(AppConfig):
    """
    Configuración de la aplicación Tienda.
    Define el campo automático predeterminado y el nombre de la aplicación.
    """
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'Tienda'
