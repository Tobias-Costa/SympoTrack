from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import DatabaseError, transaction
from django.db.models import Min, Max
from .models import (
    Language,
    State,
    City,
    EventAddress,
    EventCategories,
    Country,
    Event,
    EventCategoriesArea,
    EventPricing,
    EventStage,
    EventStagesType,
    EventSubscription,
    UserStageRequirement,
    ManagementGroup,
    ManagementGroupMember,
    CancellationReason,
    Notification,
)
from django.conf import settings
from django.utils import timezone
from datetime import timedelta
from .tasks import (
    notify_subscription,
    notify_stage_starting,
    notify_stage_ending_soon,
    notify_stage_expired,
    notify_unsubscribe,
)
from django.core.paginator import Paginator
import json


@login_required
def home(request):
    # Busca todos os eventos públicos pré-carregando as inscrições
    events = (
        Event.objects.filter(is_public=True)
        .prefetch_related("subscriptions")
        .order_by("-id")
    )

    # Paginação (12 eventos por página)
    paginator = Paginator(events, 12)

    page_number = request.GET.get("page")

    events = paginator.get_page(page_number)

    # Criação do booleano 'is_subscribed' para cada evento da lista
    for event in events:
        # Verifica se o id do usuário logado está na lista de inscrições ativas daquele evento
        event.is_subscribed = event.subscriptions.filter(
            user=request.user,
            status__in=["INSCRITO", "FINALIZADO"],
        ).exists()

        event.subscribed_count = event.subscriptions.filter(
            status__in=["INSCRITO", "FINALIZADO"],
        ).count()

    return render(request, "home.html", {"events": events})


@login_required
def register_event(request):
    # Busca todos os dados necessários para a rota GET funcionar
    languages = Language.objects.all().order_by("language")
    categories = EventCategories.objects.all().order_by("name")
    event_stage_types = EventStagesType.objects.all().order_by("name")
    areas = EventCategoriesArea.objects.prefetch_related("categories").order_by(
        "college", "name"
    )
    user_groups = ManagementGroup.objects.filter(members=request.user)
    context = {
        "languages": languages,
        "groups": user_groups,
        "selected_language": None,
        "selected_group": None,
        "category_options": categories,
        "geoapify_key": settings.GEOAPIFY_API_KEY,
        "areas": areas,
        "college_choices": EventCategoriesArea.College.choices,
        "event_stage_type_options": event_stage_types,
        "selected_categories": [],
        "stages_data": [],
        "prices_data": [],
        "is_public": True,
    }

    if request.method == "POST":
        # Atualizando context com dados do formulário
        context.update(
            {
                # INFORMAÇÕES DO EVENTO
                "title": request.POST.get("title", ""),
                "description": request.POST.get("description", ""),
                "subject": request.POST.get("subject", ""),
                "external_link": request.POST.get("external_link", ""),
                "is_public": "is_public" in request.POST,
                "selected_language": request.POST.get("language"),
                "selected_group": request.POST.get("group"),
                # ENDEREÇO
                "address_formatted": request.POST.get("address_formatted", ""),
                "place_name": request.POST.get("place_name", ""),
                "street": request.POST.get("street", ""),
                "number": request.POST.get("number", ""),
                "neighborhood": request.POST.get("neighborhood", ""),
                "cep": request.POST.get("cep", ""),
                "city_name": request.POST.get("city_name", ""),
                "state_name": request.POST.get("state_name", ""),
                "state_uf": request.POST.get("state_uf", ""),
                "country_name": request.POST.get("country_name", ""),
                "country_abbr": request.POST.get("country_abbr", ""),
                # CATEGORIAS
                "selected_categories": json.dumps(request.POST.getlist("categories")),
                # ETAPAS
                "stages_data": json.dumps(
                    [
                        list(item)
                        for item in zip(
                            request.POST.getlist("stage_type[]"),
                            request.POST.getlist("stage_start_date[]"),
                            request.POST.getlist("stage_end_date[]"),
                        )
                    ]
                ),
                # PREÇOS
                "prices_data": json.dumps(
                    [
                        list(item)
                        for item in zip(
                            request.POST.getlist("price_category[]"),
                            request.POST.getlist("batch[]"),
                            request.POST.getlist("price[]"),
                        )
                    ]
                ),
            }
        )

        # SALVANDO ENDEREÇOS
        country_name = request.POST.get("country_name")
        country_abbr = request.POST.get("country_abbr")

        state_name = request.POST.get("state_name")
        state_uf = request.POST.get("state_uf")

        city_name = request.POST.get("city_name")

        place_name = request.POST.get("place_name")

        street_name = request.POST.get("street")

        if not (place_name and street_name and city_name):
            messages.error(request, "Selecione um endereço válido no mapa.")
            return render(request, "register_event.html", context)

        try:
            # Se alguma operação falhar, todas as alterações no BD serão canceladas
            with transaction.atomic():

                # PAÍS — cria um genérico se não vier
                country, _ = Country.objects.get_or_create(
                    name=country_name or "(Não informado)",
                    defaults={"abbr": country_abbr.upper() if country_abbr else "N/I"},
                )

                # ESTADO — cria um genérico se não vier
                state, _ = State.objects.get_or_create(
                    name=state_name or "(Não informado)",
                    country=country,
                    defaults={"uf": state_uf.upper() if state_uf else "N/I"},
                )

                # CIDADE
                city, _ = City.objects.get_or_create(name=city_name, state=state)

                # ENDEREÇOS
                address, _ = EventAddress.objects.get_or_create(
                    place_name=place_name,
                    street=street_name,
                    city=city,
                    defaults={
                        "number": request.POST.get("number") or None,
                        "complement": request.POST.get("complement") or None,
                        "neighborhood": request.POST.get("neighborhood") or None,
                        "cep": request.POST.get("cep") or None,
                    },
                )

                # IDIOMA
                language = Language.objects.filter(
                    language=request.POST.get("language")
                ).first()

                if not language:
                    messages.error(request, "Selecione um idioma válido.")
                    return render(request, "register_event.html", context)

                # GRUPO
                group_id = request.POST.get("group")
                if group_id:
                    group = ManagementGroup.objects.filter(id=group_id).first()
                else:
                    group = None

                # EVENTO
                # Adicionar booleano em que se seleciona se o evento deve ser anexado a um grupo ou indivíduo
                event = Event.objects.create(
                    title=request.POST.get("title"),
                    description=request.POST.get("description"),
                    subject=request.POST.get("subject"),
                    external_link=request.POST.get("external_link"),
                    is_public=bool("is_public" in request.POST),
                    address=address,
                    language=language,
                    group=group,
                    creator=request.user,
                )

                # CATEGORIAS
                category_ids = request.POST.getlist("categories")
                if category_ids:
                    # Exclui categorias existentes relacionadas com o evento e adiciona ou mantém as escolhidas no select
                    event.categories.set(
                        EventCategories.objects.filter(id__in=category_ids)
                    )

                # ETAPAS
                stage_types = request.POST.getlist("stage_type[]")
                start_dates = request.POST.getlist("stage_start_date[]")
                end_dates = request.POST.getlist("stage_end_date[]")

                for stage_type_id, start_date, end_date in zip(
                    stage_types, start_dates, end_dates
                ):
                    if not (stage_type_id and start_date and end_date):
                        continue

                    stage_type = EventStagesType.objects.filter(
                        id=stage_type_id
                    ).first()
                    if not stage_type:
                        continue

                    EventStage.objects.create(
                        event=event,
                        stage_type=stage_type,
                        start_date=start_date,
                        end_date=end_date,
                    )

                # PREÇOS
                price_categories = request.POST.getlist("price_category[]")
                batches = request.POST.getlist("batch[]")
                prices = request.POST.getlist("price[]")

                for category, batch, price in zip(price_categories, batches, prices):
                    if not (category and price):
                        continue

                    EventPricing.objects.create(
                        event=event,
                        category=category,
                        batch=batch or "Lote 1",
                        price=price,
                    )

            # Seção de mensagens de sucesso e falha
            messages.success(request, "Evento cadastrado com sucesso.")
            return redirect("register_event")
        except Exception:
            messages.error(request, f"Erro ao salvar evento")

    return render(request, "register_event.html", context)


@login_required
def edit_event(request, event_id):
    event = get_object_or_404(Event, id=event_id)
    now = timezone.now()

    # PROTEÇÃO — apenas o criador ou membros com permissão podem editar
    is_creator = event.creator == request.user
    is_editor = (
        event.group
        and ManagementGroupMember.objects.filter(
            group=event.group,
            user=request.user,
            role__in=["OWNER", "ADMIN", "MANAGER"],
        ).exists()
    )

    if not (is_creator or is_editor):
        messages.error(request, "Você não tem permissão para editar este evento.")
        return redirect("event_detail", event_id=event.id)

    # DADOS PARA O FORMULÁRIO
    languages = Language.objects.all().order_by("language")
    categories = EventCategories.objects.all().order_by("name")
    event_stage_types = EventStagesType.objects.all().order_by("name")
    areas = EventCategoriesArea.objects.prefetch_related("categories").order_by(
        "college", "name"
    )
    user_groups = ManagementGroup.objects.filter(members=request.user)

    # DADOS EXISTENTES DO EVENTO PARA REPOPULAR O FORMULÁRIO
    existing_stages = list(
        event.stages.values_list("stage_type_id", "start_date", "end_date")
    )
    existing_prices = list(event.prices.values_list("category", "batch", "price"))

    context = {
        "event": event,
        "languages": languages,
        "groups": user_groups,
        "category_options": categories,
        "geoapify_key": settings.GEOAPIFY_API_KEY,
        "areas": areas,
        "college_choices": EventCategoriesArea.College.choices,
        "event_stage_type_options": event_stage_types,
        # REPOPULA COM DADOS EXISTENTES
        "title": event.title,
        "description": event.description,
        "subject": event.subject,
        "external_link": event.external_link,
        "is_public": event.is_public,
        "selected_language": event.language_id,
        "selected_group": event.group_id,
        # ENDEREÇO EXISTENTE
        "address_formatted": f"{event.address.street}, {event.address.number or ''} - {event.address.city.name}",
        "place_name": event.address.place_name,
        "street": event.address.street,
        "number": event.address.number or "",
        "neighborhood": event.address.neighborhood or "",
        "cep": event.address.cep or "",
        "city_name": event.address.city.name,
        "state_name": event.address.city.state.name,
        "state_uf": event.address.city.state.uf,
        "country_name": event.address.city.state.country.name,
        "country_abbr": event.address.city.state.country.abbr,
        # CATEGORIAS, ETAPAS E PREÇOS EXISTENTES
        "selected_categories": json.dumps(
            list(event.categories.values_list("id", flat=True))
        ),
        "stages_data": json.dumps(
            [
                [
                    str(s[0]),
                    timezone.localtime(s[1]).strftime("%Y-%m-%dT%H:%M"),
                    timezone.localtime(s[2]).strftime("%Y-%m-%dT%H:%M"),
                ]
                for s in existing_stages
            ]
        ),
        "prices_data": json.dumps([[p[0], p[1], str(p[2])] for p in existing_prices]),
    }

    if request.method == "POST":
        context.update(
            {
                "title": request.POST.get("title", ""),
                "description": request.POST.get("description", ""),
                "subject": request.POST.get("subject", ""),
                "external_link": request.POST.get("external_link", ""),
                "is_public": "is_public" in request.POST,
                "selected_language": request.POST.get("language"),
                "selected_group": request.POST.get("group"),
                "address_formatted": request.POST.get("address_formatted", ""),
                "place_name": request.POST.get("place_name", ""),
                "street": request.POST.get("street", ""),
                "number": request.POST.get("number", ""),
                "neighborhood": request.POST.get("neighborhood", ""),
                "cep": request.POST.get("cep", ""),
                "city_name": request.POST.get("city_name", ""),
                "state_name": request.POST.get("state_name", ""),
                "state_uf": request.POST.get("state_uf", ""),
                "country_name": request.POST.get("country_name", ""),
                "country_abbr": request.POST.get("country_abbr", ""),
                "selected_categories": json.dumps(request.POST.getlist("categories")),
                "stages_data": json.dumps(
                    [
                        list(item)
                        for item in zip(
                            request.POST.getlist("stage_type[]"),
                            request.POST.getlist("stage_start_date[]"),
                            request.POST.getlist("stage_end_date[]"),
                        )
                    ]
                ),
                "prices_data": json.dumps(
                    [
                        list(item)
                        for item in zip(
                            request.POST.getlist("price_category[]"),
                            request.POST.getlist("batch[]"),
                            request.POST.getlist("price[]"),
                        )
                    ]
                ),
            }
        )

        country_name = request.POST.get("country_name")
        country_abbr = request.POST.get("country_abbr")
        state_name = request.POST.get("state_name")
        state_uf = request.POST.get("state_uf")
        city_name = request.POST.get("city_name")
        place_name = request.POST.get("place_name")
        street_name = request.POST.get("street")

        if not (place_name and street_name and city_name):
            messages.error(request, "Selecione um endereço válido no mapa.")
            return render(request, "edit_event.html", context)

        try:
            with transaction.atomic():

                # PAÍS
                country, _ = Country.objects.get_or_create(
                    name=country_name or "(Não informado)",
                    defaults={"abbr": country_abbr.upper() if country_abbr else "N/I"},
                )

                # ESTADO
                state, _ = State.objects.get_or_create(
                    name=state_name or "(Não informado)",
                    country=country,
                    defaults={"uf": state_uf.upper() if state_uf else "N/I"},
                )

                # CIDADE
                city, _ = City.objects.get_or_create(name=city_name, state=state)

                # ENDEREÇO — atualiza o existente pelo ID
                address = event.address
                address.place_name = place_name
                address.street = street_name
                address.number = request.POST.get("number") or None
                address.complement = request.POST.get("complement") or None
                address.neighborhood = request.POST.get("neighborhood") or None
                address.cep = request.POST.get("cep") or None
                address.city = city
                address.save()

                # IDIOMA
                language = Language.objects.filter(
                    language=request.POST.get("language")
                ).first()

                if not language:
                    messages.error(request, "Selecione um idioma válido.")
                    return render(request, "edit_event.html", context)

                # GRUPO
                group_id = request.POST.get("group")
                group = (
                    ManagementGroup.objects.filter(id=group_id).first()
                    if group_id
                    else None
                )

                # EVENTO — atualiza os campos
                event.title = request.POST.get("title")
                event.description = request.POST.get("description")
                event.subject = request.POST.get("subject")
                event.external_link = request.POST.get("external_link") or ""
                event.is_public = "is_public" in request.POST
                event.language = language
                event.group = group
                event.save()

                # CATEGORIAS — substitui todas
                category_ids = request.POST.getlist("categories")
                event.categories.set(
                    EventCategories.objects.filter(id__in=category_ids)
                )

                # ETAPAS — apaga e recria
                event.stages.all().delete()
                for stage_type_id, start_date, end_date in zip(
                    request.POST.getlist("stage_type[]"),
                    request.POST.getlist("stage_start_date[]"),
                    request.POST.getlist("stage_end_date[]"),
                ):
                    if not (stage_type_id and start_date and end_date):
                        continue
                    stage_type = EventStagesType.objects.filter(
                        id=stage_type_id
                    ).first()
                    if not stage_type:
                        continue
                    EventStage.objects.create(
                        event=event,
                        stage_type=stage_type,
                        start_date=start_date,
                        end_date=end_date,
                    )

                # ATUALIZA REQUISITOS E NOTIFICAÇÕES DE TODOS OS INSCRITOS ATIVOS
                active_subscriptions = EventSubscription.objects.filter(
                    event=event,
                    status__in=["INSCRITO", "FINALIZADO"],
                )

                for subscription in active_subscriptions:

                    # SE ESTAVA FINALIZADO E HÁ NOVAS ETAPAS — volta para INSCRITO
                    if subscription.status == "FINALIZADO":
                        old_stage_ids = set(
                            subscription.requirements.values_list(
                                "event_stage_id", flat=True
                            )
                        )
                        new_stage_ids = set(event.stages.values_list("id", flat=True))

                        # SE HÁ ETAPAS NOVAS QUE O USUÁRIO AINDA NÃO TINHA — volta para INSCRITO
                        if new_stage_ids - old_stage_ids:
                            subscription.status = "INSCRITO"
                            subscription.save()

                    # DELETA REQUISITOS ANTIGOS — as tasks antigas vão buscar o requirement_id
                    # que não existe mais e retornarão sem enviar (Abordagem 3)
                    subscription.requirements.all().delete()

                    # RECRIA REQUISITOS E REAGENDA TASKS COM AS NOVAS ETAPAS
                    for stage in event.stages.all():

                        if stage.end_date <= now:
                            UserStageRequirement.objects.create(
                                event_stage=stage,
                                subscription=subscription,
                                is_completed=True,
                            )
                            continue

                        requirement = UserStageRequirement.objects.create(
                            event_stage=stage,
                            subscription=subscription,
                            is_completed=False,
                        )

                        if stage.start_date > now:
                            notify_stage_starting.apply_async(
                                args=[requirement.id],
                                eta=stage.start_date,
                            )

                        warning_time = stage.end_date - timedelta(hours=24)
                        if warning_time > now:
                            notify_stage_ending_soon.apply_async(
                                args=[requirement.id],
                                eta=warning_time,
                            )

                        notify_stage_expired.apply_async(
                            args=[requirement.id],
                            eta=stage.end_date,
                        )

                # PREÇOS — apaga e recria
                event.prices.all().delete()
                for category, batch, price in zip(
                    request.POST.getlist("price_category[]"),
                    request.POST.getlist("batch[]"),
                    request.POST.getlist("price[]"),
                ):
                    if not (category and price):
                        continue
                    EventPricing.objects.create(
                        event=event,
                        category=category,
                        batch=batch or "Lote 1",
                        price=price,
                    )

            messages.success(request, "Evento atualizado com sucesso.")
            return redirect("event_detail", event_id=event.id)

        except Exception as e:
            messages.error(request, f"Erro ao atualizar evento: {str(e)}")

    return render(request, "edit_event.html", context)


@login_required
def event_detail(request, event_id):
    event = get_object_or_404(
        Event.objects.select_related(
            "address__city__state__country",
            "language",
            "creator",
            "group",
        )
        .prefetch_related(
            "categories__area",
            "stages__stage_type",
            "prices",
            "subscriptions",
        )
        .annotate(
            min_start_date=Min("stages__start_date"),
            max_end_date=Max("stages__end_date"),
        ),
        id=event_id,
    )

    # PROTEÇÃO — evento privado só pode ser visto por:
    # 1. O criador
    # 2. Membros do grupo organizador
    # 3. Inscritos no evento
    if not event.is_public:
        is_creator = event.creator == request.user

        is_group_member = (
            event.group
            and ManagementGroupMember.objects.filter(
                group=event.group,
                user=request.user,
            ).exists()
        )

        is_subscribed = event.subscriptions.filter(user=request.user).exists()

        if not (is_creator or is_group_member or is_subscribed):
            messages.error(request, "Este evento é privado.")
            return redirect("home")

    # SALVA URL DE ORIGEM
    # Se existir '?next=' na URL (ou seja, veio da Home ou Grupos), salva na sessão
    if "next" in request.GET:
        request.session["event_back_url"] = request.GET["next"]

    # VERIFICA SE O USUÁRIO PODE EDITAR
    can_edit = False
    if event.creator == request.user:
        can_edit = True
    elif event.group:
        can_edit = ManagementGroupMember.objects.filter(
            group=event.group,
            user=request.user,
            role__in=["OWNER", "ADMIN", "MANAGER"],
        ).exists()

    is_subscribed = event.subscriptions.filter(
        user=request.user,
        status__in=["INSCRITO", "FINALIZADO"],
    ).exists()

    event.subscribed_count = event.subscriptions.filter(
        status__in=["INSCRITO", "FINALIZADO"],
    ).count()

    return render(
        request,
        "event_detail.html",
        {
            "event": event,
            "can_edit": can_edit,
            "is_subscribed": is_subscribed,
        },
    )


@login_required
def subscribe_event(request, event_id):
    event = get_object_or_404(Event, id=event_id)
    now = timezone.now()

    # PROTEÇÃO — evento privado
    if not event.is_public:
        is_creator = event.creator == request.user
        is_group_member = (
            event.group
            and ManagementGroupMember.objects.filter(
                group=event.group,
                user=request.user,
            ).exists()
        )

        if not (is_creator or is_group_member):
            messages.error(request, "Este evento é privado.")
            return redirect(request.META.get("HTTP_REFERER", "home"))

    try:
        with transaction.atomic():

            # VERIFICA SE JÁ EXISTE UMA INSCRIÇÃO
            subscription = EventSubscription.objects.filter(
                event=event, user=request.user
            ).first()

            if subscription:
                # JÁ INSCRITO OU CONFIRMADO — não faz nada
                if subscription.status in ["INSCRITO", "FINALIZADO"]:
                    messages.warning(request, "Você já está inscrito neste evento.")
                    return redirect(request.META.get("HTTP_REFERER", "home"))

                # CANCELADO OU EXPIRADO — reativa a inscrição
                subscription.status = "INSCRITO"
                subscription.save()

                # REMOVE REQUISITOS ANTIGOS PARA RECRIAR
                subscription.requirements.all().delete()

            else:
                # CRIA NOVA INSCRIÇÃO
                subscription = EventSubscription.objects.create(
                    event=event,
                    user=request.user,
                    status="INSCRITO",
                )

            # CRIA REQUISITOS E AGENDA NOTIFICAÇÕES PARA CADA ETAPA
            for stage in event.stages.all():

                # SE A ETAPA JÁ ACABOU — cria o requisito mas não agenda nada
                if stage.end_date <= now:
                    UserStageRequirement.objects.create(
                        event_stage=stage,
                        subscription=subscription,
                        is_completed=True,
                    )
                    continue

                # SE A ETAPA JÁ ESTÁ EM ANDAMENTO — cria o requisito mas não agenda início
                requirement = UserStageRequirement.objects.create(
                    event_stage=stage,
                    subscription=subscription,
                    is_completed=False,
                )

                # AGENDA INÍCIO — só se ainda não começou
                if stage.start_date > now:
                    notify_stage_starting.apply_async(
                        args=[requirement.id],
                        eta=stage.start_date,
                    )

                # AGENDA AVISO 24H ANTES DO FIM — só se ainda está no futuro
                warning_time = stage.end_date - timedelta(hours=24)
                if warning_time > now:
                    notify_stage_ending_soon.apply_async(
                        args=[requirement.id],
                        eta=warning_time,
                    )

                # AGENDA EXPIRAÇÃO — sempre que o fim ainda está no futuro
                notify_stage_expired.apply_async(
                    args=[requirement.id],
                    eta=stage.end_date,
                )

        # EMAIL DE CONFIRMAÇÃO
        notify_subscription.delay(subscription.id)

        messages.success(request, f"Inscrição realizada com sucesso em {event.title}.")

    except Exception as e:
        messages.error(request, f"Erro ao realizar inscrição: {str(e)}")

    return redirect(request.META.get("HTTP_REFERER", "home"))


@login_required
def unsubscribe_event(request, event_id):
    event = get_object_or_404(Event, id=event_id)
    subscription = get_object_or_404(EventSubscription, event=event, user=request.user)

    # SALVA URL DE ORIGEM
    # Se existir '?next=' na URL (ou seja, veio da Home ou Grupos), salva na sessão
    if "next" in request.GET:
        request.session["unsubscribe_back_url"] = request.GET["next"]

    # PROTEÇÃO — só cancela se estiver inscrito ou confirmado
    if subscription.status not in ["INSCRITO", "FINALIZADO"]:
        messages.warning(request, "Sua inscrição já está cancelada ou expirada.")
        return redirect(request.session.get("unsubscribe_back_url", "home"))

    if request.method == "POST":
        cancellation_reason = request.POST.get("reason")
        cancellation_description = request.POST.get("description")
        rating = request.POST.get("rating")

        if rating:
            rating = int(rating)

        try:
            with transaction.atomic():

                CancellationReason.objects.create(
                    subscription=subscription,
                    reason_text=cancellation_reason or None,
                    description=cancellation_description or None,
                    rating=rating or None,
                )

                # ATUALIZA STATUS PARA CANCELADO
                subscription.status = "CANCELADO"
                subscription.save()

            # ENVIA EMAIL DE DESINSCRIÇÃO
            notify_unsubscribe.delay(subscription.id)

            messages.success(
                request, f"Desinscrição do evento {event.title} realizada com sucesso."
            )
            return redirect(request.session.get("unsubscribe_back_url", "home"))
        except Exception as e:
            messages.error(request, f"Erro ao cancelar inscrição")
            return redirect(request.session.get("unsubscribe_back_url", "home"))

    return render(request, "cancel_subscription.html", {"subscription": subscription})


@login_required
def subscriptions_list(request):
    # Obtém os filtros enviados pelo formulário
    search = request.GET.get("search", "").strip()
    status = request.GET.get("status", "").strip()

    # Busca as inscrições do usuário
    subscriptions = EventSubscription.objects.filter(user=request.user).order_by(
        "-created_at"
    )

    # Pesquisa pelo título do evento
    if search:
        subscriptions = subscriptions.filter(event__title__icontains=search)

    # Filtro por status
    if status == "INSCRITO":
        subscriptions = subscriptions.filter(status="INSCRITO")

    elif status == "FINALIZADO":
        subscriptions = subscriptions.filter(status="FINALIZADO")

    elif status == "EXPIRADO":
        subscriptions = subscriptions.filter(status="EXPIRADO")

    elif status == "CANCELADO":
        subscriptions = subscriptions.filter(status="CANCELADO")

    # Descobre a próxima etapa de cada inscrição
    for subscription in subscriptions:

        requirement = (
            subscription.requirements.filter(is_completed=False)
            .order_by("event_stage__start_date")
            .first()
        )

        if requirement:
            subscription.next_stage = requirement.event_stage.stage_type.name
        else:
            subscription.next_stage = "Nenhuma"

    # Paginação
    paginator = Paginator(subscriptions, 10)

    page = request.GET.get("page")

    subscriptions = paginator.get_page(page)

    return render(
        request,
        "subscriptions_list.html",
        {
            "subscriptions": subscriptions,
        },
    )


@login_required
def subscription_detail(request, subscription_id):
    subscription = get_object_or_404(
        EventSubscription.objects.select_related(
            "event__address__city__state",
            "event__language",
            "event__group",
            "user",
        ),
        id=subscription_id,
        user=request.user,
    )

    now = timezone.now()

    # DATAS DO EVENTO
    event_dates = EventStage.objects.filter(event=subscription.event).aggregate(
        start_date=Min("start_date"),
        end_date=Max("end_date"),
    )
    subscription.event.min_start_date = event_dates["start_date"]
    subscription.event.max_end_date = event_dates["end_date"]

    # REQUISITOS COM LÓGICA DE ESTADO
    confirmations = (
        UserStageRequirement.objects.filter(subscription=subscription)
        .select_related("event_stage__stage_type")
        .order_by("event_stage__start_date")
    )

    for requirement in confirmations:
        stage = requirement.event_stage

        requirement.can_confirm = (
            not requirement.is_completed and stage.start_date <= now <= stage.end_date
        )
        requirement.expired = not requirement.is_completed and stage.end_date < now
        requirement.waiting = now < stage.start_date

    # BARRA DE PROGRESSO
    total = confirmations.count()
    completed = confirmations.filter(is_completed=True).count()
    progress = int(completed * 100 / total) if total else 0

    # PRÓXIMA ETAPA
    next_stage = (
        UserStageRequirement.objects.filter(
            subscription=subscription,
            is_completed=False,
            event_stage__end_date__gte=now,
        )
        .select_related("event_stage__stage_type")
        .order_by("event_stage__start_date")
        .first()
    )

    # NOTIFICAÇÕES
    notifications = Notification.objects.filter(user=request.user).order_by(
        "-created_at"
    )[:10]

    return render(
        request,
        "subscription_detail.html",
        {
            "subscription": subscription,
            "confirmations": confirmations,
            "notifications": notifications,
            "progress": progress,
            "completed": completed,
            "total": total,
            "next_stage": next_stage,
        },
    )


@login_required
def confirm_stage(request, requirement_id):
    requirement = get_object_or_404(
        UserStageRequirement,
        id=requirement_id,
        subscription__user=request.user,
    )

    # PROTEÇÃO — inscrição cancelada ou expirada não pode confirmar etapas
    if requirement.subscription.status in ["CANCELADO", "EXPIRADO"]:
        messages.error(request, "Sua inscrição não está ativa.")
        return redirect("subscription_detail", requirement.subscription.id)

    now = timezone.now()

    if not (
        requirement.event_stage.start_date <= now <= requirement.event_stage.end_date
    ):
        messages.error(request, "Esta etapa não pode ser confirmada no momento.")
        return redirect("subscription_detail", requirement.subscription.id)

    if requirement.is_completed:
        messages.warning(request, "Esta etapa já foi confirmada.")
        return redirect("subscription_detail", requirement.subscription.id)

    requirement.is_completed = True
    requirement.save()

    # VERIFICA SE TODAS AS ETAPAS FORAM CONCLUÍDAS
    if not requirement.subscription.requirements.filter(is_completed=False).exists():
        requirement.subscription.status = "FINALIZADO"
        requirement.subscription.save()
        messages.success(request, "Parabéns! Você concluiu todas as etapas do evento.")
    else:
        messages.success(request, "Etapa confirmada com sucesso.")

    return redirect("subscription_detail", requirement.subscription.id)


@login_required
def management_groups(request):
    user_groups = ManagementGroup.objects.filter(members=request.user).distinct()

    for group in user_groups:
        group.num_events = Event.objects.filter(group=group).count()

    context = {"management_groups": user_groups}
    return render(request, "management_groups.html", context=context)


@login_required
def register_management_group(request):

    if request.method == "POST":

        try:

            with transaction.atomic():

                # Cria o grupo
                group = ManagementGroup.objects.create(
                    name=request.POST.get("name"),
                    description=request.POST.get("description"),
                )

                # Adiciona o criador como proprietário
                ManagementGroupMember.objects.create(
                    group=group,
                    user=request.user,
                    role=ManagementGroupMember.Role.OWNER,
                )

            messages.success(request, "Grupo criado com sucesso.")

            return redirect("management_groups")

        except Exception:

            messages.error(request, "Ocorreu um erro ao criar o grupo.")

    return render(request, "register_group.html")


@login_required
def management_group_events(request, group_id):

    # Busca o grupo apenas se o usuário for membro
    management_group = get_object_or_404(
        ManagementGroup.objects.filter(members=request.user),
        id=group_id,
    )

    # Busca os eventos do grupo
    events = Event.objects.filter(group=management_group).order_by("-created_at")

    # Adiciona informações extras para o template
    for event in events:

        # Descobre o período do evento
        period = EventStage.objects.filter(event=event).aggregate(
            start_date=Min("start_date"),
            end_date=Max("end_date"),
        )

        event.start_date = period["start_date"]
        event.end_date = period["end_date"]

        # Conta apenas os inscritos ativos
        event.active_subscriptions = event.subscriptions.filter(
            status__in=["INSCRITO", "FINALIZADO"]
        ).count()

    context = {
        "management_group": management_group,
        "events": events,
    }

    return render(
        request,
        "management_group_events.html",
        context,
    )

@login_required
def edit_management_group(request, group_id):
    # Busca o grupo
    management_group = get_object_or_404(
        ManagementGroup,
        id=group_id
    )

    # Verifica se o usuário possui permissão
    member = ManagementGroupMember.objects.filter(
        group=management_group,
        user=request.user,
    ).first()

    if not member or member.role not in ["OWNER", "ADMIN", "MANAGER"]:
        messages.error(
            request,
            "Você não possui permissão para editar este grupo."
        )
        return redirect("management_groups")

    if request.method == "POST":
        name = request.POST.get("name", "").strip()
        description = request.POST.get("description", "").strip()

        if not name:
            messages.error(
                request,
                "Informe o nome do grupo."
            )
            return render(
                request,
                "edit_management_group.html",
                {"management_group": management_group},
            )

        try:
            management_group.name = name
            management_group.description = description
            management_group.save()

            messages.success(
                request,
                "Grupo atualizado com sucesso."
            )

            return redirect(
                "management_group_events",
                management_group.id,
            )

        except Exception:
            messages.error(
                request,
                "Erro ao atualizar o grupo."
            )

    return render(
        request,
        "edit_management_group.html",
        {
            "management_group": management_group,
        },
    )


# ------------------------ REGISTER VIEWS DE CAMPOS ADICIONAIS DO REGISTER EVENT ------------------------
@login_required
def register_language(request):
    if request.method == "POST":
        try:
            # Salvando linguagem do formulário no model Language
            language = request.POST.get("language")
            if language:
                Language.objects.create(language=language)
                # Atualiza buffer de messages
                messages.success(request, "Idioma adicionado.")
            else:
                messages.error(request, "Por favor, digite algo neste campo.")
        except DatabaseError:
            # Captura o erro do banco de dados e avisa o usuário sem derrubar o sistema
            messages.error(request, f"Erro ao salvar o idioma")
        except Exception:
            # Captura qualquer outro erro inesperado
            messages.error(request, f"Ocorreu um erro inesperado")

    return render(request, "register_language.html")


@login_required
def register_stage_type(request):
    if request.method == "POST":
        try:
            event_stage_type = request.POST.get("event_stage_type_name")
            if event_stage_type:
                EventStagesType.objects.create(name=event_stage_type)
                # Atualiza buffer de messages
                messages.success(request, "Tipo de etapa adicionado.")
            else:
                messages.error(request, "Por favor, digite algo neste campo.")
        except DatabaseError:
            # Captura o erro do banco de dados e avisa o usuário sem derrubar o sistema
            messages.error(request, f"Erro ao salvar o tipo de etapa")
        except Exception:
            # Captura qualquer outro erro inesperado
            messages.error(request, f"Ocorreu um erro inesperado")
    return render(request, "register_event_stage_type.html")
