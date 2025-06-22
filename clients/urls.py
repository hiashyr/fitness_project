from django.urls import path
from .views import (
    home, register, user_login, user_logout,
    EquipmentListView, MyRentalsView,
    rent_equipment, return_equipment,
    AllEquipmentView, RentalHistoryView
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
]