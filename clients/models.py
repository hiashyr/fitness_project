from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator, MaxValueValidator
from datetime import timedelta

def default_end_time():
    return timezone.now() + timezone.timedelta(hours=1)

class User(AbstractUser):
    def is_trainer(self):
        return self.groups.filter(name='Тренеры').exists() or self.is_staff

    class Meta:
        db_table = 'clients_user'
        verbose_name = _('Пользователь')
        verbose_name_plural = _('Пользователи')

class Equipment(models.Model):
    STATUS_CHOICES = [
        ('available', 'Доступен'),
        ('rented', 'В аренде'),
        ('maintenance', 'На обслуживании')
    ]
    
    name = models.CharField(max_length=100, verbose_name=_('Название'))
    description = models.TextField(blank=True, verbose_name=_('Описание'))
    status = models.CharField(
        max_length=12,
        choices=STATUS_CHOICES,
        default='available',
        verbose_name=_('Статус')
    )
    added_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Дата добавления'))
    last_updated = models.DateTimeField(auto_now=True, verbose_name=_('Последнее обновление'))
    
    class Meta:
        verbose_name = _('Оборудование')
        verbose_name_plural = _('Оборудование')
        ordering = ['-added_at']
        constraints = [
            models.CheckConstraint(
                check=models.Q(status__in=['available', 'rented', 'maintenance']),
                name="valid_equipment_status"
            )
        ]

    def __str__(self):
        return f"{self.name} ({self.get_status_display()})"
    
    def update_status(self):
        """Обновляет статус оборудования на основе активных аренд"""
        if self.rentals.filter(returned_at__isnull=True, end_time__gt=timezone.now()).exists():
            self.status = 'rented'
        else:
            self.status = 'available'
        self.save()

User = get_user_model()

class Rental(models.Model):
    client = models.ForeignKey(User, on_delete=models.CASCADE, related_name='rentals')
    equipment = models.ForeignKey(Equipment, on_delete=models.CASCADE, related_name='rentals')
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    returned_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)
    
    class Meta:
        verbose_name = "Аренда"
        verbose_name_plural = "Аренды"
        ordering = ['-start_time']
        indexes = [
            models.Index(fields=['start_time', 'end_time']),
            models.Index(fields=['equipment', 'start_time']),
        ]
        constraints = [
            models.CheckConstraint(
                check=models.Q(end_time__gt=models.F('start_time')),
                name="end_after_start"
            ),
            models.CheckConstraint(
                check=models.Q(start_time__gte=timezone.now() - timedelta(days=1)),
                name="start_not_in_past"
            )
        ]
    
    def __str__(self):
        return f"{self.client.username} → {self.equipment.name} ({self.start_time.date()})"
    
    def clean(self):
        """Валидация временных промежутков и доступности оборудования"""
        now = timezone.now()
        
        # Округляем время до минут
        self.start_time = self.start_time.replace(second=0, microsecond=0)
        self.end_time = self.end_time.replace(second=0, microsecond=0)
        
        # Проверка что время начала не в прошлом
        if self.start_time < now.replace(second=0, microsecond=0):
            raise ValidationError("Нельзя создать аренду в прошлом")
        
        # Проверка временного промежутка
        duration_minutes = (self.end_time - self.start_time).total_seconds() / 60
        
        if duration_minutes < 60:
            raise ValidationError("Минимальное время аренды - 60 минут")
        if duration_minutes > 24 * 60:
            raise ValidationError("Максимальное время аренды - 24 часа")
        
        # Проверка доступности оборудования
        if self.check_overlapping_rentals():
            raise ValidationError("Оборудование уже забронировано на этот период")

    def check_overlapping_rentals(self):
        """Проверяет пересечение с другими арендами"""
        return Rental.objects.filter(
            equipment=self.equipment,
            end_time__gt=self.start_time,
            start_time__lt=self.end_time,
            returned_at__isnull=True
        ).exclude(pk=self.pk if self.pk else None).exists()

    @property
    def is_active(self):
        """Активна ли аренда в данный момент"""
        now = timezone.now()
        return (self.start_time <= now <= self.end_time) and not self.returned_at
    
    @property
    def is_overdue(self):
        """Просрочена ли аренда"""
        return not self.returned_at and timezone.now() > self.end_time
    
    @property
    def duration(self):
        """Общая продолжительность аренды в минутах"""
        return (self.end_time - self.start_time).total_seconds() / 60
    
    @property
    def time_passed(self):
        """Прошедшее время с начала аренды в минутах"""
        now = timezone.now()
        if now > self.end_time:
            return self.duration
        return (now - self.start_time).total_seconds() / 60
    
    @property
    def progress_percent(self):
        """Процент завершения аренды"""
        return min(100, max(0, (self.time_passed / self.duration) * 100))
    
    @property
    def time_remaining(self):
        """Оставшееся время аренды в минутах"""
        now = timezone.now()
        if now >= self.end_time:
            return 0
        return (self.end_time - now).total_seconds() / 60
    
    def save(self, *args, **kwargs):
        """Переопределяем save для автоматической валидации"""
        self.full_clean()
        super().save(*args, **kwargs)
        self.equipment.update_status()
    
    @classmethod
    def get_current_for_equipment(cls, equipment):
        """Получить текущую аренду для оборудования"""
        now = timezone.now()
        return cls.objects.filter(
            equipment=equipment,
            start_time__lte=now,
            end_time__gte=now,
            returned_at__isnull=True
        ).first()