from .models import Messages
from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.core.exceptions import ValidationError
from welcome.models import CustomUser  # Correct import for CustomUser

class MessageForm(forms.ModelForm):
    recipients = forms.ModelMultipleChoiceField(
        queryset=CustomUser.objects.all(),
        widget=forms.CheckboxSelectMultiple
    )

    class Meta:
        model = Messages
        fields = ['recipients', 'subject', 'body']