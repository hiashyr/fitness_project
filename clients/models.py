from django.db import models
from django.contrib.auth.models import User, Group

class Equipment(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    status = models.CharField(
        max_length=10,
        choices=[('available', 'Доступен'), ('rented', 'В аренде')],
        default='available'
    )
    added_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

class Rental(models.Model):
    client = models.ForeignKey(User, on_delete=models.CASCADE)
    equipment = models.ForeignKey(Equipment, on_delete=models.CASCADE)
    rented_at = models.DateTimeField(auto_now_add=True)
    returned_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.client.username} → {self.equipment.name}"