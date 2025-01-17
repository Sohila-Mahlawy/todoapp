from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.core.exceptions import ValidationError
from .models import CustomUser, Project, CallCenter

class CustomUserCreationForm(UserCreationForm):
    class Meta:
        model = CustomUser
        fields = ['username', 'email', 'password1', 'password2']

    def __init__(self, *args, **kwargs):
        super(CustomUserCreationForm, self).__init__(*args, **kwargs)
        for fieldname in ['username', 'email', 'password1', 'password2']:
            self.fields[fieldname].help_text = None
        self.fields['email'].required = True


class ProjectForm(forms.ModelForm):
    class Meta:
        model = Project
        fields = ['name','start_date', 'end_date']  # Include 'start_date' if it's not already

    # Optionally, you can set default values or widgets for 'start_date'
    start_date = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}), required=True)


class CallCenterForm(forms.ModelForm):
    class Meta:
        model = CallCenter
        fields = ['zip_file']  # Only include the zip_file field

    def clean_zip_file(self):
        zip_file = self.cleaned_data.get('zip_file')
        if zip_file:
            # Check the file size (in bytes)
            max_size = 512 * 1024  # 512 KB
            if zip_file.size > max_size:
                raise ValidationError("Maximum size is 512 KB.")
        return zip_file


