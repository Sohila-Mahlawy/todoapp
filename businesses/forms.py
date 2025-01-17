from django import forms
from .models import CallCenter
from django.core.exceptions import ValidationError



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