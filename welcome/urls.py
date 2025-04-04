from django.urls import path
from . import views
from django.conf import settings
from django.conf.urls.static import static

app_name = 'welcome'  # Define the namespace for the tasks app

urlpatterns = [
    path('', views.dashboard_view, name='dashboard'),
    path('subscribe-pro/', views.subscribe_pro, name='subscribe_pro'),
    path('pay_paymob/', views.pay_paymob, name='pay_paymob'),
    path('pay/', views.pay, name='pay'),
    path('stripe-webhook/', views.stripe_webhook, name='stripe_webhook'),
    path('payment-success/', views.payment_success, name='payment_success'),
    path('payment_result/', views.payment_result, name='payment_result'),
    path('members-dashboard/', views.members_dashboard_view, name='members_dashboard'),
    path('help/', views.help, name='help'),
    path('generate-terms/', views.generate_terms, name='generate_terms'),
    path('generate-agreement/', views.generate_agreement, name='generate_agreement'),
    path('generate-forecast/', views.generate_forecast, name='generate_forecast'),
    path('generate-schedule/', views.generate_schedule, name='generate_schedule'),
    path('generate-code/', views.generate_code, name='generate_code'),
    path('generate-faq/', views.generate_faq, name='generate_faq'),
    path('generate-social-post/', views.generate_social_post, name='generate_social_post'),
    path('generate-email-campaign/', views.generate_email_campaign, name='generate_email_campaign'),
    path('generate-blog-ideas/', views.generate_blog_ideas, name='generate_blog_ideas'),
    path('generate-role-steps/', views.generate_role_steps, name='generate_role_steps'),
    path('generate-onboarding-steps/', views.generate_onboarding_steps, name='generate_onboarding_steps'),
    path('generate-marketing-copy/', views.generate_marketing_copy, name='generate_marketing_copy'),
    path('generate-product-description/', views.generate_product_description, name='generate_product_description'),
    path('plans', views.plans, name='plans'),
    path('calendar/', views.calendar, name='calendar'),
    path('generate_content_calendar/', views.generate_content_calendar, name='generate_content_calendar'),
    path('add_event/', views.add_event, name='add_event'),
    path('get_events/', views.get_events, name='get_events'),
    path('ai-tools/', views.ai_tools, name='ai_tools'),
    path('notifications/', views.notification_list, name='notifications_list'),
    path('search_suggestions/', views.search_suggestions, name='search_suggestions'),
    path('faq/', views.faq_view, name='faq'),
    path('clear_warning_modal/', views.clear_warning_modal, name='clear_warning_modal'),
    path('calendar/update/<int:event_id>/', views.update_event, name='update_event'),
    path('calendar/delete/<int:event_id>/', views.delete_event, name='delete_event'),
    path('update-ui-settings/', views.update_ui_settings, name='update_ui_settings'),
    path('mark-notification-read/', views.mark_notification_read, name='mark_notification_read'),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
