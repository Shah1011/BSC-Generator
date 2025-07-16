from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from django.contrib.messages import get_messages
from django.core.files.uploadedfile import SimpleUploadedFile
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from unittest.mock import patch, MagicMock
import json
import io
import pandas as pd
from datetime import date, datetime, timedelta

from bsc_gen.models import (
    Organization, UserProfile, FinancialBSC, CustomerBSC, 
    InternalBSC, LearningGrowthBSC
)


class AuthenticationViewsTest(TestCase):
    """Unit tests for authentication views"""
    
    def setUp(self):
        self.client = Client()
        self.organization = Organization.objects.create(name='Test Org')
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.profile = UserProfile.objects.create(
            user=self.user,
            organization=self.organization,
            role='admin'
        )
    
    def test_register_view_get(self):
        """Test register view GET request"""
        response = self.client.get(reverse('register'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Register')
    
    def test_register_view_post_success(self):
        """Test successful user registration"""
        data = {
            'username': 'newuser',
            'email': 'newuser@example.com',
            'password': 'newpass123',
            'password2': 'newpass123',
            'organization': 'New Organization'
        }
        response = self.client.post(reverse('register'), data)
        
        # Should redirect to login
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('login'))
        
        # Check user was created
        self.assertTrue(User.objects.filter(username='newuser').exists())
        
        # Check organization was created
        self.assertTrue(Organization.objects.filter(name='New Organization').exists())
        
        # Check user profile was created
        new_user = User.objects.get(username='newuser')
        self.assertTrue(UserProfile.objects.filter(user=new_user, role='admin').exists())
    
    def test_register_view_password_mismatch(self):
        """Test registration with password mismatch"""
        data = {
            'username': 'newuser',
            'email': 'newuser@example.com',
            'password': 'newpass123',
            'password2': 'differentpass',
            'organization': 'New Organization'
        }
        response = self.client.post(reverse('register'), data)
        
        self.assertEqual(response.status_code, 200)
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any('Passwords do not match' in str(m) for m in messages))
    
    def test_register_view_duplicate_username(self):
        """Test registration with existing username"""
        data = {
            'username': 'testuser',  # Already exists
            'email': 'different@example.com',
            'password': 'newpass123',
            'password2': 'newpass123',
            'organization': 'New Organization'
        }
        response = self.client.post(reverse('register'), data)
        
        self.assertEqual(response.status_code, 200)
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any('Username already exists' in str(m) for m in messages))
    
    def test_login_view_get(self):
        """Test login view GET request"""
        response = self.client.get(reverse('login'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Login')
        self.assertContains(response, 'Forgot your password?')
    
    def test_login_view_post_success(self):
        """Test successful login"""
        data = {
            'username': 'testuser',
            'password': 'testpass123'
        }
        response = self.client.post(reverse('login'), data)
        
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('dashboard'))
    
    def test_login_view_post_invalid_credentials(self):
        """Test login with invalid credentials"""
        data = {
            'username': 'testuser',
            'password': 'wrongpassword'
        }
        response = self.client.post(reverse('login'), data)
        
        self.assertEqual(response.status_code, 200)
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any('Invalid username or password' in str(m) for m in messages))
    
    def test_logout_view(self):
        """Test logout functionality"""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('logout'))
        
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('login'))


class ForgotPasswordViewsTest(TestCase):
    """Unit tests for forgot password functionality"""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
    
    def test_forgot_password_view_get(self):
        """Test forgot password view GET request"""
        response = self.client.get(reverse('forgot_password'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Forgot Password')
    
    @patch('bsc_gen.views.send_mail')
    def test_forgot_password_view_post_success(self, mock_send_mail):
        """Test successful forgot password request"""
        mock_send_mail.return_value = True
        
        data = {'email': 'test@example.com'}
        response = self.client.post(reverse('forgot_password'), data)
        
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('login'))
        
        # Check that email was sent
        mock_send_mail.assert_called_once()
        
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any('Password reset instructions have been sent' in str(m) for m in messages))
    
    def test_forgot_password_view_post_invalid_email(self):
        """Test forgot password with non-existent email"""
        data = {'email': 'nonexistent@example.com'}
        response = self.client.post(reverse('forgot_password'), data)
        
        self.assertEqual(response.status_code, 200)
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any('No account found with that email address' in str(m) for m in messages))
    
    def test_password_reset_confirm_view_get_valid_token(self):
        """Test password reset confirm view with valid token"""
        token = default_token_generator.make_token(self.user)
        uid = urlsafe_base64_encode(force_bytes(self.user.pk))
        
        response = self.client.get(reverse('password_reset_confirm', kwargs={
            'uidb64': uid,
            'token': token
        }))
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Reset Your Password')
        self.assertTrue(response.context['validlink'])
    
    def test_password_reset_confirm_view_get_invalid_token(self):
        """Test password reset confirm view with invalid token"""
        uid = urlsafe_base64_encode(force_bytes(self.user.pk))
        
        response = self.client.get(reverse('password_reset_confirm', kwargs={
            'uidb64': uid,
            'token': 'invalid-token'
        }))
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Invalid Reset Link')
        self.assertFalse(response.context['validlink'])
    
    def test_password_reset_confirm_view_post_success(self):
        """Test successful password reset"""
        token = default_token_generator.make_token(self.user)
        uid = urlsafe_base64_encode(force_bytes(self.user.pk))
        
        data = {
            'new_password': 'newpassword123',
            'confirm_password': 'newpassword123'
        }
        
        response = self.client.post(reverse('password_reset_confirm', kwargs={
            'uidb64': uid,
            'token': token
        }), data)
        
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('login'))
        
        # Check password was changed
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('newpassword123'))
    
    def test_password_reset_confirm_view_post_password_mismatch(self):
        """Test password reset with mismatched passwords"""
        token = default_token_generator.make_token(self.user)
        uid = urlsafe_base64_encode(force_bytes(self.user.pk))
        
        data = {
            'new_password': 'newpassword123',
            'confirm_password': 'differentpassword'
        }
        
        response = self.client.post(reverse('password_reset_confirm', kwargs={
            'uidb64': uid,
            'token': token
        }), data)
        
        self.assertEqual(response.status_code, 200)
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any('Passwords do not match' in str(m) for m in messages))


class DashboardViewsTest(TestCase):
    """Unit tests for dashboard views"""
    
    def setUp(self):
        self.client = Client()
        self.organization = Organization.objects.create(name='Test Org')
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.profile = UserProfile.objects.create(
            user=self.user,
            organization=self.organization,
            role='admin'
        )
        
        # Create sample BSC data
        self.financial_bsc = FinancialBSC.objects.create(
            objective='Increase Revenue',
            measure='Monthly Revenue',
            target='100000',
            actual='120000',
            batch_id='001',
            batch_name='Q1 Data',
            organization=self.organization
        )
    
    def test_dashboard_view_requires_login(self):
        """Test dashboard requires authentication"""
        response = self.client.get(reverse('dashboard'))
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, '/login/?next=/dashboard/')
    
    def test_dashboard_view_get_authenticated(self):
        """Test dashboard view for authenticated user"""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('dashboard'))
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Dashboard')
        self.assertTrue(response.context['is_admin'])
        self.assertEqual(response.context['organization'], self.organization)
        self.assertEqual(len(response.context['bsc_batches']), 1)
    
    def test_dashboard_file_upload_csv(self):
        """Test CSV file upload functionality"""
        self.client.login(username='testuser', password='testpass123')
        
        # Create CSV content
        csv_content = """perspective,objective,measure,target,actual,owner,date
financial,Revenue Growth,Monthly Sales,50000,55000,Sales Team,2024-01-15
customer,Customer Satisfaction,NPS Score,8,8.5,Customer Success,2024-01-15"""
        
        csv_file = SimpleUploadedFile(
            "test_data.csv",
            csv_content.encode('utf-8'),
            content_type="text/csv"
        )
        
        response = self.client.post(reverse('dashboard'), {
            'data_file': csv_file
        })
        
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('dashboard'))
        
        # Check that data was imported
        self.assertTrue(FinancialBSC.objects.filter(objective='Revenue Growth').exists())
        self.assertTrue(CustomerBSC.objects.filter(objective='Customer Satisfaction').exists())
    
    def test_dashboard_file_upload_invalid_format(self):
        """Test upload with invalid file format"""
        self.client.login(username='testuser', password='testpass123')
        
        txt_file = SimpleUploadedFile(
            "test_data.txt",
            b"invalid content",
            content_type="text/plain"
        )
        
        response = self.client.post(reverse('dashboard'), {
            'data_file': txt_file
        })
        
        self.assertEqual(response.status_code, 200)
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any('Invalid file type' in str(m) for m in messages))
    
    def test_dashboard_file_upload_missing_columns(self):
        """Test upload with missing required columns"""
        self.client.login(username='testuser', password='testpass123')
        
        csv_content = """perspective,objective
financial,Revenue Growth"""
        
        csv_file = SimpleUploadedFile(
            "test_data.csv",
            csv_content.encode('utf-8'),
            content_type="text/csv"
        )
        
        response = self.client.post(reverse('dashboard'), {
            'data_file': csv_file
        })
        
        self.assertEqual(response.status_code, 200)
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any('Missing required columns' in str(m) for m in messages))


class BSCDataViewsTest(TestCase):
    """Unit tests for BSC data management views"""
    
    def setUp(self):
        self.client = Client()
        self.organization = Organization.objects.create(name='Test Org')
        self.admin_user = User.objects.create_user(
            username='admin',
            email='admin@example.com',
            password='adminpass123'
        )
        self.admin_profile = UserProfile.objects.create(
            user=self.admin_user,
            organization=self.organization,
            role='admin'
        )
        
        self.employee_user = User.objects.create_user(
            username='employee',
            email='employee@example.com',
            password='employeepass123'
        )
        self.employee_profile = UserProfile.objects.create(
            user=self.employee_user,
            organization=self.organization,
            role='employee'
        )
        
        # Create test data
        self.financial_bsc = FinancialBSC.objects.create(
            objective='Test Objective',
            measure='Test Measure',
            target='100',
            actual='90',
            batch_id='001',
            organization=self.organization
        )
    
    def test_bsc_data_api_requires_login(self):
        """Test BSC data API requires authentication"""
        response = self.client.get(reverse('bsc_data_api'))
        self.assertEqual(response.status_code, 302)
    
    def test_bsc_data_api_authenticated(self):
        """Test BSC data API for authenticated user"""
        self.client.login(username='admin', password='adminpass123')
        response = self.client.get(reverse('bsc_data_api'))
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertIn('entries', data)
        self.assertEqual(len(data['entries']), 1)
        self.assertEqual(data['entries'][0]['objective'], 'Test Objective')
    
    def test_delete_bsc_data_admin_only(self):
        """Test delete BSC data requires admin role"""
        # Test with employee user
        self.client.login(username='employee', password='employeepass123')
        response = self.client.post(reverse('delete_bsc_data'), {
            'admin_password': 'employeepass123'
        })
        
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any('You do not have permission' in str(m) for m in messages))
    
    def test_delete_bsc_data_admin_success(self):
        """Test successful BSC data deletion by admin"""
        self.client.login(username='admin', password='adminpass123')
        response = self.client.post(reverse('delete_bsc_data'), {
            'admin_password': 'adminpass123'
        })
        
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('dashboard'))
        
        # Check data was deleted
        self.assertEqual(FinancialBSC.objects.count(), 0)
    
    def test_delete_bsc_data_wrong_password(self):
        """Test BSC data deletion with wrong password"""
        self.client.login(username='admin', password='adminpass123')
        response = self.client.post(reverse('delete_bsc_data'), {
            'admin_password': 'wrongpassword'
        })
        
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any('Password does not match' in str(m) for m in messages))
        
        # Check data was not deleted
        self.assertEqual(FinancialBSC.objects.count(), 1)
    
    def test_delete_batch_admin_only(self):
        """Test delete batch requires admin role"""
        self.client.login(username='employee', password='employeepass123')
        response = self.client.post(reverse('delete_batch', kwargs={'batch_id': '001'}))
        
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any('You do not have permission' in str(m) for m in messages))
    
    def test_delete_batch_success(self):
        """Test successful batch deletion"""
        self.client.login(username='admin', password='adminpass123')
        response = self.client.post(reverse('delete_batch', kwargs={'batch_id': '001'}))
        
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('dashboard'))
        
        # Check batch was deleted
        self.assertEqual(FinancialBSC.objects.filter(batch_id='001').count(), 0)
    
    def test_update_batch_admin_only(self):
        """Test update batch requires admin role"""
        self.client.login(username='employee', password='employeepass123')
        response = self.client.post(reverse('update_batch', kwargs={'batch_id': '001'}), {
            f'FinancialBSC_{self.financial_bsc.pk}_objective': 'Updated Objective'
        })
        
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any('You do not have permission' in str(m) for m in messages))
    
    def test_update_batch_success(self):
        """Test successful batch update"""
        self.client.login(username='admin', password='adminpass123')
        response = self.client.post(reverse('update_batch', kwargs={'batch_id': '001'}), {
            f'FinancialBSC_{self.financial_bsc.pk}_objective': 'Updated Objective',
            f'FinancialBSC_{self.financial_bsc.pk}_target': '150'
        })
        
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('dashboard'))
        
        # Check data was updated
        self.financial_bsc.refresh_from_db()
        self.assertEqual(self.financial_bsc.objective, 'Updated Objective')
        self.assertEqual(self.financial_bsc.target, '150')
    
    def test_rename_batch_admin_only(self):
        """Test rename batch requires admin role"""
        self.client.login(username='employee', password='employeepass123')
        response = self.client.post(reverse('rename_batch', kwargs={'batch_id': '001'}), {
            'batch_name': 'New Batch Name'
        })
        
        self.assertEqual(response.status_code, 403)
        data = json.loads(response.content)
        self.assertIn('error', data)
    
    def test_rename_batch_success(self):
        """Test successful batch rename"""
        self.client.login(username='admin', password='adminpass123')
        response = self.client.post(reverse('rename_batch', kwargs={'batch_id': '001'}), {
            'batch_name': 'New Batch Name'
        })
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data['success'])
        self.assertEqual(data['new_name'], 'New Batch Name')
        
        # Check batch was renamed
        self.financial_bsc.refresh_from_db()
        self.assertEqual(self.financial_bsc.batch_name, 'New Batch Name')


class ProfileViewsTest(TestCase):
    """Unit tests for profile management views"""
    
    def setUp(self):
        self.client = Client()
        self.organization = Organization.objects.create(name='Test Org')
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            first_name='Test',
            last_name='User'
        )
        self.profile = UserProfile.objects.create(
            user=self.user,
            organization=self.organization,
            role='admin'
        )
    
    def test_profile_view_requires_login(self):
        """Test profile view requires authentication"""
        response = self.client.get(reverse('profile'))
        self.assertEqual(response.status_code, 302)
    
    def test_profile_view_get_authenticated(self):
        """Test profile view for authenticated user"""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('profile'))
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Profile')
        self.assertEqual(response.context['user'], self.user)
        self.assertEqual(response.context['organization'], self.organization)
        self.assertEqual(response.context['role'], 'admin')
    
    def test_profile_update_success(self):
        """Test successful profile update"""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.post(reverse('profile'), {
            'action': 'update_profile',
            'first_name': 'Updated',
            'last_name': 'Name',
            'email': 'updated@example.com'
        })
        
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('profile'))
        
        # Check user was updated
        self.user.refresh_from_db()
        self.assertEqual(self.user.first_name, 'Updated')
        self.assertEqual(self.user.last_name, 'Name')
        self.assertEqual(self.user.email, 'updated@example.com')
    
    def test_password_change_success(self):
        """Test successful password change"""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.post(reverse('profile'), {
            'action': 'change_password',
            'current_password': 'testpass123',
            'new_password': 'newpassword123',
            'confirm_password': 'newpassword123'
        })
        
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('login'))
        
        # Check password was changed
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('newpassword123'))
    
    def test_password_change_wrong_current_password(self):
        """Test password change with wrong current password"""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.post(reverse('profile'), {
            'action': 'change_password',
            'current_password': 'wrongpassword',
            'new_password': 'newpassword123',
            'confirm_password': 'newpassword123'
        })
        
        self.assertEqual(response.status_code, 200)
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any('Current password is incorrect' in str(m) for m in messages))
    
    def test_password_change_mismatch(self):
        """Test password change with mismatched new passwords"""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.post(reverse('profile'), {
            'action': 'change_password',
            'current_password': 'testpass123',
            'new_password': 'newpassword123',
            'confirm_password': 'differentpassword'
        })
        
        self.assertEqual(response.status_code, 200)
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any('New passwords do not match' in str(m) for m in messages))


class ViewerManagementViewsTest(TestCase):
    """Unit tests for viewer management views"""
    
    def setUp(self):
        self.client = Client()
        self.organization = Organization.objects.create(name='Test Org')
        self.admin_user = User.objects.create_user(
            username='admin',
            email='admin@example.com',
            password='adminpass123'
        )
        self.admin_profile = UserProfile.objects.create(
            user=self.admin_user,
            organization=self.organization,
            role='admin'
        )
        
        self.employee_user = User.objects.create_user(
            username='employee',
            email='employee@example.com',
            password='employeepass123'
        )
        self.employee_profile = UserProfile.objects.create(
            user=self.employee_user,
            organization=self.organization,
            role='employee'
        )
    
    def test_add_viewer_admin_only(self):
        """Test add viewer requires admin role"""
        self.client.login(username='employee', password='employeepass123')
        response = self.client.get(reverse('add_viewer'))
        
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('dashboard'))
    
    def test_add_viewer_get_admin(self):
        """Test add viewer view for admin"""
        self.client.login(username='admin', password='adminpass123')
        response = self.client.get(reverse('add_viewer'))
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Add Viewer')
        self.assertEqual(response.context['viewer_count'], 1)  # One existing employee
    
    def test_add_viewer_post_success(self):
        """Test successful viewer creation"""
        self.client.login(username='admin', password='adminpass123')
        response = self.client.post(reverse('add_viewer'), {
            'username': 'newviewer',
            'email': 'newviewer@example.com',
            'first_name': 'New',
            'last_name': 'Viewer',
            'password': 'viewerpass123'
        })
        
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('dashboard'))
        
        # Check viewer was created
        self.assertTrue(User.objects.filter(username='newviewer').exists())
        new_user = User.objects.get(username='newviewer')
        self.assertTrue(UserProfile.objects.filter(user=new_user, role='employee').exists())
    
    def test_add_viewer_duplicate_username(self):
        """Test viewer creation with duplicate username"""
        self.client.login(username='admin', password='adminpass123')
        response = self.client.post(reverse('add_viewer'), {
            'username': 'employee',  # Already exists
            'email': 'different@example.com',
            'password': 'viewerpass123'
        })
        
        self.assertEqual(response.status_code, 200)
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any('Username already exists' in str(m) for m in messages))
    
    def test_delete_viewer_admin_only(self):
        """Test delete viewer requires admin role"""
        self.client.login(username='employee', password='employeepass123')
        response = self.client.post(reverse('delete_viewer', kwargs={
            'viewer_id': self.employee_profile.id
        }))
        
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any('You do not have permission' in str(m) for m in messages))
    
    def test_delete_viewer_success(self):
        """Test successful viewer deletion"""
        self.client.login(username='admin', password='adminpass123')
        response = self.client.post(reverse('delete_viewer', kwargs={
            'viewer_id': self.employee_profile.id
        }))
        
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('add_viewer'))
        
        # Check viewer was deleted
        self.assertFalse(User.objects.filter(username='employee').exists())
    
    def test_delete_viewer_prevent_self_deletion(self):
        """Test admin cannot delete themselves (admin profiles are not found in employee-only query)"""
        self.client.login(username='admin', password='adminpass123')
        response = self.client.post(reverse('delete_viewer', kwargs={
            'viewer_id': self.admin_profile.id
        }))
        
        # Since admin profiles have role='admin', not 'employee', the query won't find them
        # This results in a "Viewer not found" message instead of "cannot delete your own account"
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any('Viewer not found' in str(m) for m in messages))


class IntegrationViewsTest(TestCase):
    """Integration tests for view workflows"""
    
    def setUp(self):
        self.client = Client()
        self.organization = Organization.objects.create(name='Integration Test Org')
        self.admin_user = User.objects.create_user(
            username='admin',
            email='admin@example.com',
            password='adminpass123'
        )
        self.admin_profile = UserProfile.objects.create(
            user=self.admin_user,
            organization=self.organization,
            role='admin'
        )
    
    def test_complete_user_workflow(self):
        """Test complete user workflow from registration to data management"""
        # 1. Register new user
        response = self.client.post(reverse('register'), {
            'username': 'newadmin',
            'email': 'newadmin@example.com',
            'password': 'newpass123',
            'password2': 'newpass123',
            'organization': 'New Test Org'
        })
        self.assertEqual(response.status_code, 302)
        
        # 2. Login
        response = self.client.post(reverse('login'), {
            'username': 'newadmin',
            'password': 'newpass123'
        })
        self.assertEqual(response.status_code, 302)
        
        # 3. Access dashboard
        response = self.client.get(reverse('dashboard'))
        self.assertEqual(response.status_code, 200)
        
        # 4. Upload BSC data
        csv_content = """perspective,objective,measure,target,actual
financial,Revenue,Sales,100000,110000
customer,Satisfaction,NPS,8,8.5"""
        
        csv_file = SimpleUploadedFile(
            "test_data.csv",
            csv_content.encode('utf-8'),
            content_type="text/csv"
        )
        
        response = self.client.post(reverse('dashboard'), {
            'data_file': csv_file
        })
        self.assertEqual(response.status_code, 302)
        
        # 5. Verify data was created
        new_org = Organization.objects.get(name='New Test Org')
        self.assertTrue(FinancialBSC.objects.filter(organization=new_org).exists())
        self.assertTrue(CustomerBSC.objects.filter(organization=new_org).exists())
        
        # 6. Update profile
        response = self.client.post(reverse('profile'), {
            'action': 'update_profile',
            'first_name': 'New',
            'last_name': 'Admin',
            'email': 'updated@example.com'
        })
        self.assertEqual(response.status_code, 302)
        
        # 7. Add viewer
        response = self.client.post(reverse('add_viewer'), {
            'username': 'viewer1',
            'email': 'viewer1@example.com',
            'password': 'viewerpass123'
        })
        self.assertEqual(response.status_code, 302)
        
        # Verify viewer was created
        self.assertTrue(User.objects.filter(username='viewer1').exists())
    
    def test_data_isolation_between_organizations(self):
        """Test that organizations can only see their own data"""
        # Create second organization and user
        org2 = Organization.objects.create(name='Org 2')
        user2 = User.objects.create_user('user2', 'user2@example.com', 'pass')
        profile2 = UserProfile.objects.create(user=user2, organization=org2, role='admin')
        
        # Create data for first organization
        self.client.login(username='admin', password='adminpass123')
        FinancialBSC.objects.create(
            objective='Org 1 Objective',
            measure='Measure',
            target='100',
            actual='90',
            organization=self.organization
        )
        
        # Create data for second organization
        self.client.login(username='user2', password='pass')
        FinancialBSC.objects.create(
            objective='Org 2 Objective',
            measure='Measure',
            target='100',
            actual='90',
            organization=org2
        )
        
        # Test first user can only see their data
        self.client.login(username='admin', password='adminpass123')
        response = self.client.get(reverse('bsc_data_api'))
        data = json.loads(response.content)
        objectives = [entry['objective'] for entry in data['entries']]
        self.assertIn('Org 1 Objective', objectives)
        self.assertNotIn('Org 2 Objective', objectives)
        
        # Test second user can only see their data
        self.client.login(username='user2', password='pass')
        response = self.client.get(reverse('bsc_data_api'))
        data = json.loads(response.content)
        objectives = [entry['objective'] for entry in data['entries']]
        self.assertIn('Org 2 Objective', objectives)
        self.assertNotIn('Org 1 Objective', objectives)