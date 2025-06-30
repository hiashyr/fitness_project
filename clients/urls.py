from django.urls import path
from .views import (
    home, register, user_login, user_logout,
    EquipmentListView, MyRentalsView,
    rent_equipment, return_equipment,
    AllEquipmentView, RentalHistoryView,
    maintenance_list, maintenance_create, maintenance_edit, maintenance_detail
)

urlpatterns = [
    path('', home, name='home'),
    path('register/', register, name='register'),
    path('login/', user_login, name='login'),
    path('logout/', user_logout, name='logout'),
    
    # Новые пути для инвентаря
    path('equipment/', EquipmentListView.as_view(), name='equipment_list'),
    path('my-rentals/', MyRentalsView.as_view(), name='my_rentals'),
    path('rent/<int:pk>/', rent_equipment, name='rent_equipment'),
    path('return/<int:pk>/', return_equipment, name='return_equipment'),
    path('trainer/equipment/', AllEquipmentView.as_view(), name='trainer_equipment'),
    path('trainer/rentals/', RentalHistoryView.as_view(), name='trainer_rentals'),
    path('maintenance/', maintenance_list, name='maintenance_list'),
    path('maintenance/new/', maintenance_create, name='maintenance_create'),
    path('maintenance/<int:pk>/edit/', maintenance_edit, name='maintenance_edit'),
    path('maintenance/<int:pk>/', maintenance_detail, name='maintenance_detail'),
]