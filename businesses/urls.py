from django.urls import path
from . import views

urlpatterns = [
    path('add-business/', views.add_business, name='add_business'),
    path('business/<int:business_id>/members/', views.business_members_view, name='business_members'),
    path('process-business-data/', views.process_business_data, name='process_business_data'),
    path('upload_call_center/', views.upload_call_center, name='upload_call_center'),
    path('upload_finance/', views.upload_finance, name='upload_finance'),
    path('finance_records/', views.finance_records_list, name='finance_records_list'),
    path("complain/", views.submit_complaint, name="submit_complaint"),
    path('api/<int:business_id>/', views.api, name='api'),
    path('buisness/<int:business_id>', views.business_members_view, name='user_detail'),
    path('member/<int:member_id>/', views.member_detail, name='member_detail'),
    path('change_user_role/<int:user_id>/', views.change_user_role, name='change_user_role'),
    path('business/<int:business_id>/members/', views.business_members_view, name='business_members'),
    path('process_excel/', views.process_excel, name='process_excel'),
    path('get_progress/', views.get_progress, name='get_progress'),
    path('loading/', views.loading_page, name='loading_page'),  # Add the loading page URL
]