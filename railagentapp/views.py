from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from .models import PassengerProfile

@login_required(login_url='/login/')
def index(request):
    passengers = PassengerProfile.objects.filter(user=request.user)
    return render(request, 'homepage.html', {'passengers': passengers})

def register_view(request):
    if request.method=='POST':
        username=request.POST.get('username')
        email = request.POST.get('email')
        password=request.POST.get('password')
        fullname=request.POST.get('full_name')
        age=request.POST.get('age')
        gender=request.POST.get('gender')
        berth=request.POST.get('berth')

        if User.objects.filter(email=email).exists():
            return render(request, 'register.html', {'error': 'Email is already registered!'})

        # Create the core Django User
        if not User.objects.filter(username=username).exists():
            user = User.objects.create_user(username=username, email=email, password=password)
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

@login_required(login_url='/login/')
def profile_view(request):
    context = {}
    if request.method == 'POST':
        action = request.POST.get('action') # 🟢 Check which form was submitted

        if action == 'update_email':
            new_email = request.POST.get('new_email')
            # Ensure no one else is using this email
            if User.objects.filter(email=new_email).exclude(id=request.user.id).exists():
                context['error_message'] = "This email is already in use by another account."
            else:
                request.user.email = new_email
                request.user.save()
                context['success_message'] = "Alert Email updated successfully!"

        elif action == 'add_passenger':
            PassengerProfile.objects.create(
                user=request.user,
                full_name=request.POST.get('full_name'),
                age=request.POST.get('age'),
                gender=request.POST.get('gender'),
                berth_preference=request.POST.get('berth')
            )
            return redirect('profile')

    # Fetch ALL passengers belonging to this user
    context['passengers'] = PassengerProfile.objects.filter(user=request.user)
    return render(request, 'profile.html', context)

@login_required(login_url='/login/')
def delete_passenger(request, passenger_id):
    # Securely delete a passenger (ensuring it belongs to the logged-in user)
    passenger = get_object_or_404(PassengerProfile, id=passenger_id, user=request.user)
    passenger.delete()
    return redirect('profile')