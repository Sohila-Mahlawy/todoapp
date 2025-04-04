from django.contrib import admin
from .models import (
    FAQ, 
    LegalDocument, 
    ContentCalendarEvent, 
    SocialMediaPost, 
    EmailCampaign, 
    CodeSnippet
)

# Register your models here.
@admin.register(FAQ)
class FAQAdmin(admin.ModelAdmin):
    list_display = ('company_name', 'product_or_service', 'created_at')
    search_fields = ('company_name', 'product_or_service')
    list_filter = ('created_at',)

@admin.register(LegalDocument)
class LegalDocumentAdmin(admin.ModelAdmin):
    list_display = ('company_name', 'document_type', 'created_at')
    search_fields = ('company_name',)
    list_filter = ('document_type', 'created_at')

@admin.register(ContentCalendarEvent)
class ContentCalendarEventAdmin(admin.ModelAdmin):
    list_display = ('title', 'content_type', 'start_date', 'end_date')
    search_fields = ('title', 'description')
    list_filter = ('content_type', 'start_date')

@admin.register(SocialMediaPost)
class SocialMediaPostAdmin(admin.ModelAdmin):
    list_display = ('platform', 'target_audience', 'created_at')
    search_fields = ('platform', 'content')
    list_filter = ('platform', 'created_at')

@admin.register(EmailCampaign)
class EmailCampaignAdmin(admin.ModelAdmin):
    list_display = ('company_name', 'campaign_goals', 'created_at')
    search_fields = ('company_name', 'content')
    list_filter = ('created_at',)

@admin.register(CodeSnippet)
class CodeSnippetAdmin(admin.ModelAdmin):
    list_display = ('language', 'task_description', 'created_at')
    search_fields = ('language', 'task_description')
    list_filter = ('language', 'created_at')
