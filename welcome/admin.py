from django.contrib import admin
from .models import CustomUser, UnloggedUserTask, LoggedUserTask, ProUserTask, Project, TaskFeedback, Invitation,MemberProfile,Business

# Register the CustomUser model (since it's a custom user model, we use UserAdmin for it)
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.forms import UserChangeForm, UserCreationForm

class CustomUserAdmin(UserAdmin):
    model = CustomUser
    # The fields to be used in displaying the model.
    # These can be modified to customize the fields that will be shown in the admin panel.
    list_display = ('username', 'email', 'subscription_type', 'role', 'category', 'trial_start_date', 'is_staff')
    list_filter = ('is_staff', 'subscription_type', 'role', 'category')
    search_fields = ('username', 'email')
    ordering = ('username',)

# Register the CustomUser model with the custom admin
admin.site.register(CustomUser, CustomUserAdmin)

# Register the other models
admin.site.register(UnloggedUserTask)
admin.site.register(LoggedUserTask)
admin.site.register(ProUserTask)
admin.site.register(Project)
admin.site.register(TaskFeedback)
admin.site.register(Invitation)
admin.site.register(MemberProfile)
admin.site.register(Business)
