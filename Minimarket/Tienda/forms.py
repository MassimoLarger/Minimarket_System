from django import forms
from django.core.validators import RegexValidator
from django.contrib.auth.models import User

class LoginForm(forms.Form):
    """
    Formulario para el inicio de sesión de usuarios.
    Valida que el nombre de usuario contenga solo letras.
    """
    username = forms.CharField(
        label='Nombre de usuario',
        max_length=150,
        validators=[
            RegexValidator(
                regex='^[a-zA-Z]+$',
                message='El nombre de usuario solo puede contener letras',
                code='invalid_username'
            ),
        ],
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ingrese su nombre de usuario'})
    )
    password = forms.CharField(
        label='Contraseña',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control', 
            'placeholder': 'Ingrese su contraseña',
            'id': 'password-field'
        })
    )