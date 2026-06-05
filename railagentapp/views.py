from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from .models import PassengerProfile

@login_required(login_url='/login/')
def index(request):
    return render(request, 'homepage.html')

def register_view(request):
    if request.method=='POST':
        username=request.POST.get('username')
        password=request.POST.get('password')
        fullname=request.POST.get('full_name')
        age=request.POST.get('age')
        gender=request.POST.get('gender')
        berth=request.POST.get('berth')

        # Create the core Django User
        if not User.objects.filter(username=username).exists():
            user=User.objects.create_user(username=username, password=password)
            PassengerProfile.objects.create(
                user=user,
                full_name=fullname,
                age=age,
                gender=gender,
                berth_preference=berth
            )

            login(request, user)
            return redirect('index')
        else:
            return render(request, 'register.html', {'error': 'Username already exists!'})

    return render(request, 'register.html')


def login_view(request):
    if request.method=='POST':
        username=request.POST.get('username')
        password=request.POST.get('password')
        user=authenticate(request, username=username, password=password)
        
        if user is not None:
            login(request, user)
            return redirect('index')
        else:
            return render(request, 'login.html', {'error': 'Invalid credentials!'})

    return render(request, 'login.html')


def logout_view(request):
    logout(request)
    return redirect('login')