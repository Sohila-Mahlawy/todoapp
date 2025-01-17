from django.contrib.auth.models import AbstractUser, Group, Permission
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from welcome.models import CustomUser  # Replace 'yourapp' with the actual app name where CustomUser is defined

# Create your models here.
class Messages(models.Model):
    sender = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='sent_messages')
    recipients = models.ManyToManyField(CustomUser, related_name='received_messages')
    subject = models.CharField(max_length=255)
    body = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Message from {self.sender.email} to {', '.join([user.email for user in self.recipients.all()])}"

    class Meta:
        app_label = 'messaging'