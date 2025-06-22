from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import Equipment, Rental, User
from django.utils.translation import gettext_lazy as _
from django.utils import timezone

@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'email', 'is_trainer', 'is_staff', 'date_joined')
    list_filter = ('groups', 'is_staff', 'is_superuser')
    search_fields = ('username', 'email', 'first_name', 'last_name')
    date_hierarchy = 'date_joined'
    ordering = ('-date_joined',)
    
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        (_('Personal info'), {'fields': ('first_name', 'last_name', 'email')}),
        (_('Permissions'), {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions'),
        }),
        (_('Important dates'), {'fields': ('last_login', 'date_joined')}),
    )
    
    def is_trainer(self, obj):
        return obj.is_trainer()
    is_trainer.boolean = True
    is_trainer.short_description = 'Тренер'

@admin.register(Equipment)
class EquipmentAdmin(admin.ModelAdmin):
    list_display = ('name', 'status', 'added_at', 'last_updated')
    list_filter = ('status',)
    search_fields = ('name', 'description')
    date_hierarchy = 'added_at'
    list_editable = ('status',)
    list_per_page = 20
    ordering = ('-added_at',)

@admin.register(Rental)
class RentalAdmin(admin.ModelAdmin):
    list_display = ('client', 'equipment', 'rented_at', 'returned_at', 'status_info', 'duration')
    list_filter = ('equipment__status', 'rented_at', 'client__groups')
    raw_id_fields = ('client', 'equipment')
    date_hierarchy = 'rented_at'
    search_fields = ('client__username', 'equipment__name')
    list_select_related = ('client', 'equipment')
    
    def status_info(self, obj):
        return obj.equipment.get_status_display()
    status_info.short_description = 'Текущий статус'
    
    def duration(self, obj):
        if obj.returned_at:
            return obj.returned_at - obj.rented_at
        return timezone.now() - obj.rented_at
    duration.short_description = 'Длительность аренды'