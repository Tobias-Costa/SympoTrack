import re
from django.db import models
from django.core import validators
from django.utils import timezone
from django.core.mail import send_mail
from django.utils.translation import gettext_lazy as _
from django.contrib.auth.models import (
    AbstractBaseUser,
    PermissionsMixin,
    BaseUserManager,
)

# -----------------------------------------------------------
# USUÁRIO
# -----------------------------------------------------------

class UserManager(BaseUserManager):
    def _create_user(
        self, username, email, password, is_staff, is_superuser, **extra_fields
    ):
        now = timezone.now()
        if not username:
            raise ValueError(_("The given username must be set"))

        email = self.normalize_email(email)
        user = self.model(
            username=username,
            email=email,
            is_staff=is_staff,
            is_active=True,
            is_superuser=is_superuser,
            last_login=now,
            date_joined=now,
            **extra_fields,
        )
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, username, email=None, password=None, **extra_fields):
        return self._create_user(
            username, email, password, False, False, **extra_fields
        )

    def create_superuser(self, username, email, password, **extra_fields):
        user = self._create_user(username, email, password, True, True, **extra_fields)
        user.is_active = True
        user.save(using=self._db)
        return user


# Recriando tabela User
class User(AbstractBaseUser, PermissionsMixin):
    username = models.CharField(
        _("username"),
        max_length=15,
        unique=True,
        help_text=_(
            "Required. 15 characters or fewer. Letters, numbers and @/./+/-/_ characters"
        ),
        validators=[
            validators.RegexValidator(
                re.compile(r"^[\w.@+-]+$"), _("Enter a valid username."), _("invalid")
            )
        ],
    )
    first_name = models.CharField(_("first name"), max_length=30)
    last_name = models.CharField(_("last name"), max_length=30)
    email = models.EmailField(_("email address"), max_length=255, unique=True)
    is_staff = models.BooleanField(
        _("staff status"),
        default=False,
        help_text=_("Designates whether the user can log into this admin site."),
    )
    is_active = models.BooleanField(
        _("active"),
        default=True,
        help_text=_(
            "Designates whether this user should be treated as active. Unselect this instead of deleting accounts."
        ),
    )
    date_joined = models.DateTimeField(_("date joined"), default=timezone.now)

    # Novos campos de User
    cpf = models.CharField("CPF", max_length=11, unique=True, null=True, blank=True)
    telephone1 = models.CharField(_("Telefone 1"), max_length=15, null=True, blank=True)
    telephone2 = models.CharField(_("Telefone 2"), max_length=15, null=True, blank=True)
    profile_completed = models.BooleanField(
        _("Indicador de perfil completo"), default=False
    )

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["username", "first_name", "last_name"]

    objects = UserManager()

    class Meta:
        verbose_name = _("user")
        verbose_name_plural = _("users")

    def get_full_name(self):
        """Retorna o nome completo do usuário"""
        full_name = f"{self.first_name} {self.last_name}"
        return full_name.strip()

    def get_short_name(self):
        """Retorna o primeiro nome do usuário"""
        return self.first_name

    def email_user(self, subject, message, from_email=None):
        """Envia um e-mail para este usuário"""
        send_mail(subject, message, from_email, [self.email])


# -----------------------------------------------------------
# GESTÃO DO EVENTO
# -----------------------------------------------------------


class ManagementGroup(models.Model):
    name = models.CharField(_("Nome"), max_length=150)

    description = models.TextField(verbose_name=_("Descrição"), blank=True)

    created_at = models.DateTimeField(verbose_name=_("Data de criação"), auto_now_add=True)

    updated_at = models.DateTimeField(verbose_name=_("Última atualização"), auto_now=True)

    members = models.ManyToManyField(
        User,
        through="ManagementGroupMember",
        related_name="management_groups"
    )

    class Meta:
        verbose_name = _("Grupo de gestão")
        verbose_name_plural = _("Grupos de gestão")

    def __str__(self):
        return f"{self.name}"


class ManagementGroupMember(models.Model):
    class Role(models.TextChoices):
        OWNER = "OWNER", "Proprietário"
        ADMIN = "ADMIN", "Administrador"
        MANAGER = "MANAGER", "Gestor"
        EDITOR = "EDITOR", "Editor"
        VIEWER = "VIEWER", "Visualizador"


    group = models.ForeignKey(
        ManagementGroup,
        verbose_name=_("Grupo"),
        on_delete=models.CASCADE,
        related_name="group_members",
    )

    user = models.ForeignKey(
        "User", verbose_name=_("Usuário"), on_delete=models.CASCADE
    )

    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.VIEWER
    )

    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("Membro do grupo")
        verbose_name_plural = _("Membros dos grupos")
        unique_together = ("group", "user")

    def __str__(self):
            return f"{self.group} - {self.user.first_name}({self.role})"


# -----------------------------------------------------------
# CADASTRO DE EVENTO
# -----------------------------------------------------------


class Language(models.Model):
    language = models.CharField(_("Idioma"), max_length=255)

    class Meta:
        verbose_name = _("Idioma")
        verbose_name_plural = _("Idiomas")

    def __str__(self):
        return self.language


class Country(models.Model):
    name = models.CharField(_("Nome"), max_length=255)

    abbr = models.CharField(_("Sigla"), max_length=10)

    class Meta:
        verbose_name = _("País")
        verbose_name_plural = _("Países")

    def __str__(self):
        return self.name


class State(models.Model):
    name = models.CharField(_("Nome"), max_length=255)

    uf = models.CharField(_("UF"), max_length=10)

    country = models.ForeignKey(
        Country, verbose_name=_("País"), on_delete=models.CASCADE, related_name="states"
    )

    class Meta:
        verbose_name = _("Estado")
        verbose_name_plural = _("Estados")

    def __str__(self):
        return f"{self.name} ({self.uf}) - {self.country.abbr}"


class City(models.Model):
    name = models.CharField(_("Nome"), max_length=255)

    state = models.ForeignKey(
        State, verbose_name=_("Estado"), on_delete=models.CASCADE, related_name="cities"
    )

    class Meta:
        verbose_name = _("Cidade")
        verbose_name_plural = _("Cidades")

    def __str__(self):
        return f"{self.name} - {self.state.uf}, {self.state.country.abbr}"


class EventAddress(models.Model):
    place_name = models.CharField(_("Nome do local"), max_length=255)

    street = models.CharField(_("Rua"), max_length=255)

    number = models.CharField(_("Número"), max_length=10, null=True, blank=True)

    complement = models.CharField(
        _("Complemento"), max_length=255, null=True, blank=True
    )

    neighborhood = models.CharField(_("Bairro"), max_length=255, null=True, blank=True)

    cep = models.CharField(_("CEP"), max_length=20, null=True, blank=True)

    city = models.ForeignKey(
        City,
        verbose_name=_("Cidade"),
        on_delete=models.CASCADE,
        related_name="event_addresses",
    )

    created_at = models.DateTimeField(_("Data de criação"), auto_now_add=True)

    class Meta:
        verbose_name = _("Endereço do evento")
        verbose_name_plural = _("Endereços dos eventos")

    def __str__(self):
        return f"{self.place_name} - {self.city.name}, {self.city.state.name}, {self.city.state.country}"


class EventCategoriesArea(models.Model):

    class College(models.TextChoices):
        EXATAS = "EXATAS", "COLÉGIO DE CIÊNCIAS EXATAS, TECNOLÓGICAS E MULTIDISCIPLINAR"
        HUMANIDADES = "HUMANAS", "COLÉGIO DE HUMANIDADES"
        VIDA = "VIDA", "COLÉGIO DE CIÊNCIAS DA VIDA"

    name = models.CharField(_("Nome"), max_length=255)
    college = models.CharField(_("Colégio"), max_length=8, choices=College.choices)

    class Meta:
            verbose_name = _("Área de categoria do evento")
            verbose_name_plural = _("Áreas de categorias dos eventos")
    
    def __str__(self):
        return self.name


class EventCategories(models.Model):
    name = models.CharField(_("Nome"), max_length=255)
    area = models.ForeignKey(
        EventCategoriesArea,
        verbose_name=_("Área"),
        on_delete=models.CASCADE,
        related_name="categories",
        null=True,
        blank=True,
    )

    class Meta:
        verbose_name = _("Categoria do evento")
        verbose_name_plural = _("Categorias dos eventos")

    def __str__(self):
        return self.name


class Event(models.Model):
    title = models.CharField(_("Título"), max_length=255)

    description = models.TextField(_("Descrição"))

    subject = models.CharField(_("Tema"), max_length=255)

    address = models.ForeignKey(
        EventAddress,
        verbose_name=_("Endereço"),
        on_delete=models.CASCADE,
        related_name="events",
    )

    language = models.ForeignKey(
        Language,
        verbose_name=_("Idioma"),
        on_delete=models.CASCADE,
        related_name="events",
    )

    external_link = models.URLField(_("Link externo"))

    is_public = models.BooleanField(_("Evento público"), default=True)

    creator = models.ForeignKey(
        "User",
        verbose_name=_("Criador"),
        on_delete=models.CASCADE,
        related_name="created_events",
    )

    categories = models.ManyToManyField(
        EventCategories, verbose_name=_("Categorias"), through="EventCategoryRel"
    )

    group = models.ForeignKey(
            ManagementGroup,
            verbose_name=_("Grupo"),
            on_delete=models.SET_NULL,
            related_name="management_groups",
            null=True,
            blank=True,
    )

    created_at = models.DateTimeField(_("Data de criação"), auto_now_add=True)

    updated_at = models.DateTimeField(_("Última atualização"), auto_now=True)

    class Meta:
        verbose_name = _("Evento")
        verbose_name_plural = _("Eventos")

    def __str__(self):
        return self.title


class EventCategoryRel(models.Model):
    category = models.ForeignKey(
        EventCategories, verbose_name=_("Categoria"), on_delete=models.CASCADE
    )

    event = models.ForeignKey(Event, verbose_name=_("Evento"), on_delete=models.CASCADE)

    class Meta:
        verbose_name = _("Relação de categoria")
        verbose_name_plural = _("Relações de categorias")
        unique_together = ("category", "event")

    def __str__(self):
        return f"{self.event.title} - {self.category.name}"


class EventStagesType(models.Model):
    name = models.CharField(_("Nome da etapa"), max_length=255)

    class Meta:
        verbose_name = _("Tipo de etapa")
        verbose_name_plural = _("Tipos de etapas")

    def __str__(self):
        return self.name


class EventStage(models.Model):
    event = models.ForeignKey(
        Event, verbose_name=_("Evento"), on_delete=models.CASCADE, related_name="stages"
    )

    stage_type = models.ForeignKey(
        EventStagesType, verbose_name=_("Tipo da etapa"), on_delete=models.CASCADE
    )

    start_date = models.DateTimeField(_("Data inicial"))

    end_date = models.DateTimeField(_("Data final"))

    class Meta:
        verbose_name = _("Etapa do evento")
        verbose_name_plural = _("Etapas do evento")

    def __str__(self):
        return f"{self.event.title} - {self.stage_type.name}"


class EventPricing(models.Model):

    CATEGORY_CHOICES = [
        ("PROFISSIONAL", _("Profissional")),
        ("POS", _("Pós-graduação")),
        ("GRADUACAO", _("Graduação")),
    ]

    event = models.ForeignKey(
        Event, verbose_name=_("Evento"), on_delete=models.CASCADE, related_name="prices"
    )

    category = models.CharField(
        _("Categoria"), max_length=100, choices=CATEGORY_CHOICES
    )

    batch = models.CharField(_("Lote"), max_length=50, default="Lote 1")

    price = models.DecimalField(_("Preço"), max_digits=10, decimal_places=2)

    class Meta:
        verbose_name = _("Preço do evento")
        verbose_name_plural = _("Preços do evento")

    def __str__(self):
        return f"{self.event.title} - {self.category}"


# -----------------------------------------------------------
# INSCRIÇÕES E PARTICIPAÇÃO
# -----------------------------------------------------------


class EventSubscription(models.Model):

    STATUS_CHOICES = [
        ("INSCRITO", _("Inscrito")),
        ("FINALIZADO", _("Finalizado")),
        ("EXPIRADO", _("Expirado")),
        ("CANCELADO", _("Cancelado")),
    ]

    event = models.ForeignKey(
        Event,
        verbose_name=_("Evento"),
        on_delete=models.CASCADE,
        related_name="subscriptions",
    )

    user = models.ForeignKey(
        "User",
        verbose_name=_("Usuário"),
        on_delete=models.CASCADE,
        related_name="subscriptions",
    )

    status = models.CharField(_("Status"), max_length=20, choices=STATUS_CHOICES)

    created_at = models.DateTimeField(_("Data de criação"), auto_now_add=True)

    updated_at = models.DateTimeField(_("Última atualização"), auto_now=True)

    class Meta:
        verbose_name = _("Inscrição")
        verbose_name_plural = _("Inscrições")
        # Impede inscrições duplicadas do mesmo usuário no mesmo evento
        unique_together = ("event", "user")

    def __str__(self):
        return f"{self.user.username} - {self.event.title}"


class UserStageRequirement(models.Model):
    event_stage = models.ForeignKey(
        EventStage,
        verbose_name=_("Etapa do evento"),
        on_delete=models.CASCADE,
        related_name="stage_requirements",
    )

    subscription = models.ForeignKey(
        EventSubscription, verbose_name=_("Inscrição"),
        on_delete=models.CASCADE,
        related_name="requirements",
    )

    is_completed = models.BooleanField(_("Concluído"), default=False)

    created_at = models.DateTimeField(_("Data de criação"), auto_now_add=True)

    updated_at = models.DateTimeField(_("Última atualização"), auto_now=True)

    class Meta:
        verbose_name = _("Requisito da etapa")
        verbose_name_plural = _("Requisitos das etapas")

    def __str__(self):
            return f"{self.event_stage.stage_type}({self.event_stage.event.title}) - {self.subscription.user}"


class CancellationReason(models.Model):
    subscription = models.ForeignKey(
        EventSubscription,
        verbose_name=_("Inscrição"),
        on_delete=models.CASCADE,
        related_name="cancellation_reasons",
    )

    reason_text = models.CharField(_("Motivo"), max_length=100)

    description = models.TextField(_("Descrição"), blank=True, null=True)

    rating = models.IntegerField(_("Avaliação"), blank=True, null=True)

    created_at = models.DateTimeField(_("Data de criação"), auto_now_add=True)

    class Meta:
        verbose_name = _("Motivo de cancelamento")
        verbose_name_plural = _("Motivos de cancelamento")

    def __str__(self):
        return f"{self.subscription.user.username}({self.subscription.event.title}) - {self.created_at}"


# -----------------------------------------------------------
# NOTIFICAÇÕES
# -----------------------------------------------------------

class Notification(models.Model):
    user = models.ForeignKey(
        "User",
        verbose_name=_("Usuário"),
        on_delete=models.CASCADE,
        related_name="notifications",
    )

    subject = models.CharField(_("Assunto"), max_length=155)

    title = models.CharField(_("Título"), max_length=155)

    message = models.TextField(_("Mensagem"))

    created_at = models.DateTimeField(_("Data de criação"), auto_now_add=True)

    class Meta:
        verbose_name = _("Notificação")
        verbose_name_plural = _("Notificações")

    def __str__(self):
        return self.title