"""
URL configuration for signatures app.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import SignatureRequestViewSet

router = DefaultRouter()
router.register(r"", SignatureRequestViewSet, basename="signature-request")

urlpatterns = [
    path("", include(router.urls)),
]
