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
    path('plans', views.plans, name='plans'),
    path('calendar/', views.calendar, name='calendar'),
    path('add_event/', views.add_event, name='add_event'),
    path('get_events/', views.get_events, name='get_events'),
    path('notifications/', views.notification_list, name='notifications_list'),
    path('search_suggestions/', views.search_suggestions, name='search_suggestions'),
    path('faq/', views.faq_view, name='faq'),
    path('clear_warning_modal/', views.clear_warning_modal, name='clear_warning_modal'),
    path('update_event/', views.update_event, name='update_event'),
    path('delete_event/', views.delete_event, name='delete_event'),
    path('update-ui-settings/', views.update_ui_settings, name='update_ui_settings'),
    path('mark-notification-read/', views.mark_notification_read, name='mark_notification_read'),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
