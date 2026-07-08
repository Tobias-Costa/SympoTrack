from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import DatabaseError, transaction
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
    )
from django.conf import settings

@login_required
def home(request):
    return render(request, "home.html")


@login_required
def register_event(request):
    # Busca todos os dados necessários para a rota GET funcionar
    languages = Language.objects.all().order_by("language")
    categories = EventCategories.objects.all().order_by("name")
    event_stage_types = EventStagesType.objects.all().order_by("name")
    areas = EventCategoriesArea.objects.prefetch_related("categories").order_by("college", "name")
    context = {
                "languages": languages,
                "category_options": categories,
                "geoapify_key": settings.GEOAPIFY_API_KEY,
                "areas": areas,
                "college_choices": EventCategoriesArea.College.choices,
                "event_stage_type_options": event_stage_types,
            }

    if request.method == "POST":
        # SALVANDO ENDEREÇOS
        country_name = request.POST.get("country_name")
        country_abbr = request.POST.get("country_abbr")

        state_name = request.POST.get("state_name")
        state_uf = request.POST.get("state_uf")

        city_name = request.POST.get("city_name")

        if not city_name:
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
                    place_name=request.POST.get("place_name"),
                    street=request.POST.get("street"),
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

                # EVENTO
                # Adicionar booleano em que se seleciona se o evento deve ser anexado a um grupo ou indivíduo
                event = Event.objects.create(
                    title=request.POST.get("title"),
                    description=request.POST.get("description"),
                    subject=request.POST.get("subject"),
                    external_link=request.POST.get("external_link"),
                    is_public=bool(request.POST.get("is_public")),
                    address=address,
                    language=language,
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
        except Exception as e:
            import traceback
            print(traceback.format_exc()) 
            messages.error(request, f"Erro ao salvar evento: {e}")

    return render(request, "register_event.html", context)


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

# @login_required
# def register_category(request):
#     if request.method == "POST":
#         try:
#             # Salvando categoria no model EventCategories
#             category = EventCategories(name=request.POST.get("name"))
#             category.save()
#             # Atualiza buffer de messages
#             messages.success(request, "Categoria adicionada.")
#         except DatabaseError as e:
#             # Captura o erro do banco de dados e avisa o usuário sem derrubar o sistema
#             messages.error(request, f"Erro ao salvar a categoria")
#         except Exception as e:
#             # Captura qualquer outro erro inesperado
#             messages.error(request, f"Ocorreu um erro inesperado")

#     return render(request, "register_category.html")
