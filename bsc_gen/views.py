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
from django.views.decorators.http import require_POST
from collections import defaultdict

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
        bsc_entries = BSCEntry.objects.all()
        # If you want to filter by organization, add a ForeignKey to Organization in BSCEntry and filter here

    batch_map = defaultdict(list)
    batch_times = {}
    for entry in bsc_entries:
        if not entry.batch_id:
            continue  # skip entries without a batch_id
        batch_map[entry.batch_id].append(entry)
        if entry.batch_id not in batch_times or (entry.upload_time and entry.upload_time < batch_times[entry.batch_id]):
            batch_times[entry.batch_id] = entry.upload_time

    bsc_batches = []
    for batch_id in sorted(batch_map.keys()):
        entries = []
        for entry in batch_map[batch_id]:
            try:
                actual = float(entry.actual)
                target = float(entry.target)
            except (ValueError, TypeError):
                actual = 0.0
                target = 0.0
            if actual >= target:
                status = 'good'
            elif actual >= 0.8 * target:
                status = 'moderate'
            else:
                status = 'bad'
            entries.append({
                'perspective': entry.perspective,
                'objective': entry.objective,
                'measure': entry.measure,
                'target': entry.target,
                'actual': entry.actual,
                'owner': entry.owner,
                'date': entry.date,
                'status': status,
            })
        bsc_batches.append({
            'batch_id': batch_id,
            'upload_time': batch_times[batch_id],
            'entries': entries
        })

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
                    # Generate new batch_id
                    last_batch = BSCEntry.objects.order_by('-batch_id').first()
                    if last_batch and last_batch.batch_id and last_batch.batch_id.isdigit():
                        new_batch_id = str(int(last_batch.batch_id) + 1).zfill(3)
                    else:
                        new_batch_id = '001'
                    for _, row in df.iterrows():
                        BSCEntry.objects.create(
                            perspective=row.get('perspective', ''),
                            objective=row.get('objective', ''),
                            measure=row.get('measure', ''),
                            target=row.get('target', ''),
                            actual=row.get('actual', ''),
                            owner=row.get('owner', ''),
                            date=row.get('date', None),
                            batch_id=new_batch_id
                        )
                    messages.success(request, f'BSC data uploaded and processed successfully! {df.shape[0]} entries added in batch {new_batch_id}.')
                    return redirect('dashboard')
            except Exception as e:
                messages.error(request, f'Error processing file: {str(e)}')

    return render(request, 'dashboard.html', {
        'user': user,
        'is_admin': is_admin,
        'is_employee': is_employee,
        'organization': organization,
        'bsc_batches': bsc_batches,
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

@login_required
@require_POST
def delete_bsc_data(request):
    user = request.user
    try:
        profile = user.userprofile
        is_admin = profile.role == 'admin'
    except UserProfile.DoesNotExist:
        is_admin = False
    if is_admin:
        BSCEntry.objects.all().delete()
        messages.success(request, 'All BSC data has been deleted.')
    else:
        messages.error(request, 'You are not authorized to perform this action.')
    return redirect('dashboard')