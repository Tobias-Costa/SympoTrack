from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.translation import gettext_lazy as _
from .models import User

# Register your models here.

class CustomUserAdmin(UserAdmin):
    # Campos na lista principal
    list_display = ('email', 'username', 'is_active', 'is_staff', 'is_superuser', 'date_joined')

    fieldsets = (
        (None, {'fields': ('username', 'email', 'password')}),
        (_('Personal info'), {
            'fields': (
                'first_name', 
                'last_name',  
                'cpf',       
                'telephone1',  
                'telephone2', 
                'profile_completed'
            )
        }),
        (_('Permissions'), {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions'),
        }),
        (_('Important dates'), {'fields': ('last_login', 'date_joined')}),
    )

    # Para que apareçam também ao CADASTRAR um novo usuário
    add_fieldsets = UserAdmin.add_fieldsets + (
        (_('Personal info'), {
            'fields': ('email', 'first_name', 'last_name', 'cpf', 'telephone1', 'telephone2', 'profile_completed'),
        }),
        (_('Permissions'), {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions'),
        }),
        
    )

    ordering = ('email',)
    
admin.site.register(User, CustomUserAdmin)