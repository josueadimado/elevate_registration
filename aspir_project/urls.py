"""
URL configuration for aspir_project project.
"""
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),  # Django's default admin (optional)
    path('admin-panel/', include('registrations.admin_urls')),  # Custom admin dashboard
    path('', include('registrations.urls')),
    path('api/', include('registrations.api_urls')),
]
