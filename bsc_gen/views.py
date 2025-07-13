from django.http import HttpResponse, JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User, Group
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from .models import Organization, UserProfile, BSCEntry, FinancialBSC, CustomerBSC, InternalBSC, LearningGrowthBSC
import pandas as pd
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from django.views.decorators.http import require_POST, require_GET
from collections import defaultdict
from django.views.decorators.csrf import csrf_exempt
from django.urls import reverse
import datetime
from weasyprint import HTML
from django.template.loader import render_to_string
from django.http import HttpResponse, Http404
import json
import matplotlib.pyplot as plt
import io
import base64

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

def register(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')
        password2 = request.POST.get('password2')
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
            # Only create admin users through registration
            UserProfile.objects.create(user=user, organization=organization, role='admin')
            messages.success(request, 'Admin account created successfully! Please log in.')
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

    # Get data from all BSC perspective tables
    bsc_entries = []
    if organization:
        # Get entries from all perspective tables, filtered by organization
        financial_entries = FinancialBSC.objects.filter(organization=organization)
        customer_entries = CustomerBSC.objects.filter(organization=organization)
        internal_entries = InternalBSC.objects.filter(organization=organization)
        learning_entries = LearningGrowthBSC.objects.filter(organization=organization)
        
        # Combine all entries with their perspective information
        for entry in financial_entries:
            bsc_entries.append({
                'model': 'Financial',
                'entry': entry,
                'perspective': 'Financial'
            })
        for entry in customer_entries:
            bsc_entries.append({
                'model': 'Customer',
                'entry': entry,
                'perspective': 'Customer'
            })
        for entry in internal_entries:
            bsc_entries.append({
                'model': 'Internal',
                'entry': entry,
                'perspective': 'Internal'
            })
        for entry in learning_entries:
            bsc_entries.append({
                'model': 'Learning & Growth',
                'entry': entry,
                'perspective': 'Learning & Growth'
            })

    batch_map = defaultdict(list)
    batch_times = {}
    for bsc_item in bsc_entries:
        entry = bsc_item['entry']
        if not entry.batch_id:
            continue  # skip entries without a batch_id
        batch_map[entry.batch_id].append(bsc_item)
        if entry.batch_id not in batch_times or (entry.upload_time and entry.upload_time < batch_times[entry.batch_id]):
            batch_times[entry.batch_id] = entry.upload_time

    bsc_batches = []
    for batch_id in sorted(batch_map.keys(), reverse=True):
        entries = []
        batch_name = None
        for bsc_item in batch_map[batch_id]:
            entry = bsc_item['entry']
            perspective = bsc_item['perspective']
            
            # Get batch name from the first entry (they should all have the same batch_name)
            if batch_name is None:
                batch_name = entry.batch_name
            
            # Use the built-in status calculation method
            status = entry.get_status()
            
            entries.append({
                'perspective': perspective,
                'objective': entry.objective,
                'measure': entry.measure,
                'target': entry.target,
                'actual': entry.actual,
                'owner': entry.owner,
                'date': entry.date,
                'status': status,
                'model_type': type(entry).__name__,
                'pk': entry.pk,
            })
        bsc_batches.append({
            'batch_id': batch_id,
            'batch_name': batch_name or f'Batch {batch_id}',
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
                    all_entries = list(FinancialBSC.objects.all()) + list(CustomerBSC.objects.all()) + list(InternalBSC.objects.all()) + list(LearningGrowthBSC.objects.all())
                    if all_entries:
                        max_batch = max(all_entries, key=lambda x: int(x.batch_id) if x.batch_id and x.batch_id.isdigit() else 0)
                        if max_batch.batch_id and max_batch.batch_id.isdigit():
                            new_batch_id = str(int(max_batch.batch_id) + 1).zfill(3)
                        else:
                            new_batch_id = '001'
                    else:
                        new_batch_id = '001'
                    
                    for _, row in df.iterrows():
                        perspective = row.get('perspective', '').strip()
                        objective = row.get('objective', '')
                        measure = row.get('measure', '')
                        target = row.get('target', '')
                        actual = row.get('actual', '')
                        owner = row.get('owner', '')
                        date_str = row.get('date', None)
                        date_obj = None
                        if date_str and str(date_str).strip():
                            for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%m/%d/%Y"):
                                try:
                                    date_obj = datetime.datetime.strptime(str(date_str).strip(), fmt).date()
                                    break
                                except Exception:
                                    continue
                        else:
                            date_obj = None
                        
                        # Create entry in the appropriate table based on perspective
                        if perspective.lower() == 'financial':
                            FinancialBSC.objects.create(
                                objective=objective,
                                measure=measure,
                                target=target,
                                actual=actual,
                                owner=owner,
                                date=date_obj,
                                batch_id=new_batch_id,
                                organization=organization
                            )
                        elif perspective.lower() == 'customer':
                            CustomerBSC.objects.create(
                                objective=objective,
                                measure=measure,
                                target=target,
                                actual=actual,
                                owner=owner,
                                date=date_obj,
                                batch_id=new_batch_id,
                                organization=organization
                            )
                        elif perspective.lower() == 'internal':
                            InternalBSC.objects.create(
                                objective=objective,
                                measure=measure,
                                target=target,
                                actual=actual,
                                owner=owner,
                                date=date_obj,
                                batch_id=new_batch_id,
                                organization=organization
                            )
                        elif perspective.lower() == 'learning & growth':
                            LearningGrowthBSC.objects.create(
                                objective=objective,
                                measure=measure,
                                target=target,
                                actual=actual,
                                owner=owner,
                                date=date_obj,
                                batch_id=new_batch_id,
                                organization=organization
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
    
    # Get data from all perspective tables, filtered by organization
    financial_entries = FinancialBSC.objects.filter(organization=organization)
    customer_entries = CustomerBSC.objects.filter(organization=organization)
    internal_entries = InternalBSC.objects.filter(organization=organization)
    learning_entries = LearningGrowthBSC.objects.filter(organization=organization)
    
    data = []
    
    # Add financial entries
    for e in financial_entries:
        data.append({
            'perspective': 'Financial',
            'objective': e.objective,
            'measure': e.measure,
            'target': e.target,
            'actual': e.actual,
            'owner': e.owner,
            'date': e.date.strftime('%Y-%m-%d') if e.date else ''
        })
    
    # Add customer entries
    for e in customer_entries:
        data.append({
            'perspective': 'Customer',
            'objective': e.objective,
            'measure': e.measure,
            'target': e.target,
            'actual': e.actual,
            'owner': e.owner,
            'date': e.date.strftime('%Y-%m-%d') if e.date else ''
        })
    
    # Add internal entries
    for e in internal_entries:
        data.append({
            'perspective': 'Internal',
            'objective': e.objective,
            'measure': e.measure,
            'target': e.target,
            'actual': e.actual,
            'owner': e.owner,
            'date': e.date.strftime('%Y-%m-%d') if e.date else ''
        })
    
    # Add learning & growth entries
    for e in learning_entries:
        data.append({
            'perspective': 'Learning & Growth',
            'objective': e.objective,
            'measure': e.measure,
            'target': e.target,
            'actual': e.actual,
            'owner': e.owner,
            'date': e.date.strftime('%Y-%m-%d') if e.date else ''
        })
    
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
    
    if not is_admin:
        messages.error(request, 'You do not have permission to delete BSC data.')
        return redirect('dashboard')
    
    # Get the password from the form
    password = request.POST.get('admin_password')
    
    if not password:
        messages.error(request, 'Password is required to delete all BSC data.')
        return redirect('dashboard')
    
    # Verify the password
    if not user.check_password(password):
        messages.error(request, 'Password does not match. Please try again.')
        return redirect('dashboard')
    
    # If password is correct, delete all BSC data from all perspective tables
    deleted_financial = FinancialBSC.objects.all().delete()[0]
    deleted_customer = CustomerBSC.objects.all().delete()[0]
    deleted_internal = InternalBSC.objects.all().delete()[0]
    deleted_learning = LearningGrowthBSC.objects.all().delete()[0]
    
    total_deleted = deleted_financial + deleted_customer + deleted_internal + deleted_learning
    messages.success(request, f'All BSC data has been deleted successfully. {total_deleted} entries removed.')
    return redirect('dashboard')

@login_required
@require_POST
def delete_batch(request, batch_id):
    user = request.user
    try:
        profile = user.userprofile
        is_admin = profile.role == 'admin'
    except UserProfile.DoesNotExist:
        is_admin = False
    
    if is_admin:
        # Delete all entries with the specified batch_id from all perspective tables
        deleted_financial = FinancialBSC.objects.filter(batch_id=batch_id).delete()[0]
        deleted_customer = CustomerBSC.objects.filter(batch_id=batch_id).delete()[0]
        deleted_internal = InternalBSC.objects.filter(batch_id=batch_id).delete()[0]
        deleted_learning = LearningGrowthBSC.objects.filter(batch_id=batch_id).delete()[0]
        
        total_deleted = deleted_financial + deleted_customer + deleted_internal + deleted_learning
        
        if total_deleted > 0:
            messages.success(request, f'Batch {batch_id} has been deleted successfully. {total_deleted} entries removed.')
        else:
            messages.error(request, f'Batch {batch_id} not found.')
    else:
        messages.error(request, 'You do not have permission to delete BSC data.')
    
    return redirect('dashboard')

@login_required
@require_POST
@csrf_exempt
def update_batch(request, batch_id):
    user = request.user
    try:
        profile = user.userprofile
        is_admin = profile.role == 'admin'
    except Exception:
        is_admin = False
    if not is_admin:
        messages.error(request, 'You do not have permission to update BSC data.')
        return redirect('dashboard')

    # Collect all entries for this batch from all models
    models = [FinancialBSC, CustomerBSC, InternalBSC, LearningGrowthBSC]
    updated_count = 0
    for model in models:
        entries = model.objects.filter(batch_id=batch_id)
        for entry in entries:
            prefix = f"{model.__name__}_{entry.pk}_"
            # For each editable field, update if present in POST
            for field in ['objective', 'measure', 'target', 'actual', 'owner', 'date']:
                key = f"{prefix}{field}"
                if key in request.POST:
                    value = request.POST[key]
                    if field == 'date' and value == '':
                        value = None
                    setattr(entry, field, value)
            entry.save()
            updated_count += 1
    messages.success(request, f'Batch {batch_id} updated successfully. {updated_count} entries updated.')
    return redirect('dashboard')

@login_required
def profile_view(request):
    user = request.user
    try:
        profile = user.userprofile
        organization = profile.organization
        role = profile.role
    except UserProfile.DoesNotExist:
        organization = None
        role = None

    # Check if there's any BSC data to delete
    has_bsc_data = False
    if organization:
        # Check all BSC perspective tables for data
        financial_count = FinancialBSC.objects.filter(organization=organization).count()
        customer_count = CustomerBSC.objects.filter(organization=organization).count()
        internal_count = InternalBSC.objects.filter(organization=organization).count()
        learning_count = LearningGrowthBSC.objects.filter(organization=organization).count()
        
        has_bsc_data = financial_count > 0 or customer_count > 0 or internal_count > 0 or learning_count > 0

    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'update_profile':
            # Handle profile updates
            first_name = request.POST.get('first_name', '')
            last_name = request.POST.get('last_name', '')
            email = request.POST.get('email', '')
            
            user.first_name = first_name
            user.last_name = last_name
            user.email = email
            user.save()
            
            messages.success(request, 'Profile updated successfully!')
            return redirect('profile')
            
        elif action == 'change_password':
            # Handle password change
            current_password = request.POST.get('current_password')
            new_password = request.POST.get('new_password')
            confirm_password = request.POST.get('confirm_password')
            
            # Validate current password
            if not user.check_password(current_password):
                messages.error(request, 'Current password is incorrect.')
                return render(request, 'profile.html', {
                    'user': user,
                    'organization': organization,
                    'role': role,
                    'has_bsc_data': has_bsc_data,
                    'is_admin': role == 'admin',
                    'is_employee': role == 'employee',
                })
            
            # Validate new password
            if new_password != confirm_password:
                messages.error(request, 'New passwords do not match.')
                return render(request, 'profile.html', {
                    'user': user,
                    'organization': organization,
                    'role': role,
                    'has_bsc_data': has_bsc_data,
                    'is_admin': role == 'admin',
                    'is_employee': role == 'employee',
                })
            
            if len(new_password) < 6:
                messages.error(request, 'Password must be at least 6 characters long.')
                return render(request, 'profile.html', {
                    'user': user,
                    'organization': organization,
                    'role': role,
                    'has_bsc_data': has_bsc_data,
                    'is_admin': role == 'admin',
                    'is_employee': role == 'employee',
                })
            
            # Update password
            user.set_password(new_password)
            user.save()
            
            messages.success(request, 'Password changed successfully! Please log in again.')
            return redirect('login')

    return render(request, 'profile.html', {
        'user': user,
        'organization': organization,
        'role': role,
        'has_bsc_data': has_bsc_data,
        'is_admin': role == 'admin',
        'is_employee': role == 'employee',
    })

@login_required
def add_viewer(request):
    user = request.user
    try:
        profile = user.userprofile
        is_admin = profile.role == 'admin'
        organization = profile.organization
    except UserProfile.DoesNotExist:
        is_admin = False
        organization = None

    # Only admins can add viewers
    if not is_admin:
        messages.error(request, 'You do not have permission to add viewers.')
        return redirect('dashboard')

    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        first_name = request.POST.get('first_name', '')
        last_name = request.POST.get('last_name', '')
        password = request.POST.get('password', '')
        
        # Generate a random password if none provided
        if not password:
            import random
            import string
            password = ''.join(random.choices(string.ascii_letters + string.digits, k=8))
        
        # Error checks
        if User.objects.filter(username=username).exists():
            messages.error(request, 'Username already exists')
        elif User.objects.filter(email=email).exists():
            messages.error(request, 'Email already exists')
        elif password and len(password) < 6:
            messages.error(request, 'Password must be at least 6 characters long')
        else:
            # Create the user
            new_user = User.objects.create_user(
                username=username, 
                email=email, 
                password=password,
                first_name=first_name,
                last_name=last_name
            )
            
            # Create user profile with employee role
            UserProfile.objects.create(
                user=new_user, 
                organization=organization, 
                role='employee'
            )
            
            if not request.POST.get('password'):
                messages.success(request, f'Viewer account created successfully! Username: {username}, Password: {password}')
            else:
                messages.success(request, f'Viewer account created successfully! Username: {username}')
            return redirect('dashboard')

    # Count viewers in the organization and get their details
    viewer_count = 0
    viewers = []
    if organization:
        viewers = UserProfile.objects.filter(organization=organization, role='employee').select_related('user')
        viewer_count = viewers.count()

    return render(request, 'add_viewer.html', {
        'user': user,
        'organization': organization,
        'viewer_count': viewer_count,
        'viewers': viewers,
        'is_admin': profile.role == 'admin' if 'profile' in locals() and profile else False,
        'is_employee': profile.role == 'employee' if 'profile' in locals() and profile else False,
    })

@login_required
@require_POST
def delete_viewer(request, viewer_id):
    user = request.user
    try:
        profile = user.userprofile
        is_admin = profile.role == 'admin'
        organization = profile.organization
    except UserProfile.DoesNotExist:
        is_admin = False
        organization = None

    # Only admins can delete viewers
    if not is_admin:
        messages.error(request, 'You do not have permission to delete viewers.')
        return redirect('add_viewer')

    try:
        # Get the viewer profile to delete
        viewer_profile = UserProfile.objects.get(
            id=viewer_id,
            organization=organization,
            role='employee'
        )
        
        # Prevent admin from deleting themselves
        if viewer_profile.user == user:
            messages.error(request, 'You cannot delete your own account.')
            return redirect('add_viewer')
        
        # Get the username before deleting for the success message
        username = viewer_profile.user.username
        
        # Delete the user (this will also delete the profile due to CASCADE)
        viewer_profile.user.delete()
        
        messages.success(request, f'Viewer "{username}" has been deleted successfully.')
        
    except UserProfile.DoesNotExist:
        messages.error(request, 'Viewer not found or you do not have permission to delete them.')
    except Exception as e:
        messages.error(request, f'Error deleting viewer: {str(e)}')

    return redirect('add_viewer')

@login_required
@require_POST
def rename_batch(request, batch_id):
    """Rename a batch - only admins can do this"""
    user = request.user
    try:
        profile = user.userprofile
        if profile.role != 'admin':
            return JsonResponse({'error': 'Only admins can rename batches'}, status=403)
    except UserProfile.DoesNotExist:
        return JsonResponse({'error': 'User profile not found'}, status=403)
    
    new_name = request.POST.get('batch_name', '').strip()
    if not new_name:
        return JsonResponse({'error': 'Batch name cannot be empty'}, status=400)
    
    # Update all entries with this batch_id across all BSC tables
    organization = profile.organization
    
    # Update FinancialBSC entries
    FinancialBSC.objects.filter(batch_id=batch_id, organization=organization).update(batch_name=new_name)
    
    # Update CustomerBSC entries
    CustomerBSC.objects.filter(batch_id=batch_id, organization=organization).update(batch_name=new_name)
    
    # Update InternalBSC entries
    InternalBSC.objects.filter(batch_id=batch_id, organization=organization).update(batch_name=new_name)
    
    # Update LearningGrowthBSC entries
    LearningGrowthBSC.objects.filter(batch_id=batch_id, organization=organization).update(batch_name=new_name)
    
    return JsonResponse({'success': True, 'new_name': new_name})

@require_GET
@login_required
def batch_details_api(request):
    batch_id = request.GET.get('batch_id')
    if not batch_id:
        return JsonResponse({'error': 'batch_id is required'}, status=400)

    # Aggregate from all new models
    model_map = {
        'Financial': FinancialBSC,
        'Customer': CustomerBSC,
        'Internal': InternalBSC,
        'Learning & Growth': LearningGrowthBSC,
    }
    perspectives = ['Financial', 'Customer', 'Internal', 'Learning & Growth']
    perspective_data = {}

    for perspective in perspectives:
        model = model_map[perspective]
        entries = model.objects.filter(batch_id=batch_id)
        status_counts = {'good': 0, 'moderate': 0, 'bad': 0, 'unknown': 0}
        for entry in entries:
            try:
                actual_val = float(entry.actual)
                target_val = float(entry.target)
                if actual_val >= target_val:
                    status = 'good'
                elif actual_val >= 0.8 * target_val:
                    status = 'moderate'
                else:
                    status = 'bad'
            except (ValueError, TypeError):
                status = 'unknown'
            status_counts[status] += 1
        perspective_data[perspective] = status_counts

    return JsonResponse({
        'perspective_data': perspective_data,
    })

@login_required
def generate_batch_pdf(request, batch_id):
    user = request.user
    try:
        profile = user.userprofile
        organization = profile.organization
    except Exception:
        raise Http404("User profile not found")

    # Gather all entries for this batch and organization
    entries = []
    perspectives = ['Financial', 'Customer', 'Internal', 'Learning & Growth']
    for model, perspective in [
        (FinancialBSC, 'Financial'),
        (CustomerBSC, 'Customer'),
        (InternalBSC, 'Internal'),
        (LearningGrowthBSC, 'Learning & Growth'),
    ]:
        for entry in model.objects.filter(batch_id=batch_id, organization=organization):
            entries.append({
                'perspective': perspective,
                'objective': entry.objective,
                'measure': entry.measure,
                'target': entry.target,
                'actual': entry.actual,
                'owner': entry.owner,
                'date': entry.date,
                'status': entry.get_status(),
            })
    if not entries:
        raise Http404("Batch not found or no entries for this batch.")

    # Group entries by perspective for table and chart
    grouped = {p: [] for p in perspectives}
    for e in entries:
        grouped[e['perspective']].append(e)

    # Prepare pie chart data (status counts per perspective)
    pie_data = {}
    for p in perspectives:
        counts = {'good': 0, 'moderate': 0, 'bad': 0, 'unknown': 0}
        for e in grouped[p]:
            counts[e['status']] = counts.get(e['status'], 0) + 1
        pie_data[p] = counts

    # Generate pie chart images as base64 for each perspective
    pie_chart_images = {}
    for p in perspectives:
        counts = pie_data[p]
        labels = []
        sizes = []
        colors = []
        color_map = {
            'good': '#22c55e',
            'moderate': '#facc15',
            'bad': '#ef4444',
            'unknown': '#a3a3a3',
        }
        for status in ['good', 'moderate', 'bad', 'unknown']:
            if counts[status] > 0:
                labels.append(f"{status.title()} ({counts[status]})")
                sizes.append(counts[status])
                colors.append(color_map[status])
        if sum(sizes) == 0:
            # No data, show empty chart
            labels = ['No Data']
            sizes = [1]
            colors = ['#e5e7eb']
        # High DPI, no outside labels, bold black percentages, white wedge edges
        fig, ax = plt.subplots(figsize=(1.8, 1.8), dpi=200)
        wedges, texts, autotexts = ax.pie(
            sizes,
            labels=None,  # No outside labels
            colors=colors,
            autopct=lambda pct: f'{pct:.0f}%' if pct > 0 else '',
            startangle=90,
            textprops={'fontsize': 11, 'color': 'black', 'weight': 'bold'},
            wedgeprops={'edgecolor': 'white'}
        )
        ax.axis('equal')
        plt.subplots_adjust(left=0, right=1, top=1, bottom=0)  # Remove all padding
        buf = io.BytesIO()
        plt.savefig(buf, format='png', transparent=True, dpi=200)
        plt.close(fig)
        buf.seek(0)
        img_base64 = base64.b64encode(buf.read()).decode('utf-8')
        pie_chart_images[p] = img_base64

    # Get batch_name from the first entry (if available)
    batch_name = None
    for model in [FinancialBSC, CustomerBSC, InternalBSC, LearningGrowthBSC]:
        entry = model.objects.filter(batch_id=batch_id, organization=organization).first()
        if entry and getattr(entry, 'batch_name', None):
            batch_name = entry.batch_name
            break
    if not batch_name:
        batch_name = f"Batch {batch_id}"

    html_string = render_to_string('report_pdf.html', {
        'batch_id': batch_id,
        'batch_name': batch_name,
        'grouped': grouped,
        'pie_data_json': json.dumps(pie_data),
        'perspectives': perspectives,
        'pie_chart_images': pie_chart_images,
    })
    pdf = HTML(string=html_string, base_url=request.build_absolute_uri('/')).write_pdf()
    response = HttpResponse(pdf, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="batch_{batch_id}_report.pdf"'
    return response