from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import DatabaseError
from .models import Language, State, City, EventAddress, EventCategories, Country
from django.conf import settings

# Create your views here.

@login_required
def home(request):
    return render(request, "home.html")


@login_required
def register_event(request):
    if request.method == "POST":
        # SALVANDO ENDEREÇOS
        country_name = request.POST.get("country_name")
        country_abbr = request.POST.get("country_abbr")

        state_name = request.POST.get("state_name")
        state_uf = request.POST.get("state_uf")

        city_name = request.POST.get("city_name")

        if not (country_name and state_name and city_name):
            messages.error(
                request,
                "Selecione um endereço válido no mapa."
            )
            return redirect("register_event")

        try:

            country, _ = Country.objects.get_or_create(
                name=country_name,
                defaults={
                    "abbr": country_abbr.upper() or country_name[:10]
                }
            )

            state, _ = State.objects.get_or_create(
                name=state_name,
                country=country,
                defaults={
                    "uf": state_uf.upper() or state_name[:10]
                }
            )

            city, _ = City.objects.get_or_create(
                name=city_name,
                state=state
            )

            EventAddress.objects.create(
                place_name=request.POST.get("place_name"),
                street=request.POST.get("street"),
                number=request.POST.get("number") or None,
                complement=request.POST.get("complement") or None,
                neighborhood=request.POST.get("neighborhood") or None,
                cep=request.POST.get("cep") or None,
                city=city
            )

            # Seção de mensagens de sucesso e falha
            messages.success(
                request,
                "Evento cadastrado com sucesso."
            )

            # return redirect("register_event")

        except Exception as e:

            messages.error(
                request,
                f"Erro ao salvar evento"
            )

            # return redirect("register_event")

     # Retorna todas as linguagens cadastradas no DB
    languages = Language.objects.all().order_by("language")
    categories = EventCategories.objects.all().order_by("name")

    return render(request, "register_event.html", {"languages":languages, "category_options":categories, "geoapify_key":settings.GEOAPIFY_API_KEY})


# ------------------------ REGISTER VIEWS DE CAMPOS ADICIONAIS DO REGISTER EVENT ------------------------
@login_required
def register_language(request):
    if request.method == "POST":
        try:
            # Salvando linguagem do formulário no model Language
            language = Language(language=request.POST.get('language'))
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

@login_required
def register_category(request):
    if request.method == "POST":
        try:
            # Salvando categoria no model EventCategories
            category = EventCategories(name=request.POST.get('name'))
            category.save()
            # Atualiza buffer de messages
            messages.success(request, "Categoria adicionada.")
        except DatabaseError as e:
            # Captura o erro do banco de dados e avisa o usuário sem derrubar o sistema
            messages.error(request, f"Erro ao salvar a categoria")
        except Exception as e:
            # Captura qualquer outro erro inesperado
            messages.error(request, f"Ocorreu um erro inesperado")

    return render(request, "register_category.html")
    