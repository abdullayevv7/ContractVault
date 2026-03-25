"""
Views for the analytics app.
Provides read-only endpoints for dashboard metrics and reporting.
"""
import logging

from rest_framework.response import Response
from rest_framework.views import APIView

from .services import (
    get_dashboard_summary,
    get_contract_trends,
    get_contract_type_breakdown,
    get_approval_metrics,
    get_expiration_calendar,
)

logger = logging.getLogger(__name__)


class DashboardSummaryView(APIView):
    """Get high-level dashboard metrics for the user's organization."""

    def get(self, request):
        user = request.user
        if not user.organization:
            return Response({"error": "No organization assigned."}, status=400)

        summary = get_dashboard_summary(user.organization)
        return Response(summary)


class ContractTrendsView(APIView):
    """Get monthly contract creation and value trends."""

    def get(self, request):
        user = request.user
        if not user.organization:
            return Response({"error": "No organization assigned."}, status=400)

        months = int(request.query_params.get("months", 12))
        months = min(max(months, 1), 36)  # Clamp to 1-36

        trends = get_contract_trends(user.organization, months)
        return Response(trends)


class ContractTypeBreakdownView(APIView):
    """Get contract distribution by type."""

    def get(self, request):
        user = request.user
        if not user.organization:
            return Response({"error": "No organization assigned."}, status=400)

        breakdown = get_contract_type_breakdown(user.organization)
        return Response(breakdown)


class ApprovalMetricsView(APIView):
    """Get approval workflow performance metrics."""

    def get(self, request):
        user = request.user
        if not user.organization:
            return Response({"error": "No organization assigned."}, status=400)

        metrics = get_approval_metrics(user.organization)
        return Response(metrics)


class ExpirationCalendarView(APIView):
    """Get upcoming contract expirations grouped by week."""

    def get(self, request):
        user = request.user
        if not user.organization:
            return Response({"error": "No organization assigned."}, status=400)

        days = int(request.query_params.get("days", 90))
        days = min(max(days, 7), 365)

        calendar = get_expiration_calendar(user.organization, days)
        return Response(calendar)
