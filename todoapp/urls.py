# todoapp/urls.py
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('welcome.urls', namespace='welcome')), 
    path('', include('messaging.urls', namespace='messaging')),  # Correct import for messaging app URLs
    path('', include('projects.urls', namespace="projects" )),  # Include projects URLs with namespace
    path('', include('businesses.urls', namespace='businesses')),
    path('', include('users.urls', namespace='users')),
    path('', include('tasks.urls', namespace='tasks')),  # Include tasks URLs with namespace
    path('', include('ai_tools.urls', namespace='ai_tools')),  # AI tools app
] 
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)