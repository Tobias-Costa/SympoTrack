from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import DatabaseError
from .models import Language

# Create your views here.

@login_required
def home(request):
    return render(request, "home.html")


@login_required
def register_event(request):
     # Retorna todas as linguagens cadastradas no DB
    languages = Language.objects.all().order_by("language")

    return render(request, "register_event.html", {"languages":languages,})

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
            messages.error(request, f"Erro ao salvar o idioma: {e}")
        except Exception as e:
            # Captura qualquer outro erro inesperado
            messages.error(request, f"Ocorreu um erro inesperado: {e}")
    
    return render(request, "register_language.html")
    