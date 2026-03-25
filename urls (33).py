"""
Views for the compliance app.
"""
import logging
from datetime import date

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import ComplianceRule, ComplianceCheck, ComplianceReport
from .serializers import (
    ComplianceRuleSerializer,
    ComplianceCheckSerializer,
    ComplianceReportSerializer,
    RunComplianceCheckSerializer,
)
from .services import run_all_checks_for_contract, generate_compliance_report

logger = logging.getLogger(__name__)


class ComplianceRuleViewSet(viewsets.ModelViewSet):
    """CRUD for compliance rules."""

    serializer_class = ComplianceRuleSerializer
    lookup_field = "id"

    def get_queryset(self):
        user = self.request.user
        if user.is_superuser:
            return ComplianceRule.objects.all()
        if user.organization:
            return ComplianceRule.objects.filter(organization=user.organization)
        return ComplianceRule.objects.none()

    def perform_create(self, serializer):
        serializer.save(
            organization=self.request.user.organization,
            created_by=self.request.user,
        )


class ComplianceCheckViewSet(viewsets.ReadOnlyModelViewSet):
    """Read-only access to compliance check results."""

    serializer_class = ComplianceCheckSerializer
    lookup_field = "id"

    def get_queryset(self):
        user = self.request.user
        qs = ComplianceCheck.objects.select_related(
            "contract", "rule", "checked_by",
        )

        contract_id = self.request.query_params.get("contract")
        if contract_id:
            qs = qs.filter(contract_id=contract_id)

        result = self.request.query_params.get("result")
        if result:
            qs = qs.filter(result=result)

        if user.is_superuser:
            return qs
        if user.organization:
            return qs.filter(contract__organization=user.organization)
        return qs.none()


class RunComplianceChecksView(APIView):
    """Run all applicable compliance checks on a contract."""

    def post(self, request):
        serializer = RunComplianceCheckSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        from apps.contracts.models import Contract
        try:
            contract = Contract.objects.get(
                id=serializer.validated_data["contract_id"],
            )
        except Contract.DoesNotExist:
            return Response(
                {"error": "Contract not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        checks = run_all_checks_for_contract(contract, request.user)
        results = ComplianceCheckSerializer(checks, many=True).data

        summary = {
            "total": len(checks),
            "pass": sum(1 for c in checks if c.result == "pass"),
            "fail": sum(1 for c in checks if c.result == "fail"),
            "warning": sum(1 for c in checks if c.result == "warning"),
            "error": sum(1 for c in checks if c.result == "error"),
        }

        return Response({
            "summary": summary,
            "checks": results,
        })


class ComplianceReportViewSet(viewsets.ReadOnlyModelViewSet):
    """Read-only access to compliance reports, plus generation."""

    serializer_class = ComplianceReportSerializer
    lookup_field = "id"

    def get_queryset(self):
        user = self.request.user
        if user.is_superuser:
            return ComplianceReport.objects.all()
        if user.organization:
            return ComplianceReport.objects.filter(
                organization=user.organization,
            )
        return ComplianceReport.objects.none()

    @action(detail=False, methods=["post"])
    def generate(self, request):
        """Generate a new compliance report for the organization."""
        user = request.user
        if not user.organization:
            return Response(
                {"error": "No organization assigned."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        period_start = request.data.get("period_start")
        period_end = request.data.get("period_end")

        if not period_start or not period_end:
            return Response(
                {"error": "period_start and period_end are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            ps = date.fromisoformat(period_start)
            pe = date.fromisoformat(period_end)
        except ValueError:
            return Response(
                {"error": "Invalid date format. Use YYYY-MM-DD."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        report = generate_compliance_report(user.organization, ps, pe, user)
        return Response(
            ComplianceReportSerializer(report).data,
            status=status.HTTP_201_CREATED,
        )
