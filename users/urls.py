from django.urls import path
from . import views
from django.conf import settings
from django.conf.urls.static import static

app_name = "users"


urlpatterns = [
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),  # Add the logout URL
    path('register/', views.register_view, name='register'),
    path('reset-password/', views.reset_password, name='reset_password'),
    path('profile/<int:user_id>/', views.profile, name='profile'),
    path('update_notification_settings/', views.update_notification_settings, name='update_notification_settings'),
    path('member/<int:user_id>/', views.members_details, name='member_details'),
    
]