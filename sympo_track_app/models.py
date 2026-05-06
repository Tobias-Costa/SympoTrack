from django.db import models
from django.contrib.auth.models import AbstractUser

# Create your models here.
class CustomUser(AbstractUser):
    #Adicionando novos campos à tabela User do Django
    cpf = models.CharField(max_length=11, unique=True)
    telefone1 = models.CharField(max_length=15, blank=False)
    telefone2 = models.CharField(max_length=15, blank=True)
    profile_completed = models.BooleanField(default=False, blank=False)
    