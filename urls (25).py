"""
URL configuration for approvals app.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    ApprovalWorkflowViewSet,
    ApprovalStepViewSet,
    ApprovalRequestViewSet,
)

router = DefaultRouter()
router.register(r"workflows", ApprovalWorkflowViewSet, basename="approval-workflow")
router.register(r"requests", ApprovalRequestViewSet, basename="approval-request")

urlpatterns = [
    path(
        "workflows/<uuid:workflow_id>/steps/",
        ApprovalStepViewSet.as_view({"get": "list", "post": "create"}),
        name="workflow-steps",
    ),
    path(
        "workflows/<uuid:workflow_id>/steps/<uuid:id>/",
        ApprovalStepViewSet.as_view(
            {"get": "retrieve", "put": "update", "patch": "partial_update", "delete": "destroy"}
        ),
        name="workflow-step-detail",
    ),
    path("", include(router.urls)),
]
