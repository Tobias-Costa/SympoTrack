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
    ManagementGroup,
    ManagementGroupMember,
    )
from django.conf import settings
import json

@login_required
def home(request):
    events = Event.objects.filter(is_public=True).all()
    return render(request, "home.html", {"events":events})


@login_required
def register_event(request):
    # Busca todos os dados necessários para a rota GET funcionar
    languages = Language.objects.all().order_by("language")
    categories = EventCategories.objects.all().order_by("name")
    event_stage_types = EventStagesType.objects.all().order_by("name")
    areas = EventCategoriesArea.objects.prefetch_related("categories").order_by("college", "name")
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
        context.update({
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
            "place_name":   request.POST.get("place_name", ""),
            "street":       request.POST.get("street", ""),
            "number":       request.POST.get("number", ""),
            "neighborhood": request.POST.get("neighborhood", ""),
            "cep":          request.POST.get("cep", ""),
            "city_name":    request.POST.get("city_name", ""),
            "state_name":   request.POST.get("state_name", ""),
            "state_uf":     request.POST.get("state_uf", ""),
            "country_name": request.POST.get("country_name", ""),
            "country_abbr": request.POST.get("country_abbr", ""),

            # CATEGORIAS
            "selected_categories": json.dumps(request.POST.getlist("categories")),

            # ETAPAS
            "stages_data": json.dumps([
                list(item) for item in zip(
                    request.POST.getlist("stage_type[]"),
                    request.POST.getlist("stage_start_date[]"),
                    request.POST.getlist("stage_end_date[]"),
                )
            ]),

            # PREÇOS
            "prices_data": json.dumps([
                list(item) for item in zip(
                    request.POST.getlist("price_category[]"),
                    request.POST.getlist("batch[]"),
                    request.POST.getlist("price[]"),
                )
            ]),
                    
        })

        # SALVANDO ENDEREÇOS
        country_name = request.POST.get("country_name")
        country_abbr = request.POST.get("country_abbr")

        state_name = request.POST.get("state_name")
        state_uf = request.POST.get("state_uf")

        city_name = request.POST.get("city_name")

        place_name = request.POST.get("place_name")

        street_name = request.POST.get("street")

        if not ( place_name and street_name and city_name ):
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
                end_dates   = request.POST.getlist("stage_end_date[]")

                for stage_type_id, start_date, end_date in zip(stage_types, start_dates, end_dates):
                    if not (stage_type_id and start_date and end_date):
                        continue

                    stage_type = EventStagesType.objects.filter(id=stage_type_id).first()
                    if not stage_type:
                        continue

                    EventStage.objects.create(
                        event = event,
                        stage_type = stage_type,
                        start_date = start_date,
                        end_date = end_date,
                    )

                # PREÇOS
                price_categories = request.POST.getlist("price_category[]")
                batches = request.POST.getlist("batch[]")
                prices = request.POST.getlist("price[]")

                for category, batch, price in zip(price_categories, batches, prices):
                    if not (category and price):
                        continue

                    EventPricing.objects.create(
                        event = event,
                        category = category,
                        batch = batch or "Lote 1",
                        price = price,
                    )

            # Seção de mensagens de sucesso e falha
            messages.success(request, "Evento cadastrado com sucesso.")
            return redirect("register_event")
        except Exception:
            messages.error(request, f"Erro ao salvar evento")

    return render(request, "register_event.html", context)


@login_required
def management_groups(request):
    user_groups = ManagementGroup.objects.filter(members=request.user)
    context = {"management_groups": user_groups}
    return render(request, "management_groups.html", context=context)

@login_required
def event_detail(request, event_id):
    event = get_object_or_404(
        Event.objects.select_related(
            "address__city__state__country",
            "language",
            "creator",
            "group",
        ).prefetch_related(
            "categories__area",
            "stages__stage_type",
            "prices",
            "subscriptions",
        ).annotate(
        min_start_date=Min("stages__start_date"),
        max_end_date=Max("stages__end_date")
    ),
        id=event_id
    )

    # PROTEÇÃO — evento privado só pode ser visto por:
    # 1. O criador
    # 2. Membros do grupo organizador
    # 3. Inscritos no evento
    if not event.is_public:
        is_creator = (event.creator == request.user)

        is_group_member = event.group and ManagementGroupMember.objects.filter(
            group=event.group,
            user=request.user,
        ).exists()

        is_subscribed = event.subscriptions.filter(
            user=request.user
        ).exists()

        if not (is_creator or is_group_member or is_subscribed):
            messages.error(request, "Este evento é privado.")
            return redirect("home")

    # SALVA URL DE ORIGEM
    # Se existir '?next=' na URL (ou seja, veio da Home ou Grupos), salva na sessão
    if 'next' in request.GET:
        request.session['event_back_url'] = request.GET['next']

    # VERIFICA SE O USUÁRIO PODE EDITAR
    can_edit = False
    if event.creator == request.user:
        can_edit = True
    elif event.group:
        can_edit = ManagementGroupMember.objects.filter(
            group=event.group,
            user=request.user,
            role__in=["OWNER", "ADMIN", "MANAGER", "EDITOR"]
        ).exists()

    return render(request, "event_detail.html", {
        "event": event,
        "can_edit": can_edit,
    })

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
