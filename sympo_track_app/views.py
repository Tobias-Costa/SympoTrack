from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required

# Create your views here.

@login_required
def home(request):
    return render(request, "home.html")


@login_required
def register_event(request):
    return render(request, "register_event.html")
