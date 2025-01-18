from django.urls import path
from . import views
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('create-task/', views.create_task, name='create_task'),
    path('update_task_status/<int:task_id>/', views.update_task_status, name='update_task_status'),
    path('submit-feedback/<int:task_id>/', views.submit_feedback, name='submit_feedback'),
    path('upload_task_file/<int:task_id>/', views.upload_task_file, name='upload_task_file'),
    path('download-task-file/<int:task_id>/', views.download_file, name='download_task_file'),
    path('tasks/', views.user_tasks_view, name='user_tasks_view'),
    path('task/<int:task_id>/', views.task_detail, name='task_detail'),
    path('task/<int:task_id>/reassign/', views.reassign_task, name='reassign_task'),
]