from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth import get_user_model
from django.core.validators import RegexValidator, MinLengthValidator
from django.core.exceptions import ValidationError
from django.utils import timezone
from datetime import timedelta
from .models import Rental, Maintenance

User = get_user_model()

class UserRegisterForm(UserCreationForm):
    username = forms.CharField(
        label='Логин',
        error_messages={
            'required': 'Пожалуйста, введите логин',
            'invalid': 'Недопустимый логин',
            'unique': 'Пользователь с таким логином уже существует',
        },
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
        error_messages={
            'required': 'Пожалуйста, введите пароль',
        },
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Не менее 8 символов'
        }),
        help_text='Пароль должен содержать минимум 8 символов'
    )
    password2 = forms.CharField(
        label='Подтверждение пароля',
        error_messages={
            'required': 'Пожалуйста, повторите пароль',
        },
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
        error_messages={
            'required': 'Пожалуйста, введите логин',
            'invalid': 'Недопустимый логин',
        },
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ваш логин'
        })
    )
    password = forms.CharField(
        label='Пароль',
        error_messages={
            'required': 'Пожалуйста, введите пароль',
        },
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
    duration = forms.ChoiceField(
        label='Длительность (часы)',
        choices=[(str(i), f'{i} ч.') for i in range(1, 25)],
        initial='1',
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    class Meta:
        model = Rental
        fields = ['start_time', 'duration']
    
    def __init__(self, *args, **kwargs):
        self.equipment = kwargs.pop('equipment', None)
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        self.fields['start_time'].widget = forms.DateTimeInput(
            attrs={
                'type': 'datetime-local',
                'class': 'form-control',
                'step': 'any'
            }
        )
        if self.instance.pk is None:
            self.instance.equipment = self.equipment
            self.instance.client = self.user

    def clean(self):
        cleaned_data = super().clean()
        start_time = cleaned_data.get('start_time')
        duration = cleaned_data.get('duration')
        equipment = self.equipment
        if start_time and duration and equipment:
            try:
                hours = int(duration)
            except (TypeError, ValueError):
                raise ValidationError('Некорректная длительность аренды')
            end_time = start_time + timedelta(hours=hours)
            cleaned_data['end_time'] = end_time
            self.instance.end_time = end_time
            # Проверка: есть ли обслуживание на это время
            maint_qs = equipment.maintenances.filter(
                status__in=['planned', 'in_progress'],
                end_date__gt=start_time,
                start_date__lt=end_time
            )
            if maint_qs.exists():
                raise ValidationError('Оборудование находится на обслуживании в выбранный период. Аренда невозможна.')
        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.equipment = self.equipment
        instance.client = self.user
        # end_time уже установлен в clean()
        if commit:
            instance.save()
        return instance

class MaintenanceForm(forms.ModelForm):
    class Meta:
        model = Maintenance
        fields = ['equipment', 'start_date', 'end_date', 'description', 'performed_by', 'status']
        widgets = {
            'start_date': forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'form-control'}),
            'end_date': forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'performed_by': forms.TextInput(attrs={'class': 'form-control'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'equipment': forms.Select(attrs={'class': 'form-select'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        equipment = cleaned_data.get('equipment')
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')
        status = cleaned_data.get('status')
        if equipment and start_date:
            # Проверка: есть ли аренда на это время
            qs = equipment.rentals.filter(
                end_time__gt=start_date,
                start_time__lt=end_date if end_date else start_date,
                returned_at__isnull=True
            )
            if qs.exists():
                raise ValidationError('Нельзя создать обслуживание: оборудование уже арендовано на это время.')
        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)
        # Меняем статус оборудования
        if instance.status in ['planned', 'in_progress']:
            instance.equipment.status = 'maintenance'
            instance.equipment.save()
        elif instance.status == 'completed':
            # Если нет других активных обслуживаний, вернуть статус
            active_maint = instance.equipment.maintenances.filter(
                status__in=['planned', 'in_progress']
            ).exclude(pk=instance.pk).exists()
            if not active_maint:
                # Если есть активная аренда — вернуть статус 'rented', иначе 'available'
                now = timezone.now()
                has_rental = instance.equipment.rentals.filter(
                    start_time__lte=now,
                    end_time__gte=now,
                    returned_at__isnull=True
                ).exists()
                instance.equipment.status = 'rented' if has_rental else 'available'
                instance.equipment.save()
        if commit:
            instance.save()
        return instance