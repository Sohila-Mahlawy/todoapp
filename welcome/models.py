from django.contrib.auth.models import AbstractUser, Group, Permission
from django.db import models, transaction
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone

class CustomUser(AbstractUser):
    subscription_type = models.CharField(
        max_length=20,
        choices=[('free', 'Free'),('pro', 'Pro'),('business','Business')],
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

    def get_notification_settings(self):
        # Get or create notification settings
        settings, created = NotificationSettings.objects.get_or_create(user=self)
        return settings

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
    due_date = models.DateTimeField(null=True, blank=True)  # New field

    def __str__(self):
        return self.task_name

# Model for logged user tasks
class LoggedUserTask(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    task_name = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    is_done = models.BooleanField(default=False)  # Add the is_done field
    due_date = models.DateTimeField(null=True, blank=True)  # New field

    def __str__(self):
        return self.task_name

class ProUserTask(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)  # Task creator
    task_name = models.CharField(max_length=255)
    project = models.ForeignKey(
        'projects.Project', on_delete=models.CASCADE, null=True, blank=True, related_name='tasks'
    )
    assigned_to = models.ForeignKey(
        CustomUser, on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_tasks'
    )
    uploaded_file = models.FileField(upload_to='task_files/', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    is_done = models.BooleanField(default=False)
    due_date = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return self.task_name

    def has_changed(self, field_name):
        """Check if a specific field has changed."""
        # If this is a new object, then nothing has changed yet
        if self.pk is None:
            return False
        
        # Get the original values from the database
        try:
            original = ProUserTask.objects.get(pk=self.pk)
            if field_name == 'is_done':
                return self.is_done != original.is_done
            elif field_name == 'assigned_to':
                return self.assigned_to != original.assigned_to
            elif field_name == 'task_name':
                return self.task_name != original.task_name
            elif field_name == 'due_date':
                return self.due_date != original.due_date
        except ProUserTask.DoesNotExist:
            return False
        
        return False

    def save(self, *args, **kwargs):
        # Check if this is a new task or an existing one being updated
        is_new = self.pk is None
        
        # Send notifications before saving
        if not is_new:
            self.handle_notifications()

        super().save(*args, **kwargs)

    def handle_notifications(self):
        """Handle all notifications for task updates."""
        if self.has_changed('assigned_to'):
            self.send_task_assignment_notification()
        
        if self.has_changed('is_done') and self.is_done:
            self.send_task_completion_notification()

        if self.has_changed('task_name') or self.has_changed('due_date'):
            self.send_task_update_notification()

    def send_task_assignment_notification(self):
        if self.assigned_to:
            # Check if the user has enabled task assignment notifications
            if self.assigned_to.notification_settings.task_assignments:
                # Use a database transaction with select_for_update to lock the row
                with transaction.atomic():
                    # Try to find or create a notification
                    notification, created = Notification.objects.get_or_create(
                        user=self.assigned_to,
                        notification_type='info',
                        message=f'You have been assigned a new task: {self.task_name}',
                        created_at__gte=timezone.now() - timezone.timedelta(seconds=10),
                        defaults={
                            'user': self.assigned_to,
                            'notification_type': 'info',
                            'message': f'You have been assigned a new task: {self.task_name}'
                        }
                    )

    def send_task_completion_notification(self):
        if self.user.notification_settings.task_completion:
            print(f"DEBUG: Creating task completion notification for task {self.task_name}")
            
            # Use a database transaction with select_for_update to lock the row
            with transaction.atomic():
                # Use a unique identifier for this notification
                notification_key = f"task_completion_{self.id}_{timezone.now().strftime('%Y%m%d')}"
                
                # Try to find or create a "lock" record to prevent duplicates
                # Using get_or_create with defaults ensures only one notification is created
                notification, created = Notification.objects.get_or_create(
                    user=self.user,
                    notification_type='success',
                    message=f'Task "{self.task_name}" has been completed',
                    created_at__gte=timezone.now() - timezone.timedelta(seconds=10),
                    defaults={
                        'user': self.user,
                        'notification_type': 'success',
                        'message': f'Task "{self.task_name}" has been completed'
                    }
                )
                
                if not created:
                    print(f"DEBUG: Skipping duplicate notification for task {self.task_name}")
                else:
                    print(f"DEBUG: Successfully created notification for task {self.task_name}")
                    
    def send_task_update_notification(self):
        if self.assigned_to and self.assigned_to.notification_settings.task_updates:
            # Use a database transaction with select_for_update to lock the row
            with transaction.atomic():
                # Try to find or create a notification
                notification, created = Notification.objects.get_or_create(
                    user=self.assigned_to,
                    notification_type='info',
                    message=f'Task "{self.task_name}" has been updated',
                    created_at__gte=timezone.now() - timezone.timedelta(seconds=10),
                    defaults={
                        'user': self.assigned_to,
                        'notification_type': 'info',
                        'message': f'Task "{self.task_name}" has been updated'
                    }
                )

# Model for task feedback
class TaskFeedback(models.Model):
    task = models.ForeignKey(ProUserTask, on_delete=models.CASCADE, related_name='feedback')
    feedback = models.TextField()
    approved = models.BooleanField(default=False)

    def __str__(self):
        return f"Feedback for {self.task.task_name}"



class SubscriptionOrder(models.Model):
    # User who initiated the subscription
    user = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='subscription_orders'
    )

    # Payment status choices
    PAYMENT_STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('Completed', 'Completed'),
        ('Failed', 'Failed'),
    ]

    # Payment status (default is Pending)
    payment_status = models.CharField(
        max_length=20,
        choices=PAYMENT_STATUS_CHOICES,
        default='Pending'
    )

    # Stripe Payment Intent ID
    payment_intent_id = models.CharField(max_length=255, null=True, blank=True)  # Add this field


    # Amount in cents (Stripe requires amounts in the smallest currency unit)
    amount_cents = models.PositiveIntegerField(
        help_text="Amount in cents (e.g., $5.00 = 500)"
    )

    # Timestamp when the order was created
    created_at = models.DateTimeField(auto_now_add=True)

    # Optional: Timestamp when the payment was completed
    completed_at = models.DateTimeField(blank=True, null=True)

    subscription_type = models.CharField(
        max_length=20,
        choices=[('pro', 'Pro'), ('business', 'Business')],
        default='pro'
    )

    def _str_(self):
        return f"SubscriptionOrder #{self.id} - {self.user.username} ({self.payment_status})"

    def mark_as_completed(self):
        """
        Mark the subscription order as completed and update the timestamp.
        """
        self.payment_status = 'Completed'
        self.completed_at = now()
        self.save()

    def mark_as_failed(self):
        """
        Mark the subscription order as failed.
        """
        self.payment_status = 'Failed'
        self.save()
        
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

class CalendarEvent(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    title = models.CharField(max_length=255)
    start_date = models.DateField()
    end_date = models.DateField()
    description = models.TextField(blank=True, null=True)  # Add description field

    def __str__(self):
        return self.title


class Notification(models.Model):
    # Notification types (e.g., 'info', 'warning', 'error', etc.)
    NOTIFICATION_TYPES = [
        ('info', 'Information'),
        ('warning', 'Warning'),
        ('error', 'Error'),
        ('success', 'Success'),
        ('announcement', 'Announcement'),
        ('message', 'Message'),
        ('subscription', 'Subscription')
    ]

    # Fields for the notification
    user = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='notifications',
        help_text="The user who will receive this notification."
    )
    notification_type = models.CharField(
        max_length=20,
        choices=NOTIFICATION_TYPES,
        default='info',
        help_text="The type of the notification (e.g., info, warning, error)."
    )
    message = models.TextField(
        help_text="The content or message of the notification."
    )
    is_read = models.BooleanField(
        default=False,
        help_text="Whether the notification has been read by the user."
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="The timestamp when the notification was created."
    )

    def __str__(self):
        return f"{self.notification_type.capitalize()} to {self.user.username}: {self.message[:50]}"

    class Meta:
        ordering = ['-created_at']  # Order notifications by most recent first
        verbose_name = "Notification"
        verbose_name_plural = "Notifications"

class FAQ(models.Model):
    question = models.CharField(max_length=200)
    answer = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.question

class NotificationSettings(models.Model):
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='notification_settings')
    task_assignments = models.BooleanField(default=True)
    due_date_reminders = models.BooleanField(default=True)
    task_completion = models.BooleanField(default=True)
    new_projects = models.BooleanField(default=True)
    role_changes = models.BooleanField(default=True)

    def __str__(self):
        return f"Notification Settings for {self.user.username}"

@receiver(post_save, sender=CustomUser)
def create_notification_settings(sender, instance, created, **kwargs):
    if created:
        NotificationSettings.objects.create(user=instance)

class FeatureUpdate(models.Model):
    title = models.CharField(max_length=255)
    description = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.title

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Feature Update"
        verbose_name_plural = "Feature Updates"


class UISettings(models.Model):
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='ui_settings')
    navbar_fixed = models.BooleanField(default=False)
    dark_mode = models.BooleanField(default=False)
    sidenav_type = models.CharField(
        max_length=50,  # Increased length to accommodate full class names
        choices=[
            ('bg-gradient-dark', 'Dark'),
            ('bg-transparent', 'Transparent'),
            ('bg-white', 'White')
        ],
        default='bg-white'
    )
    sidebar_color = models.CharField(
        max_length=50,  # Increased length to accommodate full class names
        choices=[
            ('bg-gradient-primary', 'Primary'),
            ('bg-gradient-dark', 'Dark'),
            ('bg-gradient-info', 'Info'),
            ('bg-gradient-success', 'Success'),
            ('bg-gradient-warning', 'Warning'),
            ('bg-gradient-danger', 'Danger')
        ],
        default='bg-gradient-primary'
    )

    def __str__(self):
        return f"UI Settings for {self.user.username}"

@receiver(post_save, sender=CustomUser)
def create_ui_settings(sender, instance, created, **kwargs):
    if created:
        UISettings.objects.create(user=instance)

@receiver(post_save, sender=CustomUser)
def save_ui_settings(sender, instance, **kwargs):
    try:
        instance.ui_settings.save()
    except UISettings.DoesNotExist:
        UISettings.objects.create(user=instance)