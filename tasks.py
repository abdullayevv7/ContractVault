"""
URL configuration for compliance app.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    ComplianceRuleViewSet,
    ComplianceCheckViewSet,
    RunComplianceChecksView,
    ComplianceReportViewSet,
)

router = DefaultRouter()
router.register(r"rules", ComplianceRuleViewSet, basename="compliance-rule")
router.register(r"checks", ComplianceCheckViewSet, basename="compliance-check")
router.register(r"reports", ComplianceReportViewSet, basename="compliance-report")

urlpatterns = [
    path("run-checks/", RunComplianceChecksView.as_view(), name="run-compliance-checks"),
    path("", include(router.urls)),
]
