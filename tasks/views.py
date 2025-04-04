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
from welcome.models import SubscriptionOrder
import uuid
import requests
from django.contrib import messages
from django.shortcuts import redirect
from django.conf import settings
from welcome.models import SubscriptionOrder
from django.http import HttpResponse, Http404
import os
from django.views.decorators.csrf import csrf_exempt
from welcome.utils import pro_required
from welcome.models import NotificationSettings
from django.db.models import Q

@csrf_exempt
def update_task_status(request, task_id):
    if request.method == "POST":
        try:
            task = None
            if request.user.is_authenticated:
                # For authenticated users, try all possible task types
                try:
                    if request.user.subscription_type.lower() in ['pro', 'business']:
                        # Allow both task creator and assigned user to update the task
                        task = ProUserTask.objects.get(
                            Q(id=task_id, user=request.user) | Q(id=task_id, assigned_to=request.user)
                        )
                    else:
                        # For regular logged users, check both created and assigned tasks
                        task = LoggedUserTask.objects.filter(
                            id=task_id,
                            user=request.user
                        ).first() or ProUserTask.objects.filter(
                            id=task_id,
                            assigned_to=request.user
                        ).first()
                except (ProUserTask.DoesNotExist, LoggedUserTask.DoesNotExist):
                    pass
            else:
                # For unauthenticated users
                client_ip = get_client_ip(request)
                try:
                    task = UnloggedUserTask.objects.get(id=task_id, ip_address=client_ip)
                except UnloggedUserTask.DoesNotExist:
                    pass

            if task is None:
                return JsonResponse({
                    'status': 'error',
                    'message': 'Task not found or you do not have permission to update it'
                }, status=404)

            # Update the task status
            task.is_done = not task.is_done
            task.save()

            # Return the updated status
            return JsonResponse({
                'status': 'success',
                'is_done': task.is_done,
                'message': 'Task status updated successfully'
            })

        except Exception as e:
            print(f"Error updating task {task_id}: {str(e)}")
            return JsonResponse({
                'status': 'error',
                'message': 'An error occurred while updating the task'
            }, status=500)

    return JsonResponse({
        'status': 'error',
        'message': 'Invalid request method'
    }, status=400)

def create_task(request):
    if request.method == 'POST':
        task_name = request.POST.get('task_name')
        assigned_to_id = request.POST.get('assigned_to')
        due_date_str = request.POST.get('due_date')

        due_date = None
        if due_date_str:
            try:
                naive_due_date = datetime.strptime(due_date_str, '%Y-%m-%dT%H:%M')
                due_date = timezone.make_aware(naive_due_date)
            except (ValueError, TypeError):
                pass

        assigned_to = None
        if assigned_to_id:
            assigned_to = CustomUser.objects.get(id=assigned_to_id)

        if request.user.is_authenticated:
            if request.user.subscription_type.lower() in ['pro', 'business']:
                # Pro user task creation
                project_id = request.POST.get('project_id')
                project = get_object_or_404(Project, id=project_id) if project_id else None
                assigned_to = CustomUser.objects.get(id=assigned_to_id) if assigned_to_id else None

                task = ProUserTask.objects.create(
                    user=request.user,
                    task_name=task_name,
                    project=project,
                    assigned_to=assigned_to,
                    due_date=due_date  # Add due_date

                )
                return redirect('welcome:dashboard')
            else:
                # Free logged-in user task creation
                task = LoggedUserTask.objects.create(
                    user=request.user,
                    task_name=task_name,
                    due_date=due_date
                )
                return redirect('welcome:dashboard')
        else:
            # For unlogged user task creation
            ip_address = get_client_ip(request)
            task = UnloggedUserTask.objects.create(
                ip_address=ip_address,
                task_name=task_name,
                due_date=due_date
            )
            return redirect('welcome:dashboard')  # Fixed redirect URL

    # Handle AJAX request to fetch project members
    if request.method == 'GET' and request.headers.get('x-requested-with') == 'XMLHttpRequest':
        project_id = request.GET.get('project_id')
        if project_id:
            project = get_object_or_404(Project, id=project_id)
            members = [{'id': member.id, 'username': member.username} for member in project.members.all()]
            return JsonResponse(members, safe=False)

    # For GET request, provide the project list for pro users and members for assignment
    if request.user.is_authenticated and request.user.subscription_type.lower() in ['pro', 'business']:
        from businesses.models import Business
        businesses = Business.objects.filter(members=request.user)
        projects = Project.objects.filter(created_by=request.user)
        members = CustomUser.objects.none()
        return render(request, 'tasks/create_task.html', {'projects': projects, 'members': members})

    return render(request, 'tasks/create_task.html')




# Function to submit feedback for a task
@login_required
def submit_feedback(request, task_id):
    task = get_object_or_404(ProUserTask, id=task_id, user=request.user)
    if request.method == 'POST':
        feedback_text = request.POST.get('feedback')
        feedback = TaskFeedback.objects.create(task=task, feedback=feedback_text)
        return render(request, 'feedback_submitted.html', {'feedback': feedback})
    return render(request, 'submit_feedback.html', {'task': task})


# Function to get client IP address
def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


@login_required
def upload_task_file(request, task_id):
    try:
        # Allow both task creator and assigned user to upload files
        task = ProUserTask.objects.get(
            Q(id=task_id, user=request.user) | Q(id=task_id, assigned_to=request.user)
        )
        
        if request.method == 'POST' and request.FILES.get('file'):
            uploaded_file = request.FILES['file']
            task.uploaded_file = uploaded_file
            task.save()
            return JsonResponse({'message': 'File uploaded successfully'})
        
        return JsonResponse({
            'error': 'No file provided',
            'message': 'Please select a file to upload'
        }, status=400)
            
    except ProUserTask.DoesNotExist:
        return JsonResponse({
            'error': 'Task not found',
            'message': 'Task not found or you do not have permission to upload files'
        }, status=404)
    except Exception as e:
        print(f"Error uploading file for task {task_id}: {str(e)}")
        return JsonResponse({
            'error': str(e),
            'message': 'An error occurred while uploading the file'
        }, status=500)


def download_file(request, task_id):
    # Get the task instance
    task = get_object_or_404(ProUserTask, id=task_id)
    
    # Check if the task has an uploaded file
    if not task.uploaded_file:
        raise Http404("No file found for this task.")

    # Construct the full file path
    file_path = os.path.join(settings.MEDIA_ROOT, task.uploaded_file.name)

    # Check if the file exists
    if not os.path.exists(file_path):
        raise Http404("File not found on the server.")

    # Serve the file as a response
    with open(file_path, 'rb') as file:
        response = HttpResponse(file.read(), content_type='application/octet-stream')
        response['Content-Disposition'] = f'attachment; filename="{os.path.basename(file_path)}"'
        return response
    
def user_tasks_view(request):
    """
    Fetch tasks for a user based on their authentication and subscription status
    and render the 'tasks.html' template.
    """
    user = request.user
    context = {}

    if user.is_authenticated:
        if user.subscription_type.lower() in ['pro', 'business']:
            # Fetch Pro user tasks
            pro_tasks = ProUserTask.objects.filter(user=user)
            context['tasks'] = pro_tasks
        else:
            # Fetch tasks directly created by the free user
            user_tasks = LoggedUserTask.objects.filter(user=user)

            # Fetch tasks assigned to the free user by Pro users
            assigned_tasks = ProUserTask.objects.filter(assigned_to=user)

            # Combine the tasks into a single list
            context['tasks'] = list(user_tasks) + list(assigned_tasks)

        # Add user subscription type to context
        context['is_pro_user'] = user.subscription_type == 'pro' or "Pro" or "Business" or "business"
    else:
        # Handle unlogged users
        ip_address = get_client_ip(request)  # Fetch the IP address of the user
        unlogged_tasks = UnloggedUserTask.objects.filter(ip_address=ip_address)
        context['tasks'] = unlogged_tasks
        context['is_pro_user'] = False  # Not a logged-in user

    return render(request, 'tasks/tables.html', context)

@login_required
def task_detail(request, task_id):
    task = get_object_or_404(ProUserTask, id=task_id)
    project = task.project

    # Ensure that the current user is the project leader
    if project.created_by != request.user:
        return HttpResponseForbidden("You are not authorized to manage tasks for this project.")

    # Handle feedback submission (approve or refuse)
    if request.method == "POST":
        action = request.POST.get('action')
        feedback_text = request.POST.get('feedback')

        if action == "approve":
            # Approve the task and mark it as done
            task_feedback, created = TaskFeedback.objects.get_or_create(task=task)
            task_feedback.approved = True
            task_feedback.feedback = feedback_text
            task_feedback.save()

            # Mark the task as done
            task.is_done = True
            task.save()

        elif action == "refuse":
            # Refuse the task and save feedback
            task_feedback, created = TaskFeedback.objects.get_or_create(task=task)
            task_feedback.approved = False
            task_feedback.feedback = feedback_text
            task_feedback.save()

            # Task remains not done
            task.is_done = False
            task.save()

            # Delete the uploaded file if it exists
            if task.uploaded_file:
                task.uploaded_file.delete()

        return redirect('projects:project_detail', project_id=project.id)

    # Get the current feedback for the task (if any)
    feedback = TaskFeedback.objects.filter(task=task).first()

    return redirect('projects:project_detail', project_id=project.id)

@pro_required
@login_required
def reassign_task(request, task_id):
    # Fetch the task
    task = get_object_or_404(ProUserTask, id=task_id)

    if request.method == 'POST':
        # Get the new assignee's ID from the form
        new_assignee_id = request.POST.get('assigned_to')
        new_assignee = get_object_or_404(CustomUser, id=new_assignee_id)

        # Validate that the new assignee is a member of the project
        if new_assignee not in task.project.members.all():
            return HttpResponseForbidden("The selected user is not a member of this project.")

        # Ensure notification settings exist for the new assignee
        NotificationSettings.objects.get_or_create(user=new_assignee)

        # Reassign the task
        task.assigned_to = new_assignee
        task.save()

        # Redirect to the project detail page
        return redirect('projects:project_detail', project_id=task.project.id)

    # Fetch the project members for the dropdown
    project_members = task.project.members.all()
    
    # Ensure all project members have notification settings
    for member in project_members:
        NotificationSettings.objects.get_or_create(user=member)
    
    return render(request, 'reassign_task.html', {
        'task': task,
        'project_members': project_members,
    })








