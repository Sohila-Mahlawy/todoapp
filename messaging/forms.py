from django import forms
from .models import Messages
from welcome.models import CustomUser
from django.core.validators import validate_email
from django.core.exceptions import ValidationError

class MessageForm(forms.ModelForm):
    recipients = forms.CharField(
        widget=forms.TextInput(attrs={
            'id': 'recipients',
            'data-autocomplete-url': '/autocomplete_users/',
            'placeholder': 'Enter recipient emails, separated by commas.'
        }),
        help_text='Enter recipient emails, separated by commas.'
    )

    class Meta:
        model = Messages
        fields = ['recipients', 'subject', 'body']

    def clean_recipients(self):
        recipients_input = self.cleaned_data['recipients']
        recipients_emails = [email.strip() for email in recipients_input.split(',') if email.strip()]

        # Validate each email
        for email in recipients_emails:
            try:
                validate_email(email)
            except ValidationError:
                raise forms.ValidationError(f"'{email}' is not a valid email address.")

        # Check if all recipient emails correspond to existing users
        recipients = CustomUser.objects.filter(email__in=recipients_emails)
        if recipients.count() != len(recipients_emails):
            invalid_emails = set(recipients_emails) - set(recipients.values_list('email', flat=True))
            raise forms.ValidationError(f"The following emails do not correspond to existing users: {', '.join(invalid_emails)}")

        return recipients