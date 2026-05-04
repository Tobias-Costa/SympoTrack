from django.shortcuts import render, redirect

# Create your views here.
def index(request):
    return redirect("login")

def login(request):
    return render(request, "login.html")