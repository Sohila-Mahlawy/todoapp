from django.urls import path
from . import views
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    # Task-related URLs
    path('create-task/', views.create_task, name='create_task'),
    path('update_task_status/<int:task_id>/', views.update_task_status, name='update_task_status'),

    # Feedback-related URLs
    path('submit-feedback/<int:task_id>/', views.submit_feedback, name='submit_feedback'),
    # Dashboard URL
    path('', views.dashboard_view, name='dashboard'),
    path('subscribe/pro/', views.subscribe_pro, name='subscribe_pro'),
    path('upload_task_file/<int:task_id>/', views.upload_task_file, name='upload_task_file'),
    path('download-task-file/<int:task_id>/', views.download_file, name='download_task_file'),
    path('tasks/', views.user_tasks_view, name='user_tasks_view'),
    path('task/<int:task_id>/', views.task_detail, name='task_detail'),
    path('task/<int:task_id>/reassign/', views.reassign_task, name='reassign_task'),
    path('pay/', views.pay, name='pay'),
    path('payment_result/', views.payment_result, name='payment_result'),
    path('register/', views.register_view, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),  # Add the logout URL
    path('members-dashboard/', views.members_dashboard_view, name='members_dashboard'),
    path('reset-password/', views.reset_password, name='reset_password'),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
