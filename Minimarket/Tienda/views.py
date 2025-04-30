from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from .forms import LoginForm

def home(request):
    """
    Vista para la página principal.
    Muestra la página de inicio del Minimarket.
    """
    return render(request, 'Tienda/home.html')

def login_view(request):
    """
    Vista para el inicio de sesión.
    Procesa el formulario de login y autentica al usuario.
    """
    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']
            user = authenticate(request, username=username, password=password)
            if user is not None:
                login(request, user)
                messages.success(request, f'Bienvenido, {username}!')
                return redirect('home')
            else:
                messages.error(request, 'Nombre de usuario o contraseña incorrectos')
    else:
        form = LoginForm()
    
    return render(request, 'Tienda/login.html', {'form': form})

def logout_view(request):
    """
    Vista para cerrar sesión.
    Cierra la sesión del usuario actual y redirecciona al login.
    """
    logout(request)
    messages.info(request, 'Has cerrado sesión correctamente')
    return redirect('login')

def register(request):
    """
    Vista para el registro de usuarios.
    Actualmente no permite registros y redirecciona al login.
    """
    # Redirigir al login ya que no se permite registro
    messages.info(request, 'El registro no está disponible')
    return redirect('login')
