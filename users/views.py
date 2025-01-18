from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from welcome.models import UnloggedUserTask,LoggedUserTask, ProUserTask,TaskFeedback,CustomUser, SubscriptionOrder, UserProfile
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
    if request.method == 'POST':
        username = request.POST['username']
        email = request.POST['email']
        password1 = request.POST['password']
        password2 = request.POST['confirm_password']
        
        if password1 != password2:
            messages.error(request, "Passwords do not match!")
            return redirect('register')
        
        if CustomUser.objects.filter(username=username).exists():
            messages.error(request, "Username already exists!")
            return redirect('register')
        
        if CustomUser.objects.filter(email=email).exists():
            messages.error(request, "Email is already registered!")
            return redirect('register')
        
        user = CustomUser.objects.create_user(username=username, email=email, password=password1)
        user.save()

    return render(request, 'register.html')


# Function to handle user login
def login_view(request):
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
                return redirect('members_dashboard')
    else:
        form = AuthenticationForm()
    return render(request, 'login.html', {'form': form})

def logout_view(request):
    logout(request)  # Log out the user
    return redirect('login')  # Redirect to the login page after logout


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
            return redirect('members_dashboard')  # Redirect to the members dashboard after successful password change
    else:
        form = PasswordChangeForm(request.user)
    return render(request, 'reset_password.html', {'form': form})
    


@login_required
def user_detail(request, user_id):
    user = get_object_or_404(CustomUser, id=user_id)
    return render(request, 'user_detail.html', {'user': user})