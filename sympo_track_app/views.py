from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import DatabaseError
from .models import (
    Language,
    State,
    City,
    EventAddress,
    EventCategories,
    EventCategoryRel,
    Country,
    Event,
    EventCategoriesArea,
)
from django.conf import settings

# Create your views here.


@login_required
def home(request):
    return render(request, "home.html")


@login_required
def register_event(request):
    # Busca todos os dados necessários para a rota GET funcionar
    languages = Language.objects.all().order_by("language")
    categories = EventCategories.objects.all().order_by("name")
    areas = EventCategoriesArea.objects.prefetch_related("categories").order_by(
        "college", "name"
    )

    if request.method == "POST":
        # SALVANDO ENDEREÇOS
        country_name = request.POST.get("country_name")
        country_abbr = request.POST.get("country_abbr")

        state_name = request.POST.get("state_name")
        state_uf = request.POST.get("state_uf")

        city_name = request.POST.get("city_name")

        if not (country_name and state_name and city_name):
            messages.error(request, "Selecione um endereço válido no mapa.")
            return redirect("register_event")

        try:
            # PAÍS
            country, _ = Country.objects.get_or_create(
                name=country_name,
                defaults={"abbr": country_abbr.upper() or country_name[:10]},
            )

            # ESTADO
            state, _ = State.objects.get_or_create(
                name=state_name,
                country=country,
                defaults={"uf": state_uf.upper() or state_name[:10]},
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
                return redirect("register_event")
            # Seção de mensagens de sucesso e falha
            messages.success(request, "Evento cadastrado com sucesso.")

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

        except Exception as e:
            messages.error(request, f"Erro ao salvar evento")

    return render(
        request,
        "register_event.html",
        {
            "languages": languages,
            "category_options": categories,
            "geoapify_key": settings.GEOAPIFY_API_KEY,
            "areas": areas,
            "college_choices": EventCategoriesArea.College.choices,
        },
    )


# ------------------------ REGISTER VIEWS DE CAMPOS ADICIONAIS DO REGISTER EVENT ------------------------
@login_required
def register_language(request):
    if request.method == "POST":
        try:
            # Salvando linguagem do formulário no model Language
            language = Language(language=request.POST.get("language"))
            language.save()
            # Atualiza buffer de messages
            messages.success(request, "Idioma adicionado.")
        except DatabaseError as e:
            # Captura o erro do banco de dados e avisa o usuário sem derrubar o sistema
            messages.error(request, f"Erro ao salvar o idioma")
        except Exception as e:
            # Captura qualquer outro erro inesperado
            messages.error(request, f"Ocorreu um erro inesperado")

    return render(request, "register_language.html")


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
