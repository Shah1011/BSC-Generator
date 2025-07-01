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