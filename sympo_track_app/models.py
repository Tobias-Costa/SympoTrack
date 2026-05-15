import re
from django.db import models
from django.core import validators
from django.utils import timezone
from django.core.mail import send_mail
from django.utils.translation import gettext_lazy as _
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager

# Create your models here.

# -----------------------------------------------------------
# USUÁRIO
# -----------------------------------------------------------

class UserManager(BaseUserManager):
    def _create_user(self, username, email, password, is_staff, is_superuser, **extra_fields):
        now = timezone.now()
        if not username:
            raise ValueError(_('The given username must be set'))
        
        email = self.normalize_email(email)
        user = self.model(username=username, email=email,
            is_staff=is_staff, is_active=True,
            is_superuser=is_superuser, last_login=now,
            date_joined=now, **extra_fields
        )
        user.set_password(password)
        user.save(using=self._db)
        return user
    
    def create_user(self, username, email=None, password=None, **extra_fields):
        return self._create_user(username, email, password, False, False,
        **extra_fields)
    
    def create_superuser(self, username, email, password, **extra_fields):
        user=self._create_user(username, email, password, True, True,
        **extra_fields)
        user.is_active=True
        user.save(using=self._db)
        return user

# Recriando tabela User
class User(AbstractBaseUser, PermissionsMixin):
    username = models.CharField(_('username'), max_length=15, unique=True, help_text=_('Required. 15 characters or fewer. Letters, numbers and @/./+/-/_ characters'), validators=[ validators.RegexValidator(re.compile('^[\w.@+-]+$'), _('Enter a valid username.'), _('invalid'))])
    first_name = models.CharField(_('first name'), max_length=30)
    last_name = models.CharField(_('last name'), max_length=30)
    email = models.EmailField(_('email address'), max_length=255, unique=True)
    is_staff = models.BooleanField(_('staff status'), default=False, help_text=_('Designates whether the user can log into this admin site.'))
    is_active = models.BooleanField(_('active'), default=True, help_text=_('Designates whether this user should be treated as active. Unselect this instead of deleting accounts.'))
    date_joined = models.DateTimeField(_('date joined'), default=timezone.now)

    # Novos campos de User
    cpf = models.CharField('CPF',max_length=11, unique=True, null=True, blank=True)
    telephone1 = models.CharField(_('Telefone 1'), max_length=15, null=True, blank=True)
    telephone2 = models.CharField(_('Telefone 2'), max_length=15, null=True, blank=True)
    profile_completed = models.BooleanField(_('Indicador de perfil completo'), default=False)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username', 'first_name', 'last_name']

    objects = UserManager()

    class Meta:
        verbose_name = _('user')
        verbose_name_plural = _('users')

    def get_full_name(self):
        """Retorna o nome completo do usuário"""
        full_name = (f"{self.first_name} {self.last_name}")    
        return full_name.strip()
    
    def get_short_name(self):
        """Retorna o primeiro nome do usuário"""
        return self.first_name
    
    def email_user(self, subject, message, from_email=None):
        """Envia um e-mail para este usuário"""
        send_mail(subject, message, from_email, [self.email])


from django.db import models
from django.utils.translation import gettext_lazy as _


# -----------------------------------------------------------
# CADASTRO DE EVENTO
# -----------------------------------------------------------

class Language(models.Model):
    language = models.CharField(
        _("Idioma"),
        max_length=255
    )

    class Meta:
        verbose_name = _("Idioma")
        verbose_name_plural = _("Idiomas")

    def __str__(self):
        return self.language


class Country(models.Model):
    name = models.CharField(
        _("Nome"),
        max_length=255
    )

    abbr = models.CharField(
        _("Sigla"),
        max_length=10
    )

    class Meta:
        verbose_name = _("País")
        verbose_name_plural = _("Países")

    def __str__(self):
        return self.name


class State(models.Model):
    name = models.CharField(
        _("Nome"),
        max_length=255
    )

    uf = models.CharField(
        _("UF"),
        max_length=10
    )

    country = models.ForeignKey(
        Country,
        verbose_name=_("País"),
        on_delete=models.CASCADE,
        related_name="states"
    )

    class Meta:
        verbose_name = _("Estado")
        verbose_name_plural = _("Estados")

    def __str__(self):
        return f"{self.name} - {self.country.abbr}"


class City(models.Model):
    name = models.CharField(
        _("Nome"),
        max_length=255
    )

    state = models.ForeignKey(
        State,
        verbose_name=_("Estado"),
        on_delete=models.CASCADE,
        related_name="cities"
    )

    class Meta:
        verbose_name = _("Cidade")
        verbose_name_plural = _("Cidades")

    def __str__(self):
        return f"{self.name} - {self.state.uf}"


class EventAddress(models.Model):
    place_name = models.CharField(
        _("Nome do local"),
        max_length=255
    )

    street = models.CharField(
        _("Rua"),
        max_length=255
    )

    number = models.CharField(
        _("Número"),
        max_length=10,
        null=True,
        blank=True
    )

    complement = models.CharField(
        _("Complemento"),
        max_length=255,
        null=True,
        blank=True
    )

    neighborhood = models.CharField(
        _("Bairro"),
        max_length=255,
        null=True,
        blank=True
    )

    cep = models.CharField(
        _("CEP"),
        max_length=20,
        null=True,
        blank=True
    )

    city = models.ForeignKey(
        City,
        verbose_name=_("Cidade"),
        on_delete=models.CASCADE,
        related_name="event_addresses"
    )

    created_at = models.DateTimeField(
        _("Data de criação"),
        auto_now_add=True
    )

    class Meta:
        verbose_name = _("Endereço do evento")
        verbose_name_plural = _("Endereços dos eventos")

    def __str__(self):
        return f"{self.place_name} - {self.city.name}"


class EventCategories(models.Model):
    name = models.CharField(
        _("Nome"),
        max_length=255
    )

    class Meta:
        verbose_name = _("Categoria do evento")
        verbose_name_plural = _("Categorias dos eventos")

    def __str__(self):
        return self.name


class Event(models.Model):
    title = models.CharField(
        _("Título"),
        max_length=255
    )

    description = models.TextField(
        _("Descrição")
    )

    subject = models.CharField(
        _("Tema"),
        max_length=255
    )

    address = models.ForeignKey(
        EventAddress,
        verbose_name=_("Endereço"),
        on_delete=models.CASCADE,
        related_name="events"
    )

    language = models.ForeignKey(
        Language,
        verbose_name=_("Idioma"),
        on_delete=models.CASCADE,
        related_name="events"
    )

    external_link = models.URLField(
        _("Link externo")
    )

    is_public = models.BooleanField(
        _("Evento público"),
        default=True
    )

    creator = models.ForeignKey(
        'User',
        verbose_name=_("Criador"),
        on_delete=models.CASCADE,
        related_name="created_events"
    )

    categories = models.ManyToManyField(
        EventCategories,
        verbose_name=_("Categorias"),
        through='EventCategoryRel'
    )

    created_at = models.DateTimeField(
        _("Data de criação"),
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        _("Última atualização"),
        auto_now=True
    )

    class Meta:
        verbose_name = _("Evento")
        verbose_name_plural = _("Eventos")

    def __str__(self):
        return self.title


class EventCategoryRel(models.Model):
    category = models.ForeignKey(
        EventCategories,
        verbose_name=_("Categoria"),
        on_delete=models.CASCADE
    )

    event = models.ForeignKey(
        Event,
        verbose_name=_("Evento"),
        on_delete=models.CASCADE
    )

    class Meta:
        verbose_name = _("Relação de categoria")
        verbose_name_plural = _("Relações de categorias")
        unique_together = ('category', 'event')


class EventStagesType(models.Model):
    event_stage_type_name = models.CharField(
        _("Nome da etapa"),
        max_length=255
    )

    class Meta:
        verbose_name = _("Tipo de etapa")
        verbose_name_plural = _("Tipos de etapas")

    def __str__(self):
        return self.event_stage_type_name


class EventStage(models.Model):
    event = models.ForeignKey(
        Event,
        verbose_name=_("Evento"),
        on_delete=models.CASCADE,
        related_name="stages"
    )

    stage_type = models.ForeignKey(
        EventStagesType,
        verbose_name=_("Tipo da etapa"),
        on_delete=models.CASCADE
    )

    start_date = models.DateTimeField(
        _("Data inicial")
    )

    end_date = models.DateTimeField(
        _("Data final")
    )

    class Meta:
        verbose_name = _("Etapa do evento")
        verbose_name_plural = _("Etapas do evento")

    def __str__(self):
        return f"{self.event.title} - {self.stage_type.event_stage_type_name}"


class EventPricing(models.Model):

    CATEGORY_CHOICES = [
        ("PROFISSIONAL", _("Profissional")),
        ("POS", _("Pós-graduação")),
        ("GRADUACAO", _("Graduação")),
    ]

    event = models.ForeignKey(
        Event,
        verbose_name=_("Evento"),
        on_delete=models.CASCADE,
        related_name="prices"
    )

    category = models.CharField(
        _("Categoria"),
        max_length=100,
        choices=CATEGORY_CHOICES
    )

    batch = models.CharField(
        _("Lote"),
        max_length=50,
        default="Lote 1"
    )

    price = models.DecimalField(
        _("Preço"),
        max_digits=10,
        decimal_places=2
    )

    class Meta:
        verbose_name = _("Preço do evento")
        verbose_name_plural = _("Preços do evento")

    def __str__(self):
        return f"{self.event.title} - {self.category}"


# -----------------------------------------------------------
# GESTÃO DO EVENTO
# -----------------------------------------------------------

class EventRole(models.Model):
    role = models.CharField(
        _("Função"),
        max_length=255
    )

    class Meta:
        verbose_name = _("Função do evento")
        verbose_name_plural = _("Funções do evento")

    def __str__(self):
        return self.role


class ManagementGroup(models.Model):
    name = models.CharField(
        _("Nome"),
        max_length=255
    )

    event = models.ForeignKey(
        Event,
        verbose_name=_("Evento"),
        on_delete=models.CASCADE,
        related_name="management_groups"
    )

    class Meta:
        verbose_name = _("Grupo de gestão")
        verbose_name_plural = _("Grupos de gestão")

    def __str__(self):
        return f"{self.name} - {self.event.title}"


class ManagementGroupMember(models.Model):
    group = models.ForeignKey(
        ManagementGroup,
        verbose_name=_("Grupo"),
        on_delete=models.CASCADE,
        related_name="members"
    )

    user = models.ForeignKey(
        'User',
        verbose_name=_("Usuário"),
        on_delete=models.CASCADE
    )

    role = models.ForeignKey(
        EventRole,
        verbose_name=_("Função"),
        on_delete=models.CASCADE
    )

    class Meta:
        verbose_name = _("Membro do grupo")
        verbose_name_plural = _("Membros dos grupos")
        unique_together = ('group', 'user', 'role')


# -----------------------------------------------------------
# INSCRIÇÕES E PARTICIPAÇÃO
# -----------------------------------------------------------

class EventSubscription(models.Model):

    STATUS_CHOICES = [
        ("INSCRITO", _("Inscrito")),
        ("PENDENTE", _("Pendente")),
        ("CONFIRMADO", _("Confirmado")),
        ("EXPIRADO", _("Expirado")),
    ]

    event = models.ForeignKey(
        Event,
        verbose_name=_("Evento"),
        on_delete=models.CASCADE,
        related_name="subscriptions"
    )

    user = models.ForeignKey(
        'User',
        verbose_name=_("Usuário"),
        on_delete=models.CASCADE,
        related_name="subscriptions"
    )

    status = models.CharField(
        _("Status"),
        max_length=20,
        choices=STATUS_CHOICES
    )

    created_at = models.DateTimeField(
        _("Data de criação"),
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        _("Última atualização"),
        auto_now=True
    )

    class Meta:
        verbose_name = _("Inscrição")
        verbose_name_plural = _("Inscrições")

    def __str__(self):
        return f"{self.user.username} - {self.event.title}"


class UserStageRequirement(models.Model):
    event_stage = models.ForeignKey(
        EventStage,
        verbose_name=_("Etapa do evento"),
        on_delete=models.CASCADE,
        related_name="stage_requirements"
    )

    subscription = models.ForeignKey(
        EventSubscription,
        verbose_name=_("Inscrição"),
        on_delete=models.CASCADE
    )

    is_completed = models.BooleanField(
        _("Concluído"),
        default=False
    )

    created_at = models.DateTimeField(
        _("Data de criação"),
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        _("Última atualização"),
        auto_now=True
    )

    class Meta:
        verbose_name = _("Requisito da etapa")
        verbose_name_plural = _("Requisitos das etapas")


class CancellationReason(models.Model):
    subscription = models.ForeignKey(
        EventSubscription,
        verbose_name=_("Inscrição"),
        on_delete=models.CASCADE,
        related_name="cancellation_reasons"
    )

    reason_text = models.TextField(
        _("Motivo")
    )

    created_at = models.DateTimeField(
        _("Data de criação"),
        auto_now_add=True
    )

    class Meta:
        verbose_name = _("Motivo de cancelamento")
        verbose_name_plural = _("Motivos de cancelamento")


# -----------------------------------------------------------
# NOTIFICAÇÕES
# -----------------------------------------------------------

class NotificationsSubject(models.Model):
    message_subject = models.CharField(
        _("Assunto"),
        max_length=255
    )

    class Meta:
        verbose_name = _("Assunto da notificação")
        verbose_name_plural = _("Assuntos das notificações")

    def __str__(self):
        return self.message_subject


class Notification(models.Model):
    user = models.ForeignKey(
        'User',
        verbose_name=_("Usuário"),
        on_delete=models.CASCADE,
        related_name="notifications"
    )

    subject = models.ForeignKey(
        NotificationsSubject,
        verbose_name=_("Assunto"),
        on_delete=models.CASCADE
    )

    title = models.CharField(
        _("Título"),
        max_length=255
    )

    message = models.TextField(
        _("Mensagem")
    )

    created_at = models.DateTimeField(
        _("Data de criação"),
        auto_now_add=True
    )

    class Meta:
        verbose_name = _("Notificação")
        verbose_name_plural = _("Notificações")

    def __str__(self):
        return self.title