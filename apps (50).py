"""
URL configuration for notifications app.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import NotificationViewSet, NotificationPreferenceViewSet

router = DefaultRouter()
router.register(r"preferences", NotificationPreferenceViewSet, basename="notification-preference")
router.register(r"", NotificationViewSet, basename="notification")

urlpatterns = [
    path("", include(router.urls)),
]
