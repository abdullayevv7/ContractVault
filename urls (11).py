"""
URL configuration for amendments app.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import AmendmentViewSet

router = DefaultRouter()
router.register(r"", AmendmentViewSet, basename="amendment")

urlpatterns = [
    path("", include(router.urls)),
]
