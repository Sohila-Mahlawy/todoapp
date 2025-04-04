from django.db import models
from django.conf import settings

# Create your models here.
class AIGeneratedContent(models.Model):
    """Base model for AI generated content"""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        abstract = True

class FAQ(AIGeneratedContent):
    """Model for storing generated FAQs"""
    company_name = models.CharField(max_length=255)
    product_or_service = models.CharField(max_length=255)
    common_questions = models.TextField()
    generated_faq = models.TextField()
    
    def __str__(self):
        return f"FAQ for {self.company_name} - {self.created_at.strftime('%Y-%m-%d')}"

class LegalDocument(AIGeneratedContent):
    """Model for storing generated legal documents like terms and agreements"""
    company_name = models.CharField(max_length=255)
    document_type = models.CharField(max_length=100, choices=[
        ('terms', 'Terms and Conditions'),
        ('agreement', 'Legal Agreement'),
        ('policy', 'Privacy Policy')
    ])
    content = models.TextField()
    
    def __str__(self):
        return f"{self.document_type} for {self.company_name}"

class ContentCalendarEvent(AIGeneratedContent):
    """Model for content calendar events"""
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    start_date = models.DateField()
    end_date = models.DateField()
    content_type = models.CharField(max_length=100)
    
    def __str__(self):
        return self.title

class SocialMediaPost(AIGeneratedContent):
    """Model for storing generated social media posts"""
    platform = models.CharField(max_length=100)
    target_audience = models.CharField(max_length=255)
    campaign_goal = models.CharField(max_length=255)
    content = models.TextField()
    
    def __str__(self):
        return f"{self.platform} post - {self.created_at.strftime('%Y-%m-%d')}"

class EmailCampaign(AIGeneratedContent):
    """Model for storing generated email campaigns"""
    company_name = models.CharField(max_length=255)
    campaign_goals = models.CharField(max_length=255)
    target_audience = models.CharField(max_length=255)
    content = models.TextField()
    
    def __str__(self):
        return f"Email Campaign for {self.company_name} - {self.created_at.strftime('%Y-%m-%d')}"

class CodeSnippet(AIGeneratedContent):
    """Model for storing generated code snippets"""
    language = models.CharField(max_length=100)
    task_description = models.TextField()
    code = models.TextField()
    
    def __str__(self):
        return f"{self.language} code - {self.created_at.strftime('%Y-%m-%d')}"
