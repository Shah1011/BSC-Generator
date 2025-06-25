from django.http import HttpResponse
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User, Group
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .models import Organization, UserProfile

def register(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')
        password2 = request.POST.get('password2')
        role = request.POST.get('role')
        org_name = request.POST.get('organization')
        if password != password2:
            messages.error(request, 'Passwords do not match')
            return render(request, 'register.html')
        if User.objects.filter(username=username).exists():
            messages.error(request, 'Username already exists')
            return render(request, 'register.html')
        if User.objects.filter(email=email).exists():
            messages.error(request, 'Email already exists')
            return render(request, 'register.html')
        user = User.objects.create_user(username=username, email=email, password=password)
        user.save()
        # Get or create organization
        organization, created = Organization.objects.get_or_create(name=org_name)
        # Create user profile
        UserProfile.objects.create(user=user, organization=organization, role=role)
        messages.success(request, 'Account created successfully! Please log in.')
        return redirect('login')
    return render(request, 'register.html')


def login_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect('dashboard')
        else:
            messages.error(request, 'Invalid username or password')
            return render(request, 'login.html')
    return render(request, 'login.html')


def logout_view(request):
    logout(request)
    return redirect('login')


@login_required(login_url='login')
def hello_world(request):
    return render(request, 'hello_world.html', {'user': request.user})


@login_required(login_url='login')
def dashboard(request):
    user = request.user
    try:
        profile = user.userprofile
        is_admin = profile.role == 'admin'
        is_employee = profile.role == 'employee'
        organization = profile.organization
    except UserProfile.DoesNotExist:
        is_admin = False
        is_employee = False
        organization = None
    return render(request, 'dashboard.html', {
        'user': user,
        'is_admin': is_admin,
        'is_employee': is_employee,
        'organization': organization,
    })