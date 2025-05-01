from django.contrib.auth import logout
from django.utils import timezone
from datetime import timedelta
import time

class SessionTimeoutMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            last_activity = request.session.get('last_activity')
            
            # Comparar el timestamp almacenado con el tiempo actual
            if last_activity and (time.time() - last_activity > 6 * 3600): # 6 horas en segundos
                logout(request)
                from django.contrib import messages
                messages.warning(request, 'Tu sesión ha expirado por inactividad.')
            
            # Convertir el objeto datetime a timestamp (serializable en JSON)
            request.session['last_activity'] = time.time()
        
        response = self.get_response(request)
        return response