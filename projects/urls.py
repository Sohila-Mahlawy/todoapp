from django.urls import path
from . import views

app_name = 'projects'  # Define the namespace for the tasks app


urlpatterns = [
    path('create-project/', views.create_project, name='create_project'),
    path('project/<int:project_id>/invite/', views.invite_team_members, name='invite_team_members'),
    path('accept-invitation/<str:token>/', views.accept_invitation, name='accept_invitation'),
    path('view-invitations/', views.view_invitations, name='view_invitations'),
    path('send-invitation/', views.send_invitation, name='send_invitation'),
    path('projects/', views.user_projects_view, name='user_projects_view'),
    path('project/<int:project_id>/tasks/', views.view_project_tasks, name='view_project_tasks'),
    path('project/<int:project_id>/', views.project_detail, name='project_detail'),
    path('export_project_files/<int:project_id>/', views.export_project_files, name='export_project_files'),
]