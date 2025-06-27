from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth import get_user_model
from django.core.validators import RegexValidator, MinLengthValidator
from django.core.exceptions import ValidationError
from django.utils import timezone
from datetime import timedelta
from .models import Rental

User = get_user_model()

class UserRegisterForm(UserCreationForm):
    username = forms.CharField(
        label='Логин',
        validators=[
            RegexValidator(
                regex='^[a-zA-Z0-9_]+$',
                message='Логин может содержать только латинские буквы, цифры и подчеркивания'
            ),
            MinLengthValidator(
                4, 
                message='Логин должен содержать минимум 4 символа'
            )
        ],
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Придумайте логин'
        })
    )
    password1 = forms.CharField(
        label='Пароль',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Не менее 8 символов'
        }),
        help_text='Пароль должен содержать минимум 8 символов'
    )
    password2 = forms.CharField(
        label='Подтверждение пароля',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Повторите пароль'
        })
    )

    def clean_username(self):
        username = self.cleaned_data['username'].strip()
        if User.objects.filter(username__iexact=username).exists():
            raise ValidationError('Пользователь с таким логином уже существует')
        return username

    class Meta:
        model = User
        fields = ['username', 'password1', 'password2']

class UserLoginForm(AuthenticationForm):
    username = forms.CharField(
        label='Логин',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ваш логин'
        })
    )
    password = forms.CharField(
        label='Пароль',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ваш пароль'
        })
    )

    error_messages = {
        'invalid_login': "Неверный логин или пароль",
        'inactive': "Аккаунт неактивен",
    }

class RentEquipmentForm(forms.ModelForm):
    class Meta:
        model = Rental
        fields = ['start_time', 'end_time']
    
    def __init__(self, *args, **kwargs):
        self.equipment = kwargs.pop('equipment', None)
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Настройка виджетов
        self.fields['start_time'].widget = forms.DateTimeInput(
            attrs={
                'type': 'datetime-local',
                'class': 'form-control',
                'step': 'any'
            }
        )
        self.fields['end_time'].widget = forms.DateTimeInput(
            attrs={
                'type': 'datetime-local',
                'class': 'form-control',
                'step': 'any'
            }
        )

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.equipment = self.equipment  # Устанавливаем оборудование
        instance.client = self.user
        
        if commit:
            instance.save()
        
        return instance