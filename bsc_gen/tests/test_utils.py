from django.test import TestCase
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.utils import timezone
from datetime import date, datetime, timedelta
import json

from bsc_gen.models import Organization, UserProfile, FinancialBSC


class UtilityFunctionsTest(TestCase):
    """Unit tests for utility functions and edge cases"""
    
    def setUp(self):
        self.organization = Organization.objects.create(name='Test Org')
        self.user = User.objects.create_user('testuser', 'test@example.com', 'pass')
        self.profile = UserProfile.objects.create(
            user=self.user,
            organization=self.organization,
            role='admin'
        )
    
    def test_bsc_status_calculation_edge_cases(self):
        """Test BSC status calculation with various edge cases"""
        test_cases = [
            # (target, actual, expected_status)
            ('100', '120', 'blue'),      # 120 >= 1.2 * 100
            ('100', '100', 'good'),      # 100 >= 100
            ('100', '90', 'moderate'),   # 90 >= 0.8 * 100
            ('100', '70', 'bad'),        # 70 < 0.8 * 100
            ('0', '100', 'blue'),        # Division by zero case - actual behavior
            ('abc', '100', 'unknown'),   # Invalid target
            ('100', 'xyz', 'unknown'),   # Invalid actual
            ('', '100', 'unknown'),      # Empty target
            ('100', '', 'unknown'),      # Empty actual
            ('-100', '50', 'blue'),      # Negative target - actual behavior
            ('100', '-50', 'bad'),       # Negative actual
        ]
        
        for i, (target, actual, expected) in enumerate(test_cases):
            with self.subTest(case=i, target=target, actual=actual):
                bsc = FinancialBSC.objects.create(
                    objective=f'Test {i}',
                    measure=f'Measure {i}',
                    target=target,
                    actual=actual,
                    organization=self.organization
                )
                self.assertEqual(bsc.get_status(), expected)
    
    def test_batch_id_generation_logic(self):
        """Test batch ID generation and uniqueness"""
        # Create first BSC entry
        bsc1 = FinancialBSC.objects.create(
            objective='First',
            measure='Measure',
            target='100',
            actual='90',
            batch_id='001',
            organization=self.organization
        )
        
        # Create second BSC entry with same batch
        bsc2 = FinancialBSC.objects.create(
            objective='Second',
            measure='Measure',
            target='100',
            actual='90',
            batch_id='001',
            organization=self.organization
        )
        
        # Both should have same batch_id
        self.assertEqual(bsc1.batch_id, bsc2.batch_id)
        
        # Create third with different batch
        bsc3 = FinancialBSC.objects.create(
            objective='Third',
            measure='Measure',
            target='100',
            actual='90',
            batch_id='002',
            organization=self.organization
        )
        
        self.assertNotEqual(bsc1.batch_id, bsc3.batch_id)
    
    def test_organization_data_isolation(self):
        """Test that organizations cannot access each other's data"""
        # Create second organization
        org2 = Organization.objects.create(name='Org 2')
        
        # Create BSC data for first organization
        bsc1 = FinancialBSC.objects.create(
            objective='Org 1 Data',
            measure='Measure',
            target='100',
            actual='90',
            organization=self.organization
        )
        
        # Create BSC data for second organization
        bsc2 = FinancialBSC.objects.create(
            objective='Org 2 Data',
            measure='Measure',
            target='100',
            actual='90',
            organization=org2
        )
        
        # Test filtering by organization
        org1_data = FinancialBSC.objects.filter(organization=self.organization)
        org2_data = FinancialBSC.objects.filter(organization=org2)
        
        self.assertEqual(org1_data.count(), 1)
        self.assertEqual(org2_data.count(), 1)
        self.assertEqual(org1_data.first().objective, 'Org 1 Data')
        self.assertEqual(org2_data.first().objective, 'Org 2 Data')
    
    def test_user_profile_role_validation(self):
        """Test user profile role validation"""
        valid_roles = ['admin', 'employee']
        
        for role in valid_roles:
            user = User.objects.create_user(f'user_{role}', f'{role}@test.com', 'pass')
            profile = UserProfile.objects.create(
                user=user,
                organization=self.organization,
                role=role
            )
            self.assertEqual(profile.role, role)
    
    def test_model_string_representations(self):
        """Test model __str__ methods"""
        # Test Organization
        self.assertEqual(str(self.organization), 'Test Org')
        
        # Test UserProfile
        expected_profile_str = f"{self.user.username} (admin) - {self.organization.name}"
        self.assertEqual(str(self.profile), expected_profile_str)
        
        # Test BSC models
        bsc = FinancialBSC.objects.create(
            objective='Test Objective',
            measure='Test Measure',
            target='100',
            actual='90',
            organization=self.organization
        )
        self.assertEqual(str(bsc), 'Financial - Test Objective')
    
    def test_date_handling(self):
        """Test date field handling in BSC models"""
        # Test with valid date
        bsc_with_date = FinancialBSC.objects.create(
            objective='With Date',
            measure='Measure',
            target='100',
            actual='90',
            date=date.today(),
            organization=self.organization
        )
        self.assertEqual(bsc_with_date.date, date.today())
        
        # Test without date (should be None)
        bsc_without_date = FinancialBSC.objects.create(
            objective='Without Date',
            measure='Measure',
            target='100',
            actual='90',
            organization=self.organization
        )
        self.assertIsNone(bsc_without_date.date)
    
    def test_upload_time_auto_generation(self):
        """Test that upload_time is automatically set"""
        before_creation = timezone.now()
        
        bsc = FinancialBSC.objects.create(
            objective='Test Upload Time',
            measure='Measure',
            target='100',
            actual='90',
            organization=self.organization
        )
        
        after_creation = timezone.now()
        
        self.assertIsNotNone(bsc.upload_time)
        self.assertGreaterEqual(bsc.upload_time, before_creation)
        self.assertLessEqual(bsc.upload_time, after_creation)
    
    def test_optional_fields(self):
        """Test that optional fields can be None or empty"""
        bsc = FinancialBSC.objects.create(
            objective='Required Field',
            measure='Required Field',
            target='100',
            actual='90',
            organization=self.organization,
            # Optional fields not provided
            owner=None,
            date=None,
            batch_id=None,
            batch_name=None
        )
        
        self.assertIsNone(bsc.owner)
        self.assertIsNone(bsc.date)
        self.assertIsNone(bsc.batch_id)
        self.assertIsNone(bsc.batch_name)
        
        # Should still be able to calculate status
        # 90 >= 0.8 * 100 (80), so it should be 'moderate'
        self.assertEqual(bsc.get_status(), 'moderate')
    
    def test_model_field_max_lengths(self):
        """Test model field maximum lengths"""
        # Test with maximum length strings
        long_string_255 = 'x' * 255
        long_string_10 = 'x' * 10
        
        bsc = FinancialBSC.objects.create(
            objective=long_string_255,
            measure=long_string_255,
            target=long_string_255,
            actual=long_string_255,
            owner=long_string_255,
            batch_id=long_string_10,
            batch_name=long_string_255,
            organization=self.organization,
            financial_metric=long_string_255,
            currency=long_string_10,
            period='x' * 50
        )
        
        self.assertEqual(len(bsc.objective), 255)
        self.assertEqual(len(bsc.batch_id), 10)
        self.assertEqual(len(bsc.currency), 10)


class PerformanceTest(TestCase):
    """Performance and load tests"""
    
    def setUp(self):
        self.organization = Organization.objects.create(name='Performance Test Org')
    
    def test_bulk_bsc_creation_performance(self):
        """Test performance with bulk BSC data creation"""
        import time
        
        start_time = time.time()
        
        # Create 100 BSC entries
        bsc_entries = []
        for i in range(100):
            bsc_entries.append(FinancialBSC(
                objective=f'Objective {i}',
                measure=f'Measure {i}',
                target=str(100 + i),
                actual=str(90 + i),
                batch_id=f'{i:03d}',
                organization=self.organization
            ))
        
        FinancialBSC.objects.bulk_create(bsc_entries)
        
        end_time = time.time()
        creation_time = end_time - start_time
        
        # Should create 100 entries in reasonable time (less than 1 second)
        self.assertLess(creation_time, 1.0)
        self.assertEqual(FinancialBSC.objects.count(), 100)
    
    def test_query_performance_with_large_dataset(self):
        """Test query performance with larger dataset"""
        import time
        
        # Create test data
        bsc_entries = []
        for i in range(50):
            bsc_entries.append(FinancialBSC(
                objective=f'Objective {i}',
                measure=f'Measure {i}',
                target=str(100 + i),
                actual=str(90 + i),
                batch_id=f'{i:03d}',
                organization=self.organization
            ))
        
        FinancialBSC.objects.bulk_create(bsc_entries)
        
        # Test query performance
        start_time = time.time()
        
        # Perform various queries
        all_entries = list(FinancialBSC.objects.all())
        org_entries = list(FinancialBSC.objects.filter(organization=self.organization))
        status_calculations = [entry.get_status() for entry in org_entries[:10]]
        
        end_time = time.time()
        query_time = end_time - start_time
        
        # Queries should complete in reasonable time
        self.assertLess(query_time, 0.5)
        self.assertEqual(len(all_entries), 50)
        self.assertEqual(len(org_entries), 50)
        self.assertEqual(len(status_calculations), 10)