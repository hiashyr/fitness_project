from django.shortcuts import render, get_object_or_404, redirect
from django.views.generic import ListView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.db.models import Q
from django.contrib.auth import login, logout
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.models import Group
from django.core.exceptions import ValidationError
from datetime import timedelta

from .models import Equipment, Rental
from .forms import UserRegisterForm, RentEquipmentForm

def trainer_check(user):
    """Проверка, является ли пользователь тренером"""
    return user.is_trainer()

class AllEquipmentView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    """Просмотр всего оборудования для тренеров"""
    model = Equipment
    template_name = 'clients/trainer/all_equipment.html'
    context_object_name = 'equipment'
    paginate_by = 20

    def test_func(self):
        return self.request.user.is_trainer()
    
    def get_queryset(self):
        return Equipment.objects.all() \
            .select_related() \
            .order_by('status', 'name')

class RentalHistoryView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    """История аренд для тренеров"""
    model = Rental
    template_name = 'clients/trainer/rental_history.html'
    context_object_name = 'rentals'
    paginate_by = 20
    ordering = ['-start_time']
    
    def test_func(self):
        return self.request.user.is_trainer()
    
    def get_queryset(self):
        queryset = super().get_queryset() \
            .select_related('client', 'equipment')
        
        status = self.request.GET.get('status')
        if status == 'active':
            queryset = queryset.filter(returned_at__isnull=True)
        elif status == 'returned':
            queryset = queryset.filter(returned_at__isnull=False)
            
        return queryset
    
    def get(self, request, *args, **kwargs):
        if request.GET.get('export') == 'csv':
            return self.export_to_csv()
        return super().get(request, *args, **kwargs)
    
    def export_to_csv(self):
        """Экспорт истории аренд в CSV"""
        import csv
        from django.http import HttpResponse
        
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="rentals_history.csv"'
        
        writer = csv.writer(response)
        writer.writerow([
            'Клиент', 'Оборудование', 
            'Начало аренды', 'Конец аренды', 
            'Возвращено', 'Статус', 'Длительность (ч)'
        ])
        
        for rental in self.get_queryset():
            status = 'Завершена' if rental.returned_at else 'Активна'
            duration = rental.duration / 60 if hasattr(rental, 'duration') else 0
            
            writer.writerow([
                rental.client.username,
                rental.equipment.name,
                rental.start_time.strftime('%d.%m.%Y %H:%M'),
                rental.end_time.strftime('%d.%m.%Y %H:%M'),
                rental.returned_at.strftime('%d.%m.%Y %H:%M') if rental.returned_at else '',
                status,
                f"{duration:.1f}"
            ])
        
        return response

def home(request):
    """Главная страница"""
    return render(request, 'clients/home.html', {
        'title': 'Главная страница фитнес-центра'
    })

def register(request):
    """Регистрация нового пользователя"""
    if request.method == 'POST':
        form = UserRegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            try:
                client_group = Group.objects.get(name='Клиенты')
                user.groups.add(client_group)
            except Group.DoesNotExist:
                pass
            login(request, user)
            messages.success(request, 'Регистрация прошла успешно!')
            return redirect('home')
    else:
        form = UserRegisterForm()
    
    return render(request, 'clients/register.html', {'form': form})

def user_login(request):
    """Авторизация пользователя"""
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            messages.success(request, f'Добро пожаловать, {user.username}!')
            return redirect('home')
    else:
        form = AuthenticationForm()
    
    return render(request, 'clients/login.html', {'form': form})

@login_required
def user_logout(request):
    """Выход из системы"""
    logout(request)
    messages.info(request, 'Вы успешно вышли из системы')
    return redirect('home')

class EquipmentListView(LoginRequiredMixin, ListView):
    """Список доступного оборудования"""
    model = Equipment
    template_name = 'clients/equipment_list.html'
    context_object_name = 'equipment'
    paginate_by = 12
    
    def get_queryset(self):
        now = timezone.now()
        rented_ids = Rental.objects.filter(
            end_time__gt=now,
            start_time__lt=now,
            returned_at__isnull=True
        ).values_list('equipment_id', flat=True)
        
        return Equipment.objects.exclude(
            id__in=rented_ids
        ).filter(status='available').order_by('name')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        now = timezone.now()
        
        context['current_rentals'] = {
            r.equipment_id: r for r in 
            Rental.objects.filter(
                end_time__gt=now,
                start_time__lt=now,
                returned_at__isnull=True
            ).select_related('equipment')
        }
        return context

class MyRentalsView(LoginRequiredMixin, ListView):
    """Список аренд текущего пользователя"""
    model = Rental
    template_name = 'clients/my_rentals.html'
    context_object_name = 'rentals'
    paginate_by = 10
    
    def get_queryset(self):
        return Rental.objects.filter(
            client=self.request.user
        ).select_related('equipment') \
         .order_by('-start_time')

@login_required
def rent_equipment(request, pk):
    equipment = get_object_or_404(Equipment, pk=pk)
    
    if request.method == 'POST':
        form = RentEquipmentForm(request.POST, equipment=equipment, user=request.user)
        if form.is_valid():
            try:
                rental = form.save()  # Теперь equipment будет установлен
                equipment.status = 'rented'
                equipment.save()
                
                messages.success(request, f'Вы успешно арендовали {equipment.name}')
                return redirect('my_rentals')
            except Exception as e:
                messages.error(request, f'Ошибка: {str(e)}')
    else:
        form = RentEquipmentForm(equipment=equipment)
    
    return render(request, 'clients/rent_equipment.html', {
        'form': form,
        'equipment': equipment
    })
    equipment = get_object_or_404(Equipment, pk=pk)
    
    if request.method == 'POST':
        form = RentEquipmentForm(
            request.POST,
            equipment=equipment,  # Передаем оборудование
            user=request.user     # Передаем пользователя
        )
        if form.is_valid():
            try:
                rental = form.save()
                equipment.status = 'rented'
                equipment.save()
                
                messages.success(
                    request,
                    f'Вы успешно арендовали {equipment.name} '
                    f'с {rental.start_time.strftime("%d.%m.%Y %H:%M")} '
                    f'до {rental.end_time.strftime("%d.%m.%Y %H:%M")}'
                )
                return redirect('my_rentals')
            except Exception as e:
                messages.error(request, f'Ошибка при создании аренды: {str(e)}')
    else:
        form = RentEquipmentForm(equipment=equipment)
    
    return render(request, 'clients/rent_equipment.html', {
        'form': form,
        'equipment': equipment
    })

@login_required
def return_equipment(request, pk):
    """Возврат оборудования"""
    rental = get_object_or_404(
        Rental, 
        pk=pk, 
        client=request.user,
        returned_at__isnull=True
    )
    
    rental.returned_at = timezone.now()
    rental.save()
    
    equipment = rental.equipment
    equipment.status = 'available'
    equipment.save()
    
    messages.success(
        request,
        f'Вы вернули {equipment.name}. '
        f'Аренда длилась {rental.duration // 60} ч. {rental.duration % 60} мин.'
    )
    return redirect('my_rentals')