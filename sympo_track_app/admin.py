from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.translation import gettext_lazy as _
from .models import (
    User,
    Language,
    Country,
    State,
    City,
    EventAddress,
    EventCategories,
    Event,
    EventCategoryRel,
    EventStagesType,
    EventStage,
    EventPricing,
    EventRole,
    ManagementGroup,
    ManagementGroupMember,
    EventSubscription,
    UserStageRequirement,
    CancellationReason,
    NotificationsSubject,
    Notification,
)

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

# ===========================================================
# USUÁRIOS
# ===========================================================

admin.site.register(User, CustomUserAdmin)

# ===========================================================
# LOCALIZAÇÃO
# ===========================================================

admin.site.register(Language)
admin.site.register(Country)
admin.site.register(State)
admin.site.register(City)
admin.site.register(EventAddress)

# ===========================================================
# EVENTOS
# ===========================================================

admin.site.register(EventCategories)
admin.site.register(Event)
admin.site.register(EventCategoryRel)
admin.site.register(EventStagesType)
admin.site.register(EventStage)
admin.site.register(EventPricing)

# ===========================================================
# GESTÃO
# ===========================================================

admin.site.register(EventRole)
admin.site.register(ManagementGroup)
admin.site.register(ManagementGroupMember)

# ===========================================================
# INSCRIÇÕES
# ===========================================================

admin.site.register(EventSubscription)
admin.site.register(UserStageRequirement)
admin.site.register(CancellationReason)

# ===========================================================
# NOTIFICAÇÕES
# ===========================================================

admin.site.register(NotificationsSubject)
admin.site.register(Notification)