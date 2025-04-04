from django.urls import path
from . import views

app_name = 'messaging'  # Define the namespace for the tasks app


urlpatterns = [
    path('send_message/', views.send_message, name='send_message'),
    path('view_messages/', views.view_messages, name='view_messages'),
    path('search_users/', views.search_users, name='search_users'),
    path('autocomplete_users/', views.autocomplete_users, name='autocomplete_users'),
    path('generate_email/', views.generate_email, name='generate_email'),

]