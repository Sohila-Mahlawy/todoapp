from django.db import models
from welcome.models import CustomUser

class Project(models.Model):
    name = models.CharField(max_length=255)
    created_by = models.ForeignKey(
        'welcome.CustomUser', on_delete=models.CASCADE, related_name='projects'
    )
    start_date = models.DateField()
    end_date = models.DateField()
    members = models.ManyToManyField('welcome.CustomUser', related_name='project_members')
    business = models.ForeignKey(
        'businesses.Business', on_delete=models.CASCADE, related_name='projects', null=True, blank=True
    )

    def __str__(self):
        return f"Project by {self.created_by.username}"

    # Optional utility method to retrieve all tasks
    def get_tasks(self):
        return self.tasks.all()

    

# Model for invitations
class Invitation(models.Model):
    ROLE_CHOICES = [
        ('team_member', 'Team Member'),
        ('product_owner', 'Product Owner'),
    ]
    team_leader = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='sent_invitations')
    name = models.CharField(max_length=255)
    email = models.EmailField()
    token = models.CharField(max_length=255, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    accepted = models.BooleanField(default=False)
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='invitations')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='team_member')  # Add this field

    def __str__(self):
        return f"Invitation to {self.email} for {self.project} as {self.role}"
    
