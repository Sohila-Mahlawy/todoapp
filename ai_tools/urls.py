from django.urls import path
from . import views

app_name = 'ai_tools'

urlpatterns = [
    path('ai-tools/', views.ai_tools_dashboard, name='dashboard'),
    path('ai-tools/help/', views.help, name='help'),
    path('ai-tools/generate-terms/', views.generate_terms, name='generate_terms'),
    path('ai-tools/generate-agreement/', views.generate_agreement, name='generate_agreement'),
    path('ai-tools/generate-forecast/', views.generate_forecast, name='generate_forecast'),
    path('ai-tools/generate-schedule/', views.generate_schedule, name='generate_schedule'),
    path('ai-tools/generate-code/', views.generate_code, name='generate_code'),
    path('ai-tools/generate-faq/', views.generate_faq, name='generate_faq'),
    path('ai-tools/generate-social-post/', views.generate_social_post, name='generate_social_post'),
    path('ai-tools/generate-email-campaign/', views.generate_email_campaign, name='generate_email_campaign'),
    path('ai-tools/generate-blog-ideas/', views.generate_blog_ideas, name='generate_blog_ideas'),
    path('ai-tools/generate-role-steps/', views.generate_role_steps, name='generate_role_steps'),
    path('ai-tools/generate-onboarding-steps/', views.generate_onboarding_steps, name='generate_onboarding_steps'),
    path('ai-tools/generate-marketing-copy/', views.generate_marketing_copy, name='generate_marketing_copy'),
    path('ai-tools/generate-product-description/', views.generate_product_description, name='generate_product_description'),
    path('ai-tools/generate-content-calendar/', views.generate_content_calendar, name='generate_content_calendar'),
] 