from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils.translation import gettext_lazy as _

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

    def __str__(self):
        return f"{self.name} ({self.get_status_display()})"

class Rental(models.Model):
    client = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name=_('Клиент'))
    equipment = models.ForeignKey(Equipment, on_delete=models.CASCADE, verbose_name=_('Оборудование'))
    rented_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Дата аренды'))
    returned_at = models.DateTimeField(null=True, blank=True, verbose_name=_('Дата возврата'))
    notes = models.TextField(blank=True, verbose_name=_('Примечания'))
    
    class Meta:
        verbose_name = _('Аренда')
        verbose_name_plural = _('Аренды')
        ordering = ['-rented_at']
    
    def __str__(self):
        return f"{self.client.username} → {self.equipment.name} ({self.rented_at.date()})"