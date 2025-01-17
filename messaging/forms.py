from django import forms
from .models import Messages
from welcome.models import CustomUser
from django.core.validators import validate_email

class MessageForm(forms.ModelForm):
    recipients = forms.CharField(
        widget=forms.TextInput(attrs={'id': 'recipients', 'data-autocomplete-url': '/autocomplete_users/', 'placeholder': 'Enter recipient emails, separated by commas.'}),
        help_text='Enter recipient emails, separated by commas.'
    )

    class Meta:
        model = Messages
        fields = ['recipients', 'subject', 'body']

    def clean_recipients(self):
        recipients_input = self.cleaned_data['recipients']
        recipients_emails = [email.strip() for email in recipients_input.split(',') if email.strip()]
        for email in recipients_emails:
            if not validate_email(email):
                raise forms.ValidationError(f"'{email}' is not a valid email address.")
        return recipients_emails