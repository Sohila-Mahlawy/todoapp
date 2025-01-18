from django.urls import path
from . import views
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    # Task-related URLs

    # Feedback-related URLs
    # Dashboard URL
    path('', views.dashboard_view, name='dashboard'),
    path('subscribe/pro/', views.subscribe_pro, name='subscribe_pro'),
    path('pay/', views.pay, name='pay'),
    path('payment_result/', views.payment_result, name='payment_result'),
    path('members-dashboard/', views.members_dashboard_view, name='members_dashboard'),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
