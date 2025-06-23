from django.shortcuts import render, get_object_or_404, redirect
from django.views.generic import ListView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.utils import timezone
from .models import Equipment, Rental
from .forms import UserRegisterForm
from django.contrib.auth import login, logout
from django.contrib.auth.forms import AuthenticationForm  # Добавлен этот импорт
from django.contrib.auth.models import Group
from django.contrib.auth import get_user_model
from .models import Equipment, Rental

def trainer_check(user):
    return user.is_trainer()

class AllEquipmentView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    model = Equipment
    template_name = 'clients/trainer/all_equipment.html'
    context_object_name = 'equipment'
    
    def test_func(self):
        return self.request.user.is_trainer()
    
    def get_queryset(self):
        return Equipment.objects.all().order_by('status', 'name')

class RentalHistoryView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    model = Rental
    template_name = 'clients/trainer/rental_history.html'
    context_object_name = 'rentals'
    paginate_by = 20
    
    def test_func(self):
        return self.request.user.is_trainer()
    
    def get_queryset(self):
        queryset = Rental.objects.all().select_related('client', 'equipment').order_by('-rented_at')
        
        # Фильтрация по статусу
        status = self.request.GET.get('status')
        if status == 'active':
            queryset = queryset.filter(returned_at__isnull=True)
        elif status == 'returned':
            queryset = queryset.filter(returned_at__isnull=False)
            
        return queryset
    
    def get(self, request, *args, **kwargs):
        # Обработка экспорта в CSV
        if request.GET.get('export') == 'csv':
            return self.export_to_csv()
        return super().get(request, *args, **kwargs)
    
    def export_to_csv(self):
        import csv
        from django.http import HttpResponse
        
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="rentals_history.csv"'
        
        writer = csv.writer(response)
        writer.writerow(['Клиент', 'Оборудование', 'Дата аренды', 'Дата возврата', 'Статус'])
        
        for rental in self.get_queryset():
            status = 'Завершена' if rental.returned_at else 'Активна'
            writer.writerow([
                rental.client.username,
                rental.equipment.name,
                rental.rented_at.strftime('%d.%m.%Y %H:%M'),
                rental.returned_at.strftime('%d.%m.%Y %H:%M') if rental.returned_at else '',
                status
            ])
        
        return response

def home(request):
    """Главная страница"""
    context = {
        'title': 'Главная страница фитнес-центра'
    }
    return render(request, 'clients/home.html', context)

def register(request):
    """Регистрация нового пользователя"""
    if request.method == 'POST':
        form = UserRegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            # Добавляем пользователя в группу "Клиенты" (если она существует)
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
    paginate_by = 10  # Пагинация по 10 элементов
    
    def get_queryset(self):
        return Equipment.objects.filter(status='available').order_by('name')

class MyRentalsView(LoginRequiredMixin, ListView):
    """Список аренд текущего пользователя"""
    model = Rental
    template_name = 'clients/my_rentals.html'
    context_object_name = 'rentals'
    
    def get_queryset(self):
        return Rental.objects.filter(client=self.request.user).order_by('-rented_at')

@login_required
def rent_equipment(request, pk):
    """Аренда оборудования"""
    equipment = get_object_or_404(Equipment, pk=pk)
    
    # Проверка доступности оборудования
    if equipment.status != 'available':
        messages.error(request, 'Это оборудование недоступно для аренды')
        return redirect('equipment_list')
    
    # Проверка, не арендовал ли пользователь уже это оборудование
    active_rental = Rental.objects.filter(
        client=request.user,
        equipment=equipment,
        returned_at__isnull=True
    ).exists()
    
    if active_rental:
        messages.warning(request, 'Вы уже арендовали это оборудование')
        return redirect('my_rentals')
    
    # Создание аренды
    equipment.status = 'rented'
    equipment.save()
    
    Rental.objects.create(
        client=request.user,
        equipment=equipment,
        notes=f"Аренда {equipment.name} через веб-интерфейс"
    )
    
    messages.success(request, f'Вы успешно арендовали {equipment.name}')
    return redirect('my_rentals')

@login_required
def return_equipment(request, pk):
    """Возврат оборудования"""
    rental = get_object_or_404(Rental, pk=pk, client=request.user)
    
    if rental.returned_at:
        messages.warning(request, 'Это оборудование уже было возвращено')
        return redirect('my_rentals')
    
    # Обновление данных о возврате
    rental.returned_at = timezone.now()
    rental.save()
    
    equipment = rental.equipment
    equipment.status = 'available'
    equipment.save()
    
    messages.success(request, f'Вы вернули {equipment.name}')
    return redirect('my_rentals')