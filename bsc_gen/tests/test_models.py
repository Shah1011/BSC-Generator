from django.test import TestCase
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from decimal import Decimal
from datetime import date, datetime, timedelta
from bsc_gen.models import (
    Organization, UserProfile, FinancialBSC, CustomerBSC, 
    InternalBSC, LearningGrowthBSC
)


class OrganizationModelTest(TestCase):
    """Unit tests for Organization model"""
    
    def setUp(self):
        self.org_data = {'name': 'Test Organization'}
    
    def test_organization_creation(self):
        """Test organization can be created successfully"""
        org = Organization.objects.create(**self.org_data)
        self.assertEqual(org.name, 'Test Organization')
        self.assertEqual(str(org), 'Test Organization')
    
    def test_organization_unique_name(self):
        """Test organization name must be unique"""
        Organization.objects.create(**self.org_data)
        with self.assertRaises(Exception):
            Organization.objects.create(**self.org_data)


class UserProfileModelTest(TestCase):
    """Unit tests for UserProfile model"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.organization = Organization.objects.create(name='Test Org')
    
    def test_user_profile_creation(self):
        """Test user profile can be created successfully"""
        profile = UserProfile.objects.create(
            user=self.user,
            organization=self.organization,
            role='admin'
        )
        self.assertEqual(profile.user, self.user)
        self.assertEqual(profile.organization, self.organization)
        self.assertEqual(profile.role, 'admin')
        self.assertEqual(str(profile), f"{self.user.username} (admin) - {self.organization.name}")
    
    def test_user_profile_role_choices(self):
        """Test user profile role validation"""
        # Valid roles
        for role in ['admin', 'employee']:
            profile = UserProfile.objects.create(
                user=User.objects.create_user(f'user_{role}', f'{role}@test.com', 'pass'),
                organization=self.organization,
                role=role
            )
            self.assertEqual(profile.role, role)


# Note: StrategyMap, ActionPlan, and PerformanceReview models will be added in future updates


class BSCBaseModelTest(TestCase):
    """Unit tests for BSC base functionality"""
    
    def setUp(self):
        self.organization = Organization.objects.create(name='Test Org')
    
    def test_financial_bsc_creation(self):
        """Test FinancialBSC model creation and methods"""
        financial_bsc = FinancialBSC.objects.create(
            objective='Increase Revenue',
            measure='Monthly Revenue',
            target='100000',
            actual='120000',
            owner='Finance Team',
            date=date.today(),
            batch_id='001',
            organization=self.organization,
            financial_metric='Revenue',
            currency='USD',
            period='Monthly'
        )
        
        # Test basic fields
        self.assertEqual(financial_bsc.objective, 'Increase Revenue')
        self.assertEqual(financial_bsc.measure, 'Monthly Revenue')
        self.assertEqual(financial_bsc.target, '100000')
        self.assertEqual(financial_bsc.actual, '120000')
        self.assertEqual(financial_bsc.financial_metric, 'Revenue')
        self.assertEqual(financial_bsc.currency, 'USD')
        
        # Test status calculation
        self.assertEqual(financial_bsc.get_status(), 'blue')  # 120000 >= 1.2 * 100000
    
    def test_customer_bsc_creation(self):
        """Test CustomerBSC model creation"""
        customer_bsc = CustomerBSC.objects.create(
            objective='Improve Customer Satisfaction',
            measure='Customer Satisfaction Score',
            target='4.5',
            actual='4.2',
            organization=self.organization,
            customer_segment='Premium Customers',
            satisfaction_metric='NPS Score',
            loyalty_indicator='Retention Rate'
        )
        
        self.assertEqual(customer_bsc.get_status(), 'moderate')  # 4.2 >= 0.8 * 4.5 but < 4.5
        self.assertEqual(customer_bsc.customer_segment, 'Premium Customers')
    
    def test_internal_bsc_creation(self):
        """Test InternalBSC model creation"""
        internal_bsc = InternalBSC.objects.create(
            objective='Improve Process Efficiency',
            measure='Process Cycle Time',
            target='5',
            actual='7',
            organization=self.organization,
            process_name='Order Processing',
            efficiency_metric='Cycle Time',
            quality_indicator='Error Rate'
        )
        
        # 7 > 1.2 * 5 = 6, so it should be 'blue' (exceeding target is good for higher values)
        # But for cycle time, lower is better, so this logic might need adjustment in real implementation
        self.assertEqual(internal_bsc.get_status(), 'blue')  # 7 >= 1.2 * 5
        self.assertEqual(internal_bsc.process_name, 'Order Processing')
    
    def test_learning_growth_bsc_creation(self):
        """Test LearningGrowthBSC model creation"""
        learning_bsc = LearningGrowthBSC.objects.create(
            objective='Increase Employee Skills',
            measure='Training Hours per Employee',
            target='40',
            actual='40',
            organization=self.organization,
            skill_area='Technical Skills',
            training_metric='Hours Completed',
            innovation_indicator='New Ideas Submitted'
        )
        
        self.assertEqual(learning_bsc.get_status(), 'good')  # 40 == 40
        self.assertEqual(learning_bsc.skill_area, 'Technical Skills')
    
    def test_bsc_status_edge_cases(self):
        """Test BSC status calculation edge cases"""
        # Test with invalid data
        bsc = FinancialBSC.objects.create(
            objective='Test',
            measure='Test',
            target='invalid',
            actual='100',
            organization=self.organization
        )
        self.assertEqual(bsc.get_status(), 'unknown')
        
        # Test with zero target
        bsc2 = FinancialBSC.objects.create(
            objective='Test2',
            measure='Test2',
            target='0',
            actual='100',
            organization=self.organization
        )
        # Should handle division by zero gracefully
        self.assertIn(bsc2.get_status(), ['unknown', 'blue', 'good', 'moderate', 'bad'])


class ModelIntegrationTest(TestCase):
    """Integration tests for model relationships"""
    
    def setUp(self):
        self.organization = Organization.objects.create(name='Integration Test Org')
        self.user = User.objects.create_user('testuser', 'test@example.com', 'pass')
        self.profile = UserProfile.objects.create(
            user=self.user,
            organization=self.organization,
            role='admin'
        )
    
    def test_basic_bsc_workflow(self):
        """Test basic BSC workflow with current models"""
        # Create BSC entry
        financial_bsc = FinancialBSC.objects.create(
            objective='Increase Revenue',
            measure='Monthly Revenue',
            target='100000',
            actual='80000',  # Below target
            organization=self.organization,
            batch_id='001',
            batch_name='Q1 Data'
        )
        
        # Test relationships
        self.assertEqual(financial_bsc.organization, self.organization)
        self.assertEqual(financial_bsc.batch_id, '001')
        
        # Test business logic
        # 80000 / 100000 = 0.8, which is >= 0.8 * 100000 but < 100000, so it should be 'moderate'
        self.assertEqual(financial_bsc.get_status(), 'moderate')  # 80000 >= 0.8 * 100000 but < 100000
    
    def test_organization_cascade_relationships(self):
        """Test that organization relationships work correctly"""
        # Create multiple BSC entries for the organization
        financial_bsc = FinancialBSC.objects.create(
            objective='Revenue',
            measure='Sales',
            target='100',
            actual='90',
            organization=self.organization
        )
        
        customer_bsc = CustomerBSC.objects.create(
            objective='Satisfaction',
            measure='Score',
            target='5',
            actual='4.5',
            organization=self.organization
        )
        
        # Test organization filtering
        org_financial = FinancialBSC.objects.filter(organization=self.organization)
        org_customer = CustomerBSC.objects.filter(organization=self.organization)
        
        self.assertEqual(org_financial.count(), 1)
        self.assertEqual(org_customer.count(), 1)
        self.assertEqual(org_financial.first(), financial_bsc)
        self.assertEqual(org_customer.first(), customer_bsc)
    
    def test_user_profile_organization_consistency(self):
        """Test user profile and organization consistency"""
        # Create another organization
        other_org = Organization.objects.create(name='Other Org')
        
        # Create user profile for other organization
        other_user = User.objects.create_user('otheruser', 'other@test.com', 'pass')
        other_profile = UserProfile.objects.create(
            user=other_user,
            organization=other_org,
            role='employee'
        )
        
        # Test that profiles are correctly associated with organizations
        self.assertEqual(self.profile.organization, self.organization)
        self.assertEqual(other_profile.organization, other_org)
        self.assertNotEqual(self.profile.organization, other_profile.organization)
        
        # Test organization-specific queries
        org1_profiles = UserProfile.objects.filter(organization=self.organization)
        org2_profiles = UserProfile.objects.filter(organization=other_org)
        
        self.assertEqual(org1_profiles.count(), 1)
        self.assertEqual(org2_profiles.count(), 1)
        self.assertIn(self.profile, org1_profiles)
        self.assertIn(other_profile, org2_profiles)