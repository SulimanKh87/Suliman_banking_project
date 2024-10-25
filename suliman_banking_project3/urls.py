from django.contrib import admin  # Import the admin module
from django.urls import path, include  # Import path and include from django.urls
from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi

# Configure the schema view for API documentation
schema_view = get_schema_view(
    openapi.Info(
        title="Banking API",
        default_version='v1',
        description="API documentation for the Banking Management System",
        terms_of_service="https://www.google.com/policies/terms/",
        contact=openapi.Contact(email="contact@bankapi.local"),
        license=openapi.License(name="BSD License"),
    ),
    public=True,
    permission_classes=[permissions.AllowAny],
)

# Define URL patterns for the project
urlpatterns = [
    path('admin/', admin.site.urls),
    # Include URLs from the core app
    path('api/', include('core.urls')),
    # API docs
    path('swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),  # Swagger UI for
    # ReDoc for API docs
    path('redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),
]
