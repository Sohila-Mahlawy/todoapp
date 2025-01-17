from django.contrib.auth.models import AbstractUser, Group, Permission
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver

class CustomUser(AbstractUser):
    subscription_type = models.CharField(
        max_length=20,
        choices=[('free', 'Free'), ('pro', 'Pro')],
        default='free'
    )
    ROLE_CHOICES = [
        ('team_leader', 'Team Leader'),
        ('product_owner', 'Product Owner'),
        ('programmer', 'Programmer'),
    ]
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, null=True)
    trial_start_date = models.DateField(null=True, blank=True)
    category = models.CharField(
        max_length=20,
        choices=[('programming', 'Programming'), ('education', 'Education'), ('crm', 'CRM')],
        null=True
    )
    pro_subscription_date = models.DateField(null=True, blank=True)
    subscription_end_date = models.DateField(null=True, blank=True)
    groups = models.ManyToManyField(
        Group,
        related_name="custom_user_groups",
        blank=True
    )
    user_permissions = models.ManyToManyField(
        Permission,
        related_name="custom_user_permissions",
        blank=True
    )

class MemberProfile(models.Model):
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name="profile")
    job_description = models.TextField(default='No job description')
    role = models.TextField()
# Model for unlogged user tasks
class UnloggedUserTask(models.Model):
    ip_address = models.GenericIPAddressField()
    task_name = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    is_done = models.BooleanField(default=False)  # Add the is_done field

    def __str__(self):
        return self.task_name

# Model for logged user tasks
class LoggedUserTask(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    task_name = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    is_done = models.BooleanField(default=False)  # Add the is_done field

    def __str__(self):
        return self.task_name

class ProUserTask(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)  # Task creator
    task_name = models.CharField(max_length=255)
    project = models.ForeignKey(
        'projects.Project', on_delete=models.CASCADE, null=True, blank=True, related_name='tasks'
    )  # Related name for reverse querying tasks by project
    assigned_to = models.ForeignKey(
        CustomUser, on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_tasks'
    )  # User to whom the task is assigned
    uploaded_file = models.FileField(upload_to='task_files/', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    is_done = models.BooleanField(default=False)

    def __str__(self):
        return self.task_name

# Model for task feedback
class TaskFeedback(models.Model):
    task = models.ForeignKey(ProUserTask, on_delete=models.CASCADE, related_name='feedback')
    feedback = models.TextField()
    approved = models.BooleanField(default=False)

    def __str__(self):
        return f"Feedback for {self.task.task_name}"



class SubscriptionOrder(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    payment_status = models.CharField(
        max_length=20,
        choices=[('Pending', 'Pending'), ('Completed', 'Completed'), ('Failed', 'Failed')],
        default='Pending'
    )
    payment_key = models.CharField(max_length=255, blank=True, null=True)
    payment_url = models.URLField(blank=True, null=True)
    amount_cents = models.PositiveIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)
    
class UserProfile(models.Model):
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE)
    status = models.CharField(max_length=10, default='Deactivated')  # 'Activated' or 'Deactivated'
    logged_in_status = models.CharField(max_length=10, default='Unlogged')  # 'Logged In' or 'Unlogged'

    def __str__(self):
        return self.user.username

@receiver(post_save, sender=CustomUser)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)

@receiver(post_save, sender=CustomUser)
def save_user_profile(sender, instance, **kwargs):
    try:
        instance.userprofile.save()
    except UserProfile.DoesNotExist:
        UserProfile.objects.create(user=instance)
