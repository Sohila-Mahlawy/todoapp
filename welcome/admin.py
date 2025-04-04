from django.contrib import admin
from .models import FAQ,CustomUser,UnloggedUserTask, UserProfile,Notification ,CalendarEvent,LoggedUserTask, ProUserTask,TaskFeedback,MemberProfile,SubscriptionOrder, UISettings
from messaging.models import Messages  # Correct import for Messages model
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.forms import UserChangeForm, UserCreationForm

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import Group, Permission
from .models import CustomUser,NotificationSettings  # Adjust the import based on your project structure

class CustomUserAdmin(UserAdmin):
    model = CustomUser

    # Fields to display in the list view
    list_display = (
        'username', 'email', 'subscription_type', 'role', 'category', 
        'trial_start_date', 'pro_subscription_date', 'subscription_end_date', 'is_staff'
    )

    # Filters available in the right sidebar
    list_filter = (
        'is_staff', 'is_superuser', 'is_active', 'subscription_type', 'role', 'category', 
        'groups'
    )

    # Search fields for quick filtering
    search_fields = ('username', 'email')

    # Ordering of records in the list view
    ordering = ('username',)

    # Fields to display in the add form
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': (
                'username', 'email', 'password1', 'password2', 'subscription_type', 
                'role', 'category', 'trial_start_date', 'pro_subscription_date', 
                'subscription_end_date', 'is_staff', 'is_active', 'groups', 'user_permissions'
            ),
        }),
    )

    # Fields to display in the change form
    fieldsets = (
        ('Authentication', {'fields': ('username', 'password')}),
        ('Personal Info', {'fields': ('email',)}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Subscription Details', {
            'fields': (
                'subscription_type', 'role', 'category', 'trial_start_date', 
                'pro_subscription_date', 'subscription_end_date'
            )
        }),
        ('Important Dates', {'fields': ('last_login', 'date_joined')}),
    )

admin.site.register(CustomUser, CustomUserAdmin)
admin.site.register(UnloggedUserTask)
admin.site.register(LoggedUserTask)
admin.site.register(ProUserTask)
admin.site.register(TaskFeedback)
admin.site.register(MemberProfile)
admin.site.register(SubscriptionOrder)
admin.site.register(CalendarEvent)
admin.site.register(Notification)
admin.site.register(UserProfile)
admin.site.register(FAQ)
admin.site.register(NotificationSettings)
admin.site.register(UISettings)