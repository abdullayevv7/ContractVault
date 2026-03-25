"""
Analytics services for ContractVault.
Provides aggregated metrics, trend data, and compliance reporting.
"""
import logging
from collections import defaultdict
from datetime import timedelta
from decimal import Decimal

from django.db.models import Count, Sum, Avg, Q, F
from django.db.models.functions import TruncMonth, TruncWeek
from django.utils import timezone

logger = logging.getLogger(__name__)


def get_dashboard_summary(organization):
    """
    Get high-level contract statistics for an organization dashboard.

    Args:
        organization: Organization instance

    Returns:
        dict with summary metrics
    """
    from apps.contracts.models import Contract

    contracts = Contract.objects.filter(organization=organization)
    today = timezone.now().date()

    total = contracts.count()
    by_status = dict(
        contracts.values_list("status")
        .annotate(count=Count("id"))
        .values_list("status", "count")
    )

    total_value = contracts.aggregate(
        total=Sum("total_value"),
        avg=Avg("total_value"),
    )

    expiring_30 = contracts.filter(
        status=Contract.Status.ACTIVE,
        expiration_date__lte=today + timedelta(days=30),
        expiration_date__gte=today,
    ).count()

    expiring_90 = contracts.filter(
        status=Contract.Status.ACTIVE,
        expiration_date__lte=today + timedelta(days=90),
        expiration_date__gte=today,
    ).count()

    pending_approvals = contracts.filter(
        status=Contract.Status.PENDING_APPROVAL,
    ).count()

    pending_signatures = contracts.filter(
        status=Contract.Status.PENDING_SIGNATURE,
    ).count()

    return {
        "total_contracts": total,
        "by_status": by_status,
        "total_value": str(total_value["total"] or Decimal("0.00")),
        "average_value": str(total_value["avg"] or Decimal("0.00")),
        "active_contracts": by_status.get("active", 0),
        "draft_contracts": by_status.get("draft", 0),
        "expiring_in_30_days": expiring_30,
        "expiring_in_90_days": expiring_90,
        "pending_approvals": pending_approvals,
        "pending_signatures": pending_signatures,
    }


def get_contract_trends(organization, months=12):
    """
    Get monthly trend data for contract creation and value.

    Args:
        organization: Organization instance
        months: Number of months to look back

    Returns:
        list of monthly data dicts
    """
    from apps.contracts.models import Contract

    cutoff = timezone.now() - timedelta(days=months * 30)

    monthly_data = (
        Contract.objects.filter(
            organization=organization,
            created_at__gte=cutoff,
        )
        .annotate(month=TruncMonth("created_at"))
        .values("month")
        .annotate(
            count=Count("id"),
            total_value=Sum("total_value"),
        )
        .order_by("month")
    )

    results = []
    for entry in monthly_data:
        results.append({
            "month": entry["month"].strftime("%Y-%m"),
            "contracts_created": entry["count"],
            "total_value": str(entry["total_value"] or Decimal("0.00")),
        })
    return results


def get_contract_type_breakdown(organization):
    """
    Get contract distribution by type.

    Args:
        organization: Organization instance

    Returns:
        list of type breakdown dicts
    """
    from apps.contracts.models import Contract

    breakdown = (
        Contract.objects.filter(organization=organization)
        .values("contract_type__name")
        .annotate(
            count=Count("id"),
            total_value=Sum("total_value"),
            active=Count("id", filter=Q(status="active")),
        )
        .order_by("-count")
    )

    results = []
    for entry in breakdown:
        results.append({
            "type_name": entry["contract_type__name"] or "Untyped",
            "count": entry["count"],
            "total_value": str(entry["total_value"] or Decimal("0.00")),
            "active_count": entry["active"],
        })
    return results


def get_approval_metrics(organization):
    """
    Get approval workflow performance metrics.

    Args:
        organization: Organization instance

    Returns:
        dict with approval metrics
    """
    from apps.approvals.models import ApprovalRequest

    requests = ApprovalRequest.objects.filter(
        contract__organization=organization,
    )

    total = requests.count()
    if total == 0:
        return {
            "total_requests": 0,
            "approved": 0,
            "rejected": 0,
            "pending": 0,
            "approval_rate": 0.0,
            "avg_days_to_approve": None,
        }

    by_status = dict(
        requests.values_list("status")
        .annotate(count=Count("id"))
        .values_list("status", "count")
    )

    # Calculate average time to complete approval
    completed = requests.filter(
        status__in=["approved", "rejected"],
        completed_at__isnull=False,
    ).annotate(
        duration=F("completed_at") - F("created_at"),
    )

    avg_duration = None
    if completed.exists():
        total_seconds = sum(
            (r.duration.total_seconds() for r in completed),
        )
        avg_seconds = total_seconds / completed.count()
        avg_duration = round(avg_seconds / 86400, 1)  # Convert to days

    approved = by_status.get("approved", 0)
    rejected = by_status.get("rejected", 0)
    decided = approved + rejected

    return {
        "total_requests": total,
        "approved": approved,
        "rejected": rejected,
        "pending": by_status.get("in_progress", 0) + by_status.get("pending", 0),
        "approval_rate": round(approved / decided * 100, 1) if decided > 0 else 0.0,
        "avg_days_to_approve": avg_duration,
    }


def get_expiration_calendar(organization, days_ahead=90):
    """
    Get contracts expiring within the given time window, grouped by week.

    Args:
        organization: Organization instance
        days_ahead: Number of days to look ahead

    Returns:
        list of weekly groupings
    """
    from apps.contracts.models import Contract

    today = timezone.now().date()
    end_date = today + timedelta(days=days_ahead)

    weekly_data = (
        Contract.objects.filter(
            organization=organization,
            status=Contract.Status.ACTIVE,
            expiration_date__gte=today,
            expiration_date__lte=end_date,
        )
        .annotate(week=TruncWeek("expiration_date"))
        .values("week")
        .annotate(
            count=Count("id"),
            total_value=Sum("total_value"),
        )
        .order_by("week")
    )

    results = []
    for entry in weekly_data:
        results.append({
            "week_start": entry["week"].strftime("%Y-%m-%d"),
            "expiring_count": entry["count"],
            "total_value": str(entry["total_value"] or Decimal("0.00")),
        })
    return results
