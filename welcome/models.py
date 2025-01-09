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
        'Project', on_delete=models.CASCADE, null=True, blank=True, related_name='tasks'
    )  # Related name for reverse querying tasks by project
    assigned_to = models.ForeignKey(
        CustomUser, on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_tasks'
    )  # User to whom the task is assigned
    uploaded_file = models.FileField(upload_to='task_files/', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    is_done = models.BooleanField(default=False)

    def __str__(self):
        return self.task_name

class Project(models.Model):
    name = models.CharField(max_length=255)
    created_by = models.ForeignKey(
        CustomUser, on_delete=models.CASCADE, related_name='projects'
    )
    start_date = models.DateField()
    end_date = models.DateField()
    members = models.ManyToManyField(CustomUser, related_name='project_members')

    def __str__(self):
        return f"Project by {self.created_by.username}"

    # Optional utility method to retrieve all tasks
    def get_tasks(self):
        return self.tasks.all()

# Model for task feedback
class TaskFeedback(models.Model):
    task = models.ForeignKey(ProUserTask, on_delete=models.CASCADE, related_name='feedback')
    feedback = models.TextField()
    approved = models.BooleanField(default=False)

    def __str__(self):
        return f"Feedback for {self.task.task_name}"

# Model for invitations
class Invitation(models.Model):
    ROLE_CHOICES = [
        ('team_member', 'Team Member'),
        ('product_owner', 'Product Owner'),
    ]
    team_leader = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='sent_invitations')
    name = models.CharField(max_length=255)
    email = models.EmailField()
    token = models.CharField(max_length=255, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    accepted = models.BooleanField(default=False)
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='invitations')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='team_member')  # Add this field

    def __str__(self):
        return f"Invitation to {self.email} for {self.project} as {self.role}"

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

class Business(models.Model):
    name = models.CharField(max_length=255)
    icon = models.ImageField(upload_to='uploaded_icons/')
    employee_file = models.FileField(upload_to='employee_files/')
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='businesses')
    members = models.ManyToManyField(CustomUser, related_name='member_of_businesses')
    category = models.CharField(max_length=200, null=True)
    
class UserProfile(models.Model):
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE)
    status = models.CharField(max_length=10, default='Deactivfated')  # 'Activated' or 'Deactivated'
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

class CallCenter(models.Model):
    business = models.ForeignKey(Business, on_delete=models.CASCADE, related_name='call_centers')
    zip_file = models.FileField(upload_to='call_center_zips/')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Call Center for {self.business.name}"

class FinanceRecord(models.Model):
    business = models.ForeignKey(Business, on_delete=models.CASCADE)
    sold_piece = models.CharField(max_length=255)
    sold_to = models.CharField(max_length=255)
    date = models.DateField()
    total_price = models.DecimalField(max_digits=10, decimal_places=2)
    paid_price = models.DecimalField(max_digits=10, decimal_places=2)
