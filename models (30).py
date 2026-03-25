"""
Compliance models: ComplianceRule, ComplianceCheck, ComplianceReport.
Tracks regulatory and policy compliance for contracts.
"""
import uuid

from django.conf import settings
from django.db import models


class ComplianceRule(models.Model):
    """
    Defines a compliance requirement that contracts must satisfy.
    Rules can be organisation-wide or scoped to specific contract types.
    """

    class RuleCategory(models.TextChoices):
        REGULATORY = "regulatory", "Regulatory"
        POLICY = "policy", "Internal Policy"
        FINANCIAL = "financial", "Financial Control"
        DATA_PRIVACY = "data_privacy", "Data Privacy"
        SECURITY = "security", "Security"
        LEGAL = "legal", "Legal Requirement"

    class Severity(models.TextChoices):
        LOW = "low", "Low"
        MEDIUM = "medium", "Medium"
        HIGH = "high", "High"
        CRITICAL = "critical", "Critical"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        "accounts.Organization",
        on_delete=models.CASCADE,
        related_name="compliance_rules",
    )
    name = models.CharField(max_length=255)
    description = models.TextField()
    category = models.CharField(
        max_length=20,
        choices=RuleCategory.choices,
    )
    severity = models.CharField(
        max_length=10,
        choices=Severity.choices,
        default=Severity.MEDIUM,
    )
    contract_type = models.ForeignKey(
        "contracts.ContractType",
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="compliance_rules",
        help_text="If set, this rule only applies to contracts of this type",
    )
    check_function = models.CharField(
        max_length=255,
        help_text="Dotted path to the Python function that validates this rule",
    )
    parameters = models.JSONField(
        default=dict, blank=True,
        help_text="Parameters passed to the check function",
    )
    is_active = models.BooleanField(default=True)
    effective_date = models.DateField(
        null=True, blank=True,
        help_text="Date from which this rule is enforceable",
    )
    expiration_date = models.DateField(
        null=True, blank=True,
        help_text="Date after which this rule no longer applies",
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="created_compliance_rules",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-severity", "name"]

    def __str__(self):
        return f"[{self.get_category_display()}] {self.name}"


class ComplianceCheck(models.Model):
    """
    Result of running a compliance rule against a specific contract.
    Created each time compliance is evaluated.
    """

    class Result(models.TextChoices):
        PASS = "pass", "Pass"
        FAIL = "fail", "Fail"
        WARNING = "warning", "Warning"
        SKIPPED = "skipped", "Skipped"
        ERROR = "error", "Error"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    contract = models.ForeignKey(
        "contracts.Contract",
        on_delete=models.CASCADE,
        related_name="compliance_checks",
    )
    rule = models.ForeignKey(
        ComplianceRule,
        on_delete=models.CASCADE,
        related_name="checks",
    )
    result = models.CharField(
        max_length=10,
        choices=Result.choices,
        db_index=True,
    )
    message = models.TextField(
        blank=True, default="",
        help_text="Human-readable explanation of the check result",
    )
    details = models.JSONField(
        default=dict, blank=True,
        help_text="Machine-readable check details",
    )
    checked_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        help_text="User who triggered the check, or null for automated",
    )
    checked_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-checked_at"]
        indexes = [
            models.Index(fields=["contract", "result"]),
        ]

    def __str__(self):
        return f"{self.rule.name} - {self.get_result_display()} ({self.contract.contract_number})"


class ComplianceReport(models.Model):
    """
    A point-in-time compliance report for an organization.
    Aggregates all compliance checks run during a reporting period.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        "accounts.Organization",
        on_delete=models.CASCADE,
        related_name="compliance_reports",
    )
    title = models.CharField(max_length=255)
    period_start = models.DateField()
    period_end = models.DateField()
    total_contracts_checked = models.PositiveIntegerField(default=0)
    total_checks_run = models.PositiveIntegerField(default=0)
    passed = models.PositiveIntegerField(default=0)
    failed = models.PositiveIntegerField(default=0)
    warnings = models.PositiveIntegerField(default=0)
    compliance_score = models.DecimalField(
        max_digits=5, decimal_places=2, default=0,
        help_text="Percentage score (0-100)",
    )
    summary = models.JSONField(
        default=dict, blank=True,
        help_text="Breakdown by category, severity, etc.",
    )
    generated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.title} ({self.period_start} - {self.period_end})"
