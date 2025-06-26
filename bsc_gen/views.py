from django.http import HttpResponse, JsonResponse
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User, Group
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from .models import Organization, UserProfile, BSCEntry
import pandas as pd
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile

def register(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')
        password2 = request.POST.get('password2')
        role = request.POST.get('role')
        org_name = request.POST.get('organization')

        # Error checks
        if password != password2:
            messages.error(request, 'Passwords do not match')
        elif User.objects.filter(username=username).exists():
            messages.error(request, 'Username already exists')
        elif User.objects.filter(email=email).exists():
            messages.error(request, 'Email already exists')
        else:
            user = User.objects.create_user(username=username, email=email, password=password)
            organization, _ = Organization.objects.get_or_create(name=org_name)
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

    bsc_entries = []
    if organization:
        bsc_entries = BSCEntry.objects.filter(owner__isnull=False, owner__exact='') | BSCEntry.objects.filter(owner__isnull=True)
        bsc_entries = BSCEntry.objects.all() if is_admin else BSCEntry.objects.filter(owner__isnull=False, owner__exact='')
        bsc_entries = BSCEntry.objects.filter(owner__isnull=True) | BSCEntry.objects.filter(owner__isnull=False)
        bsc_entries = BSCEntry.objects.all()
        # If you want to filter by organization, add a ForeignKey to Organization in BSCEntry and filter here

    if is_admin and request.method == 'POST' and 'data_file' in request.FILES:
        data_file = request.FILES['data_file']
        file_name = data_file.name
        if not (file_name.endswith('.csv') or file_name.endswith('.xlsx') or file_name.endswith('.xls')):
            messages.error(request, 'Invalid file type. Please upload a CSV or Excel file.')
        else:
            try:
                if file_name.endswith('.csv'):
                    df = pd.read_csv(data_file)
                else:
                    df = pd.read_excel(data_file)
                required_columns = {'perspective', 'objective', 'measure', 'target', 'actual'}
                df.columns = [col.lower() for col in df.columns]
                if not required_columns.issubset(df.columns):
                    messages.error(request, f"Missing required columns. Required: {', '.join(required_columns)}")
                else:
                    for _, row in df.iterrows():
                        BSCEntry.objects.create(
                            perspective=row.get('perspective', ''),
                            objective=row.get('objective', ''),
                            measure=row.get('measure', ''),
                            target=row.get('target', ''),
                            actual=row.get('actual', ''),
                            owner=row.get('owner', ''),
                            date=row.get('date', None)
                        )
                    messages.success(request, f'BSC data uploaded and processed successfully! {df.shape[0]} entries added.')
            except Exception as e:
                messages.error(request, f'Error processing file: {str(e)}')

    return render(request, 'dashboard.html', {
        'user': user,
        'is_admin': is_admin,
        'is_employee': is_employee,
        'organization': organization,
        'bsc_entries': bsc_entries,
    })

@login_required
def bsc_data_api(request):
    user = request.user
    try:
        organization = user.userprofile.organization
    except UserProfile.DoesNotExist:
        return JsonResponse({'error': 'No organization'}, status=400)
    entries = BSCEntry.objects.all()  # Optionally filter by organization if you add a ForeignKey
    data = [
        {
            'perspective': e.perspective,
            'objective': e.objective,
            'measure': e.measure,
            'target': e.target,
            'actual': e.actual,
            'owner': e.owner,
            'date': e.date.strftime('%Y-%m-%d') if e.date else ''
        }
        for e in entries
    ]
    return JsonResponse({'entries': data})

@login_required
def bsc_detailed_view(request):
    bsc_entries = BSCEntry.objects.all()
    return render(request, 'bsc_detailed.html', {'bsc_entries': bsc_entries})