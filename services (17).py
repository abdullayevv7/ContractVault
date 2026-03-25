"""
URL configuration for analytics app.
"""
from django.urls import path

from .views import (
    DashboardSummaryView,
    ContractTrendsView,
    ContractTypeBreakdownView,
    ApprovalMetricsView,
    ExpirationCalendarView,
)

urlpatterns = [
    path("dashboard/", DashboardSummaryView.as_view(), name="analytics-dashboard"),
    path("trends/", ContractTrendsView.as_view(), name="analytics-trends"),
    path("type-breakdown/", ContractTypeBreakdownView.as_view(), name="analytics-type-breakdown"),
    path("approval-metrics/", ApprovalMetricsView.as_view(), name="analytics-approval-metrics"),
    path("expiration-calendar/", ExpirationCalendarView.as_view(), name="analytics-expiration-calendar"),
]
