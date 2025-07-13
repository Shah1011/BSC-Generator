from django.db import models
from django.contrib.auth.models import User

class Organization(models.Model):
    name = models.CharField(max_length=255, unique=True)

    def __str__(self):
        return self.name

class UserProfile(models.Model):
    ROLE_CHOICES = (
        ('admin', 'Admin'),
        ('employee', 'Employee'),
    )
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE)
    role = models.CharField(max_length=10, choices=ROLE_CHOICES)

    def __str__(self):
        return f"{self.user.username} ({self.role}) - {self.organization.name}"

# Base class for common BSC fields
class BSCBase(models.Model):
    objective = models.CharField(max_length=255)
    measure = models.CharField(max_length=255)
    target = models.CharField(max_length=255)
    actual = models.CharField(max_length=255)
    owner = models.CharField(max_length=255, blank=True, null=True)
    date = models.DateField(blank=True, null=True)
    batch_id = models.CharField(max_length=10, blank=True, null=True)
    batch_name = models.CharField(max_length=255, blank=True, null=True)
    upload_time = models.DateTimeField(auto_now_add=True, blank=True, null=True)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, null=True, blank=True)

    class Meta:
        abstract = True

    def get_status(self):
        try:
            actual_val = float(self.actual)
            target_val = float(self.target)
            if actual_val >= target_val:
                return 'good'
            elif actual_val >= 0.8 * target_val:
                return 'moderate'
            else:
                return 'bad'
        except (ValueError, TypeError):
            return 'unknown'

# Financial Perspective
class FinancialBSC(BSCBase):
    financial_metric = models.CharField(max_length=255, help_text="Specific financial metric (e.g., Revenue, Profit, ROI)")
    currency = models.CharField(max_length=10, default='USD', help_text="Currency for financial metrics")
    period = models.CharField(max_length=50, blank=True, help_text="Reporting period (Monthly, Quarterly, Annual)")

    def __str__(self):
        return f"Financial - {self.objective}"

# Customer Perspective
class CustomerBSC(BSCBase):
    customer_segment = models.CharField(max_length=255, blank=True, help_text="Target customer segment")
    satisfaction_metric = models.CharField(max_length=255, blank=True, help_text="Customer satisfaction metric")
    loyalty_indicator = models.CharField(max_length=255, blank=True, help_text="Customer loyalty indicator")

    def __str__(self):
        return f"Customer - {self.objective}"

# Internal Process Perspective
class InternalBSC(BSCBase):
    process_name = models.CharField(max_length=255, blank=True, help_text="Internal process name")
    efficiency_metric = models.CharField(max_length=255, blank=True, help_text="Process efficiency metric")
    quality_indicator = models.CharField(max_length=255, blank=True, help_text="Quality indicator")

    def __str__(self):
        return f"Internal - {self.objective}"

# Learning & Growth Perspective
class LearningGrowthBSC(BSCBase):
    skill_area = models.CharField(max_length=255, blank=True, help_text="Skill or knowledge area")
    training_metric = models.CharField(max_length=255, blank=True, help_text="Training or development metric")
    innovation_indicator = models.CharField(max_length=255, blank=True, help_text="Innovation indicator")

    def __str__(self):
        return f"Learning & Growth - {self.objective}"

# Keep the old model for backward compatibility during migration
class BSCEntry(models.Model):
    PERSPECTIVE_CHOICES = [
        ('Financial', 'Financial'),
        ('Customer', 'Customer'),
        ('Internal', 'Internal'),
        ('Learning & Growth', 'Learning & Growth'),
    ]
    perspective = models.CharField(max_length=32, choices=PERSPECTIVE_CHOICES)
    objective = models.CharField(max_length=255)
    measure = models.CharField(max_length=255)
    target = models.CharField(max_length=255)
    actual = models.CharField(max_length=255)
    owner = models.CharField(max_length=255, blank=True, null=True)
    date = models.DateField(blank=True, null=True)
    batch_id = models.CharField(max_length=10, blank=True, null=True)
    upload_time = models.DateTimeField(auto_now_add=True, blank=True, null=True)

    def __str__(self):
        return f"{self.perspective} - {self.objective}" 