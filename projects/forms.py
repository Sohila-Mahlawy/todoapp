from django import forms
from .models import Project


class ProjectForm(forms.ModelForm):
    class Meta:
        model = Project
        fields = ['name','start_date', 'end_date']  # Include 'start_date' if it's not already

    # Optionally, you can set default values or widgets for 'start_date'
    start_date = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}), required=True)