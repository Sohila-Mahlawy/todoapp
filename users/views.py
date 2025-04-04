from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from welcome.models import UnloggedUserTask,LoggedUserTask, ProUserTask,TaskFeedback,CustomUser, SubscriptionOrder, UserProfile, MemberProfile
from projects.models import Project
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.decorators import login_required
from datetime import datetime, timedelta
from django.conf import settings
from django.utils import timezone
from django.http import HttpResponseForbidden
from django.utils.timezone import now
from django.contrib import messages
import requests
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth import update_session_auth_hash
from django.urls import reverse



# Function to handle user registration
def register_view(request):
    if request.user.is_authenticated:
        return redirect('welcome:dashboard')
    if request.method == 'POST':
        username = request.POST['username']
        email = request.POST['email']
        password1 = request.POST['password']
        password2 = request.POST['confirm_password']
        
        if password1 != password2:
            messages.error(request, "Passwords do not match!")
            return redirect('users:register')
        
        if CustomUser.objects.filter(username=username).exists():
            messages.error(request, "Username already exists!")
            return redirect('users:register')
        
        if CustomUser.objects.filter(email=email).exists():
            messages.error(request, "Email is already registered!")
            return redirect('users:register')
        
        user = CustomUser.objects.create_user(username=username, email=email, password=password1)
        user.save()

        # Log the user in after registration
        login(request, user)

        # Redirect to the dashboard
        return redirect('welcome:dashboard')  # Replace 'welcome:dashboard' with your dashboard URL name

    return render(request, 'users/sign-up.html')


# Function to handle user login
def login_view(request):
    if request.user.is_authenticated:
        return redirect('welcome:dashboard')
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(request, username=username, password=password)
            if user is not None:
                login(request, user)
                user.userprofile.logged_in_status = 'Logged In'
                user.userprofile.save()
                return redirect('welcome:members_dashboard')
    else:
        form = AuthenticationForm()
    return render(request, 'users/sign-in.html', {'form': form})

def logout_view(request):
    logout(request)  # Log out the user
    return redirect('users:login')  # Redirect to the login page after logout


@login_required
def reset_password(request):
    if request.method == 'POST':
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)  # Important!
            # Update user profile status
            user.userprofile.status = 'Activated'
            user.userprofile.save()
            return redirect('welcome:members_dashboard')  # Redirect to the members dashboard after successful password change
    else:
        form = PasswordChangeForm(request.user)
    return render(request, 'users/reset_password.html', {'form': form})
    

@login_required
def profile(request, user_id):
    # Redirect to the dashboard if the user_id does not match the logged-in user's ID
    if request.user.id != user_id:
        return redirect('users:member_details', user_id=user_id)

    from messaging.models import Messages
    # Fetch the user object
    user = get_object_or_404(CustomUser, id=user_id)
    
    # Fetch the member profile associated with the user
    member_profile = getattr(user, 'profile', None)  # Use related_name "profile"
    
    # Fetch all projects created by the user
    projects = Project.objects.filter(created_by=user)
    last_messages = Messages.objects.filter(recipients=request.user)\
                                    .order_by('-created_at')[:5]

    # Pass the user, their projects, and their member profile to the template
    return render(
        request,
        'users/profile.html',
        {'user': user, 'projects': projects, 'member_profile': member_profile ,'messages': last_messages}
    )

@login_required
def update_notification_settings(request):
    if request.method == 'POST':
        try:
            # Use the get_notification_settings method
            settings = request.user.get_notification_settings()
            # Update all settings from the form data
            settings.task_assignments = request.POST.get('taskAssignments') == 'on'
            settings.due_date_reminders = request.POST.get('dueDateReminders') == 'on'
            settings.task_comments = request.POST.get('taskComments') == 'on'
            settings.new_projects = request.POST.get('newProjects') == 'on'
            settings.task_updates = request.POST.get('taskUpdates') == 'on'
            settings.role_changes = request.POST.get('roleChanges') == 'on'
            settings.push_notifications = request.POST.get('pushNotifications') == 'on'
            settings.sms_notifications = request.POST.get('smsNotifications') == 'on'
            settings.in_app_notifications = request.POST.get('inAppNotifications') == 'on'
            settings.task_completion = request.POST.get('taskCompletion') == 'on'
            settings.mentions = request.POST.get('mentions') == 'on'
            settings.weekly_summary = request.POST.get('weeklySummary') == 'on'
            settings.feature_updates = request.POST.get('featureUpdates') == 'on'
            
            settings.save()
            return JsonResponse({'success': 'Notification settings updated successfully!'})
        except Exception as e:
            return JsonResponse({'error': f'Error updating settings: {str(e)}'}, status=400)
    else:
        return JsonResponse({'error': 'Invalid request method'}, status=405)
    
@login_required
def members_details(request, user_id):
    # Fetch the user object or return a 404 if it doesn't exist
    user = get_object_or_404(CustomUser, id=user_id)
    
    # Pass the user object to the template
    return render(request, 'users/members_details.html', {'user': user})  # Note: changed from member_details.html to members_details.html