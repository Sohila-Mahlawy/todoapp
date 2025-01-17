from django.urls import path
from . import views

urlpatterns = [
    path('send_message/', views.send_message, name='send_message'),
    path('view_messages/', views.view_messages, name='view_messages'),
    path('search_users/', views.search_users, name='search_users'),
]