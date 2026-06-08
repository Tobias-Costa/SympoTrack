from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import DatabaseError
from .models import Language, State, City, EventAddress

# Create your views here.

@login_required
def home(request):
    return render(request, "home.html")


@login_required
def register_event(request):
     # Retorna todas as linguagens cadastradas no DB
    languages = Language.objects.all().order_by("language")
    address = EventAddress.objects.all().order_by("place_name")

    return render(request, "register_event.html", {"languages":languages, "address_options":address})

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
def register_address(request):
    if request.method == "POST":
        try:
            place_name=request.POST.get('place_name')
            cep=request.POST.get('cep')
            street=request.POST.get('street')
            number=request.POST.get('number')
            complement=request.POST.get('complement')
            neighborhood=request.POST.get('neighborhood')
            city = get_object_or_404(City, id=request.POST.get('city'))

            # Salvando endereço do formulário no model EventAddress
            event_addr = EventAddress(place_name=place_name, street=street, number=number, complement=complement, neighborhood=neighborhood, cep=cep, city=city)
            event_addr.save()
            # Atualiza buffer de messages
            messages.success(request, "Endereço adicionado.")
        except DatabaseError as e:
            # Captura o erro do banco de dados e avisa o usuário sem derrubar o sistema
            messages.error(request, f"Erro ao salvar o endereço")
        except Exception as e:
            # Captura qualquer outro erro inesperado
            messages.error(request, f"Ocorreu um erro inesperado")

    cities = City.objects.all().order_by("name")
    return render(request, "register_address.html", {"cities":cities})


@login_required
def register_city(request):
    if request.method == "POST":
        try:
            # Salvando cidade do formulário no model City
            state_id = get_object_or_404(State, id=request.POST.get('state'))
            city = City(name=request.POST.get('name'), state=state_id)
            city.save()
            # Atualiza buffer de messages
            messages.success(request, "Cidade adicionada.")
        except DatabaseError as e:
            # Captura o erro do banco de dados e avisa o usuário sem derrubar o sistema
            messages.error(request, f"Erro ao salvar a cidade")
        except Exception as e:
            # Captura qualquer outro erro inesperado
            messages.error(request, f"Ocorreu um erro inesperado")

    states = State.objects.all().order_by('name')
    return render(request, "register_city.html", {'states':states})
    