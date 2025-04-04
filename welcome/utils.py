from django.shortcuts import redirect
from django.contrib import messages
from functools import wraps
from django.core.mail import send_mail
from .models import Notification, NotificationSettings, ProUserTask, MemberProfile, CustomUser, FeatureUpdate
from projects.models import Project
from django.utils import timezone
from datetime import timedelta
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.db import models
import re

def business_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.warning(request, "You need to be logged in to access this feature.")
            request.session["show_warning_modal"] = True
            return redirect("welcome:dashboard")
        
        # Check if user is a business owner or a member of any business
        is_business_owner = request.user.subscription_type.lower() == "business"
        is_business_member = request.user.businesses.exists()
        
        if not (is_business_owner or is_business_member):
            messages.warning(request, "You need to be a business owner or member to access this feature.")
            request.session["show_warning_modal"] = True
            return redirect("welcome:dashboard")
            
        request.session["show_warning_modal"] = False
        return view_func(request, *args, **kwargs)
    return wrapper

def pro_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.warning(request, "You need to be logged in to access this feature.")
            request.session["show_warning_modal"] = True
            return redirect("welcome:dashboard")
        # Corrected condition check
        if request.user.subscription_type.lower() not in ["pro", "business"]:
            messages.warning(request, "You need a Pro subscription to access this feature.")
            request.session["show_warning_modal"] = True
            return redirect("welcome:dashboard")
        request.session["show_warning_modal"] = False
        return view_func(request, *args, **kwargs)
    return wrapper


def has_business_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.warning(request, "You need to be logged in to access this feature.")
            request.session["show_warning_modal"] = True
            return redirect("welcome:dashboard")
        # Check if user has any businesses
        if not request.user.businesses.exists():
            messages.warning(request, "You need to create a business first.")
            request.session["show_warning_modal"] = True
            return redirect("welcome:dashboard")
        request.session["show_warning_modal"] = False
        return view_func(request, *args, **kwargs)
    return wrapper

def send_notification(user, notification_type, message):
    # Create in-app notification
    if user.notification_settings.in_app_notifications:
        Notification.objects.create(
            user=user,
            notification_type=notification_type,
            message=message
        )
    
    # Send email notification
    if user.notification_settings.email_notifications:
        send_mail(
            'Checkify Notification',
            message,
            'notifications@checkify.com',
            [user.email],
            fail_silently=True,
        )

def check_due_date_reminders():
    # Get tasks with due dates in the next 24 hours
    tasks = ProUserTask.objects.filter(
        due_date__gte=timezone.now(),
        due_date__lte=timezone.now() + timedelta(hours=24),
        is_done=False
    )
    
    for task in tasks:
        if task.assigned_to and task.assigned_to.notification_settings.due_date_reminders:
            Notification.objects.create(
                user=task.assigned_to,
                notification_type='warning',
                message=f'Task "{task.task_name}" is due soon'
            )

class TaskComment(models.Model):
    task = models.ForeignKey(ProUserTask, on_delete=models.CASCADE, related_name='comments')
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    comment = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        
        # Notify the task creator and assignee
        recipients = set()
        if self.task.user:
            recipients.add(self.task.user)
        if self.task.assigned_to:
            recipients.add(self.task.assigned_to)
        
        for user in recipients:
            if user and user.notification_settings.task_comments:
                Notification.objects.create(
                    user=user,
                    notification_type='info',
                    message=f'New comment on task "{self.task.task_name}"'
                )

@receiver(post_save, sender=Project)
def handle_new_project_notification(sender, instance, created, **kwargs):
    if created:
        # Notify the team leader (project creator)
        if instance.created_by.notification_settings.new_projects:
            Notification.objects.create(
                user=instance.created_by,
                notification_type='info',
                message=f'You have created a new project: {instance.name}'
            )

        # Notify all project members
        for member in instance.members.all():
            if member.notification_settings.new_projects:
                Notification.objects.create(
                    user=member,
                    notification_type='info',
                    message=f'You have been added to a new project: {instance.name}'
                )

@receiver(post_save, sender=MemberProfile)
def handle_role_change_notification(sender, instance, created, **kwargs):
    if not created:
        try:
            original = MemberProfile.objects.get(pk=instance.pk)
            if original.role != instance.role:
                if instance.user.notification_settings.role_changes:
                    Notification.objects.create(
                        user=instance.user,
                        notification_type='info',
                        message=f'Your role has been changed to: {instance.role}'
                    )
        except MemberProfile.DoesNotExist:
            pass

def send_weekly_summary():
    # Get all users with weekly summary enabled
    users = CustomUser.objects.filter(notification_settings__weekly_summary=True)
    
    for user in users:
        # Get tasks completed in the last week
        completed_tasks = ProUserTask.objects.filter(
            assigned_to=user,
            is_done=True,
            completed_at__gte=timezone.now() - timedelta(days=7)
        )
        
        # Get upcoming tasks
        upcoming_tasks = ProUserTask.objects.filter(
            assigned_to=user,
            is_done=False,
            due_date__gte=timezone.now()
        )
        
        # Create summary message
        message = f"Weekly Summary:\n\n"
        message += f"Completed Tasks: {completed_tasks.count()}\n"
        message += f"Upcoming Tasks: {upcoming_tasks.count()}"
        
        # Send notification
        if user.notification_settings.weekly_summary:
            Notification.objects.create(
                user=user,
                notification_type='info',
                message=message
            )
            completed_at__gte=timezone.now() - timedelta(days=7)
        
        # Get upcoming tasks
        upcoming_tasks = ProUserTask.objects.filter(
            assigned_to=user,
            is_done=False,
            due_date__gte=timezone.now()
        )
        
        # Create summary message
        message = f"Weekly Summary:\n\n"
        message += f"Completed Tasks: {completed_tasks.count}\n"
        message += f"Upcoming Tasks: {upcoming_tasks.count}"
        
        # Send notification
        send_notification(user, 'info', message)


@receiver(post_save, sender=FeatureUpdate)
def handle_feature_update_notification(sender, instance, created, **kwargs):
    if created:
        users = CustomUser.objects.filter(notification_settings__feature_updates=True)
        for user in users:
            Notification.objects.create(
                user=user,
                notification_type='info',
                message=f'New feature update: {instance.title}'
            )