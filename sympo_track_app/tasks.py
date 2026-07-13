from celery import shared_task
from django.core.mail import send_mail
from .models import Notification
from .models import EventSubscription, EventStage, UserStageRequirement

@shared_task
def notify_subscription(subscription_id):
    subscription = EventSubscription.objects.select_related(
        "user", "event"
    ).get(id=subscription_id)

    # SALVA NO BANCO
    Notification.objects.create(
        user=subscription.user,
        subject="Inscrição confirmada",
        title=f"Inscrição confirmada — {subscription.event.title}",
        message=f"Sua inscrição no evento {subscription.event.title} foi realizada com sucesso.",
    )

    send_mail(
        subject=f"Inscrição confirmada — {subscription.event.title}",
        message=(
            f"Olá, {subscription.user.get_full_name()}!\n\n"
            f"Sua inscrição no evento {subscription.event.title} foi realizada com sucesso.\n\n"
            f"Acompanhe as etapas do evento pela plataforma."
        ),
        from_email=None,  # usa DEFAULT_FROM_EMAIL do settings
        recipient_list=[subscription.user.email],
    )


@shared_task
def notify_stage_starting(requirement_id):
    # SE O REQUISITO FOI DELETADO E RECRIADO, O ID ANTIGO NÃO EXISTE — ignora
    requirement = UserStageRequirement.objects.select_related(
        "subscription__user",
        "subscription__event",
        "event_stage__stage_type",
    ).filter(id=requirement_id).first()

    if not requirement:
        return

    subscription = requirement.subscription

    # NÃO ENVIA SE CANCELADO OU EXPIRADO
    if subscription.status in ["EXPIRADO", "CANCELADO"]:
        return

    # SALVA NO BANCO
    Notification.objects.create(
        user=subscription.user,
        subject="Nova etapa iniciada",
        title=f"Nova etapa iniciada — {subscription.event.title}",
        message=(
            f"Olá, {subscription.user.get_full_name()}!\n\n"
            f"A etapa {requirement.event_stage.stage_type.name} do evento {subscription.event.title} acabou de começar.\n\n"
            f"Prazo final: {requirement.event_stage.end_date.strftime('%d/%m/%Y %H:%M')}"
        ),
    )

    send_mail(
        subject=f"Nova etapa iniciada — {subscription.event.title}",
        message=(
            f"Olá, {subscription.user.get_full_name()}!\n\n"
            f"A etapa {requirement.event_stage.stage_type.name} do evento {subscription.event.title} acabou de começar.\n\n"
            f"Prazo final: {requirement.event_stage.end_date.strftime('%d/%m/%Y %H:%M')}"
        ),
        from_email=None,
        recipient_list=[subscription.user.email],
    )


@shared_task
def notify_stage_ending_soon(requirement_id):
    requirement = UserStageRequirement.objects.select_related(
        "subscription__user",
        "subscription__event",
        "event_stage__stage_type",
    ).filter(id=requirement_id).first()

    if not requirement:
        return

    subscription = requirement.subscription

    # NÃO ENVIA SE CANCELADO OU EXPIRADO
    if subscription.status in ["EXPIRADO", "CANCELADO"]:
        return

    # NÃO ENVIA SE JÁ COMPLETOU A ETAPA
    if requirement.is_completed:
        return

    # SALVA NO BANCO
    Notification.objects.create(
        user=subscription.user,
        subject="Etapa encerrando em breve",
        title=f"Etapa encerrando em breve — {subscription.event.title}",
        message=(
            f"Olá, {subscription.user.get_full_name()}!\n\n"
            f"A etapa {requirement.event_stage.stage_type.name} do evento {subscription.event.title} "
            f"encerrará em {requirement.event_stage.end_date.strftime('%d/%m/%Y %H:%M')}.\n\n"
            f"Não perca o prazo!"
        ),
    )

    send_mail(
        subject=f"Etapa encerrando em breve — {subscription.event.title}",
        message=(
            f"Olá, {subscription.user.get_full_name()}!\n\n"
            f"A etapa {requirement.event_stage.stage_type.name} do evento {subscription.event.title} "
            f"encerrará em {requirement.event_stage.end_date.strftime('%d/%m/%Y %H:%M')}.\n\n"
            f"Não perca o prazo!"
        ),
        from_email=None,
        recipient_list=[subscription.user.email],
    )


@shared_task
def notify_stage_expired(requirement_id):
    requirement = UserStageRequirement.objects.select_related(
        "subscription__user",
        "subscription__event",
        "event_stage__stage_type",
    ).filter(id=requirement_id).first()

    if not requirement:
        return

    subscription = requirement.subscription

    # NÃO PROCESSA SE JÁ CANCELADO OU EXPIRADO
    if subscription.status in ["EXPIRADO", "CANCELADO"]:
        return

    # SÓ EXPIRA SE NÃO COMPLETOU A ETAPA
    if requirement.is_completed:
        return

    # ATUALIZA STATUS DA INSCRIÇÃO
    subscription.status = "EXPIRADO"
    subscription.save()

    # SALVA NO BANCO
    Notification.objects.create(
        user=subscription.user,
        subject="Etapa expirada",
        title=f"Etapa expirada — {subscription.event.title}",
        message=(
            f"Olá, {subscription.user.get_full_name()}!\n\n"
            f"Infelizmente o prazo da etapa {requirement.event_stage.stage_type.name} do evento "
            f"{subscription.event.title} encerrou sem que você completasse o requisito.\n\n"
            f"Sua inscrição foi marcada como expirada."
        ),
    )

    send_mail(
        subject=f"Etapa expirada — {subscription.event.title}",
        message=(
            f"Olá, {subscription.user.get_full_name()}!\n\n"
            f"Infelizmente o prazo da etapa {requirement.event_stage.stage_type.name} do evento "
            f"{subscription.event.title} encerrou sem que você completasse o requisito.\n\n"
            f"Sua inscrição foi marcada como expirada."
        ),
        from_email=None,
        recipient_list=[subscription.user.email],
    )


@shared_task
def notify_unsubscribe(subscription_id):
    subscription = EventSubscription.objects.select_related(
        "user", "event"
    ).get(id=subscription_id)

    # SALVA NO BANCO
    Notification.objects.create(
        user=subscription.user,
        subject="Desinscrição confirmada",
        title=f"Desinscrição confirmada — {subscription.event.title}",
        message=(
            f"Olá, {subscription.user.get_full_name()}!\n\n"
            f"Sua desinscrição do evento {subscription.event.title} foi realizada com sucesso."          
        ),
    )

    send_mail(
        subject=f"Desinscrição confirmada — {subscription.event.title}",
        message=(
            f"Olá, {subscription.user.get_full_name()}!\n\n"
            f"Sua desinscrição do evento {subscription.event.title} foi realizada com sucesso."
        ),
        from_email=None,
        recipient_list=[subscription.user.email],
    )