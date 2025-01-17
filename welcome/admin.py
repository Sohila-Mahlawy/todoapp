from django.contrib import admin
from .models import CustomUser, ProjectResult, Complaint, UnloggedUserTask, FinanceRecord, LoggedUserTask, ProUserTask, Project, TaskFeedback, Invitation, MemberProfile, Business, CallCenter
from messaging.models import Messages  # Correct import for Messages model
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.forms import UserChangeForm, UserCreationForm

class CustomUserAdmin(UserAdmin):
    model = CustomUser
    list_display = ('username', 'email', 'subscription_type', 'role', 'category', 'trial_start_date', 'is_staff')
    list_filter = ('is_staff', 'subscription_type', 'role', 'category')
    search_fields = ('username', 'email')
    ordering = ('username',)

admin.site.register(CustomUser, CustomUserAdmin)
admin.site.register(CallCenter)
admin.site.register(ProjectResult)
admin.site.register(FinanceRecord)
admin.site.register(Complaint)
admin.site.register(UnloggedUserTask)
admin.site.register(LoggedUserTask)
admin.site.register(ProUserTask)
admin.site.register(Project)
admin.site.register(TaskFeedback)
admin.site.register(Invitation)
admin.site.register(MemberProfile)
admin.site.register(Business)
