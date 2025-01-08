from django.urls import path
from . import views
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    # Task-related URLs
    path('create-task/', views.create_task, name='create_task'),


    # Project-related URLs
    path('create-project/', views.create_project, name='create_project'),
    path('update_task_status/<int:task_id>/', views.update_task_status, name='update_task_status'),

    # Feedback-related URLs
    path('submit-feedback/<int:task_id>/', views.submit_feedback, name='submit_feedback'),

    # Invitation-related URLs
    path('view-invitations/', views.view_invitations, name='view_invitations'),
    path('send-invitation/', views.send_invitation, name='send_invitation'),

    # Dashboard URL
    path('', views.dashboard_view, name='dashboard'),

    path('project/<int:project_id>/invite/', views.invite_team_members, name='invite_team_members'),
    path('invitation/<uuid:token>/accept/', views.accept_invitation, name='accept_invitation'),
    path('subscribe/pro/', views.subscribe_pro, name='subscribe_pro'),
    path('upload_task_file/<int:task_id>/', views.upload_task_file, name='upload_task_file'),
    path('download-task-file/<int:task_id>/', views.download_file, name='download_task_file'),
    path('export_project_files/<int:project_id>/', views.export_project_files, name='export_project_files'),
    path('tasks/', views.user_tasks_view, name='user_tasks_view'),

    path('projects/', views.user_projects_view, name='user_projects_view'),
    path('project/<int:project_id>/tasks/', views.view_project_tasks, name='view_project_tasks'),
    path('project/<int:project_id>/', views.project_detail, name='project_detail'),
    path('task/<int:task_id>/', views.task_detail, name='task_detail'),

    path('task/<int:task_id>/reassign/', views.reassign_task, name='reassign_task'),
    path('pay/', views.pay, name='pay'),
    path('payment_result/', views.payment_result, name='payment_result'),
    # Authentication URLs
    path('register/', views.register_view, name='register'),
    path('login/', views.login_view, name='login'),
    path('process_excel/', views.process_excel, name='process_excel'),
    path('get_progress/', views.get_progress, name='get_progress'),
    path('loading/', views.loading_page, name='loading_page'),  # Add the loading page URL
    path('logout/', views.logout_view, name='logout'),  # Add the logout URL
    path('add-business/', views.add_business, name='add_business'),
    path('business/<int:business_id>/members/', views.business_members_view, name='business_members'),
    path('change_user_role/<int:user_id>/', views.change_user_role, name='change_user_role'),
    path('members-dashboard/', views.members_dashboard_view, name='members_dashboard'),
    path('reset-password/', views.reset_password, name='reset_password'),
    path('process-business-data/', views.process_business_data, name='process_business_data'),
] +static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
