"""
Serializers for the compliance app.
"""
from rest_framework import serializers

from .models import ComplianceRule, ComplianceCheck, ComplianceReport


class ComplianceRuleSerializer(serializers.ModelSerializer):
    category_display = serializers.CharField(
        source="get_category_display", read_only=True,
    )
    severity_display = serializers.CharField(
        source="get_severity_display", read_only=True,
    )

    class Meta:
        model = ComplianceRule
        fields = [
            "id", "organization", "name", "description",
            "category", "category_display", "severity", "severity_display",
            "contract_type", "check_function", "parameters",
            "is_active", "effective_date", "expiration_date",
            "created_by", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class ComplianceCheckSerializer(serializers.ModelSerializer):
    rule_name = serializers.CharField(
        source="rule.name", read_only=True,
    )
    rule_category = serializers.CharField(
        source="rule.category", read_only=True,
    )
    rule_severity = serializers.CharField(
        source="rule.severity", read_only=True,
    )
    contract_number = serializers.CharField(
        source="contract.contract_number", read_only=True,
    )
    result_display = serializers.CharField(
        source="get_result_display", read_only=True,
    )

    class Meta:
        model = ComplianceCheck
        fields = [
            "id", "contract", "contract_number",
            "rule", "rule_name", "rule_category", "rule_severity",
            "result", "result_display", "message", "details",
            "checked_by", "checked_at",
        ]
        read_only_fields = ["id", "checked_at"]


class ComplianceReportSerializer(serializers.ModelSerializer):
    generated_by_name = serializers.CharField(
        source="generated_by.get_full_name", read_only=True, default="",
    )

    class Meta:
        model = ComplianceReport
        fields = [
            "id", "organization", "title", "period_start", "period_end",
            "total_contracts_checked", "total_checks_run",
            "passed", "failed", "warnings", "compliance_score",
            "summary", "generated_by", "generated_by_name",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]


class RunComplianceCheckSerializer(serializers.Serializer):
    """Input for running compliance checks on a single contract."""
    contract_id = serializers.UUIDField()
