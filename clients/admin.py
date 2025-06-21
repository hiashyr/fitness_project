from django.contrib import admin
from .models import Equipment, Rental

@admin.register(Equipment)
class EquipmentAdmin(admin.ModelAdmin):
    list_display = ('name', 'status', 'added_at')
    list_filter = ('status',)
    search_fields = ('name', 'description')

@admin.register(Rental)
class RentalAdmin(admin.ModelAdmin):
    list_display = ('client', 'equipment', 'rented_at', 'returned_at')
    list_filter = ('equipment__status',)