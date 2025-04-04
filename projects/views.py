from django.shortcuts import render,redirect,get_object_or_404
from welcome.models import CustomUser
from .models import Project,Invitation
from .forms import ProjectForm
from django.core.mail import send_mail
from django.db import IntegrityError
from django.contrib.auth.decorators import login_required
import uuid
from django.urls import reverse
from django.conf import settings
from django.contrib import messages
from django.http import HttpResponseForbidden
from django.utils import timezone
import zipfile
from django.http import HttpResponse
import os
from businesses.models import Business
from welcome.utils import pro_required

@pro_required
@login_required
def create_project(request):
    if request.method == 'POST':
        form = ProjectForm(request.POST, user=request.user)
        if form.is_valid():
            project = form.save(commit=False)
            project.created_by = request.user
            
            # For pro users, only save the name and redirect
            if request.user.subscription_type == 'pro':
                project.save()
                return redirect('projects:invite_team_members', project_id=project.id)
            
            # For regular users, continue with the existing logic
            if request.user.businesses.exists():
                project.business = request.user.businesses.first()

            # Set default dates if not provided and ensure end_date is after start_date
            if not project.start_date:
                project.start_date = timezone.now().date()

            if not project.end_date:
                project.end_date = project.start_date + timezone.timedelta(days=30)
            elif project.end_date < project.start_date:
                form.add_error('end_date', "End date cannot be before the start date.")
                return render(request, 'projects/create_project.html', {'form': form})

            project.save()
            form.save_m2m()
            return redirect('projects:project_detail', project_id=project.id)
        else:
            print("Form Errors:", form.errors)
    else:
        form = ProjectForm(user=request.user)

    return render(request, 'projects/create_project.html', {'form': form})



@login_required
def invite_team_members(request, project_id):
    project = get_object_or_404(Project, id=project_id)

    # Ensure only the project creator can invite members
    if request.user != project.created_by:
        return redirect('project_detail', project_id=project.id)

    if request.method == 'POST':
        email = request.POST.get("email")
        role = request.POST.get("role")

        if email and role:
            try:
                # Validate email format
                if not is_valid_email(email):
                    return render(request, 'projects/add_team_members.html', {
                        'project': project,
                        'error_message': "Invalid email format"
                    })

                # Check if user already exists
                user, created = CustomUser.objects.get_or_create(
                    email=email,
                    defaults={"username": email.split("@")[0]}
                )

                # Check for existing invitations using filter()
                existing_invitations = Invitation.objects.filter(
                    email=email,
                    project=project
                )

                if existing_invitations.exists():
                    return render(request, 'projects/add_team_members.html', {
                        'project': project,
                        'error_message': "This email has already been invited to the project."
                    })

                # Create new invitation
                token = str(uuid.uuid4())
                Invitation.objects.create(
                    email=email,
                    project=project,
                    team_leader=request.user,
                    token=token,
                    role=role
                )

                # Send invitation email
                try:
                    send_mail(
                        subject="You're Invited to Join a Project!",
                        message=f"Hi,\n\nYou've been invited by {request.user.username} to join their project.\n\nClick the link below to accept the invitation:\n{request.build_absolute_uri(reverse('projects:accept_invitation', kwargs={'token': token}))}\n\nThanks!",
                        from_email=settings.DEFAULT_FROM_EMAIL,
                        recipient_list=[email],
                    )
                    return render(request, 'projects/invitation_sent.html', {
                        'email': email,
                        'project': project
                    })
                except Exception as e:
                    # Delete the invitation if email sending fails
                    Invitation.objects.filter(token=token).delete()
                    return render(request, 'projects/add_team_members.html', {
                        'project': project,
                        'error_message': f"Failed to send invitation: {str(e)}"
                    })

            except IntegrityError as e:
                return render(request, 'projects/add_team_members.html', {
                    'project': project,
                    'error_message': f"An error occurred: {str(e)}"
                })

    return render(request, 'projects/add_team_members.html', {'project': project})

def is_valid_email(email):
    """Helper function to validate email format without recursion"""
    from django.core.validators import validate_email
    from django.core.exceptions import ValidationError
    try:
        validate_email(email)
        return True
    except ValidationError:
        return False
    
@pro_required
def send_invitation(team_leader, email, token, request):
    # Use reverse to generate the URL for accepting the invitation
    invitation_link = request.build_absolute_uri(reverse('projects:accept_invitation', kwargs={'token': token}))
    send_mail(
        subject="You're Invited to Join a Project!",
        message=f"Hi,\n\nYou've been invited by {team_leader.username} to join their project.\n\nClick the link below to accept the invitation:\n{invitation_link}\n\nThanks!",
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[email],
    )

@pro_required
def generate_unique_token():
    import uuid
    return str(uuid.uuid4())

@pro_required
@login_required
def send_invitation(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        email = request.POST.get('email')
        project_id = request.POST.get('project_id')
        project = get_object_or_404(Project, id=project_id, created_by=request.user)

        invitation = Invitation.objects.create(
            team_leader=request.user,
            name=name,
            email=email,
            token=generate_unique_token(),
            project=project
        )
        return render(request, 'invitation_sent.html', {'invitation': invitation})

    projects = Project.objects.filter(created_by=request.user)
    return render(request, 'send_invitation.html', {'projects': projects})

# Function to view invitations
@login_required
def view_invitations(request):
    invitations = Invitation.objects.filter(team_leader=request.user)
    return render(request, 'invitations.html', {'invitations': invitations})


@login_required
def accept_invitation(request, token):
    # Retrieve the invitation
    invitation = get_object_or_404(Invitation, token=token, accepted=False)

    # Add the logged-in user to the project's members
    project = invitation.project
    if request.user not in project.members.all():  # Avoid duplicate additions
        project.members.add(request.user)
    else:
        messages.warning(request, "You are already a member of this project.")

    # Check the role specified in the invitation
    if invitation.role == 'product_owner':
        # Assign "Product Owner" permissions (if applicable) or simply acknowledge
        messages.success(request, "You have joined the project as the Product Owner.")
    elif invitation.role == 'team_member':
        # Acknowledge the user as a team member
        messages.success(request, "You have joined the project as a Team Member.")

    # Mark the invitation as accepted
    invitation.accepted = True
    invitation.save()

    return render(request, 'projects/invitation_accepted.html', {'project': project})

@login_required
def project_detail(request, project_id):
    # Fetch the project or return a 404 if it doesn't exist
    project = get_object_or_404(Project, id=project_id)

    # Ensure the user is either the project creator or a member of the project
    if request.user != project.created_by and request.user not in project.members.all():
        return HttpResponseForbidden("You do not have permission to view this project.")

    # Fetch tasks related to this project and prefetch feedback
    tasks = project.tasks.all().prefetch_related('feedback')

    # Debugging output to confirm task query results
    print(f"Tasks for project {project_id}: {tasks}")

    # Render the project details page
    return render(request, 'projects/project_detail.html', {
        'project': project,
        'tasks': tasks,
        'members': project.members.all()
    })

@pro_required
def user_projects_view(request):
    """
    Fetch projects related to the authenticated user and render the 'tab-panel.html' template.
    """
    user = request.user

    # Fetch projects created by the user and projects where the user is a member
    created_projects = Project.objects.filter(created_by=user)
    member_projects = Project.objects.filter(members=user)

    # Combine QuerySets into a Python list and remove duplicates
    user_projects = list(created_projects) + list(member_projects)
    unique_projects = {project.id: project for project in user_projects}.values()  # Deduplicate by project ID

    # Calculate completion percentages for each project
    project_data = []
    for project in unique_projects:
        total_tasks = project.tasks.count()
        completed_tasks = project.tasks.filter(is_done=True).count()
        completion_percentage = int((completed_tasks / total_tasks) * 100) if total_tasks > 0 else 0
        project_data.append({
            'project': project,
            'completion_percentage': completion_percentage
        })

    # Context data for the template
    context = {
        'project_data': project_data,
        'members_count': sum(project.members.count() for project in unique_projects)
    }

    return render(request, 'projects/projects.html', context)

@pro_required
def view_project_tasks(request, project_id):
    project = get_object_or_404(Project, id=project_id)

    # Ensure the user is the Product Owner of the project

    # Fetch all tasks related to this project
    tasks = project.tasks.all()

    return render(request, 'projects/project_tasks.html', {
        'project': project,
        'tasks': tasks,
    })

@pro_required
def export_project_files(request, project_id):
    # Fetch the project and associated tasks
    project = get_object_or_404(Project, id=project_id)
    tasks = project.tasks.all()

    # Define a temporary zip file location
    zip_filename = f"{project.name}_files.zip"
    temp_dir = os.path.join(settings.MEDIA_ROOT, 'temp')
    os.makedirs(temp_dir, exist_ok=True)
    zip_path = os.path.join(temp_dir, zip_filename)

    # Create the zip file
    with zipfile.ZipFile(zip_path, 'w') as zip_file:
        for task in tasks:
            if task.uploaded_file and os.path.exists(task.uploaded_file.path):
                file_path = task.uploaded_file.path
                file_name = os.path.basename(file_path)
                # Add the file under a folder named after the task
                zip_file.write(file_path, arcname=f"{task.task_name}/{file_name}")

    # Serve the zip file as a downloadable response
    with open(zip_path, 'rb') as zip_file:
        response = HttpResponse(zip_file.read(), content_type='application/zip')
        response['Content-Disposition'] = f'attachment; filename="{zip_filename}"'

    # Clean up the temporary file
    os.remove(zip_path)

    return response
