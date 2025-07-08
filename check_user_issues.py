import os
import django
from django.conf import settings

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bsc_gen.settings')
django.setup()

from django.contrib.auth.models import User

def check_user_issues():
    print("=== CHECKING FOR POTENTIAL ISSUES ===\n")
    
    all_users = User.objects.all()
    
    # Find users without email
    users_no_email = User.objects.filter(email__isnull=True) | User.objects.filter(email='')

    for user in users_no_email:
        print(f"User {user.username} has no email")
        # You can manually add emails if needed
        # user.email = f"{user.username}@example.com"
        # user.save()
    
    # Check for inactive users
    inactive_users = User.objects.filter(is_active=False)
    if inactive_users:
        print("⚠️  Inactive users (password reset might not work):")
        for user in inactive_users:
            print(f"   - {user.username} ({user.email})")
        print()
    
    # Activate all users
    User.objects.filter(is_active=False).update(is_active=True)
    
    # Check for duplicate emails
    from django.db.models import Count
    duplicate_emails = User.objects.values('email').annotate(count=Count('email')).filter(count__gt=1)
    if duplicate_emails:
        print("⚠️  Duplicate email addresses:")
        for item in duplicate_emails:
            users_with_email = User.objects.filter(email=item['email'])
            print(f"   Email: {item['email']}")
            for user in users_with_email:
                print(f"     - {user.username}")
        print()
    
    # Summary
    total_users = all_users.count()
    valid_users = User.objects.filter(is_active=True).exclude(email__isnull=True).exclude(email='').count()
    
    print("=== SUMMARY ===")
    print(f"Total users: {total_users}")
    print(f"Users who can use password reset: {valid_users}")
    print(f"Users who cannot use password reset: {total_users - valid_users}")

if __name__ == "__main__":
    check_user_issues()