from django import forms
from .models import Project
from welcome.models import CustomUser
from businesses.models import Business
from django.forms.widgets import DateInput

class ProjectForm(forms.ModelForm):
    class Meta:
        model = Project
        fields = ['name', 'start_date', 'end_date', 'members', 'business']

    members = forms.ModelMultipleChoiceField(
        queryset=CustomUser.objects.none(),
        widget=forms.SelectMultiple,
        required=False  # Make members optional
    )
    start_date = forms.DateField(widget=DateInput(attrs={'type': 'date'}), required=False)
    end_date = forms.DateField(widget=DateInput(attrs={'type': 'date'}), required=False)
    
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        if user:
            business = Business.objects.filter(user=user).first()
            if business:
                self.fields['members'].queryset = business.members.all()

            if user.subscription_type == 'pro':
                self.fields['business'].queryset = Business.objects.filter(user=user)
                # Make business optional for pro users
                self.fields['business'].required = False