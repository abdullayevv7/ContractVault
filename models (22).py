"""
Approval models: ApprovalWorkflow, ApprovalStep, ApprovalRequest.
"""
import uuid

from django.conf import settings
from django.db import models


class ApprovalWorkflow(models.Model):
    """
    Defines an approval workflow with ordered steps.
    Workflows can be associated with contract types.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        "accounts.Organization",
        on_delete=models.CASCADE,
        related_name="approval_workflows",
    )
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, default="")
    contract_type = models.ForeignKey(
        "contracts.ContractType",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="workflows",
        help_text="If set, this workflow applies to contracts of this type",
    )
    is_active = models.BooleanField(default=True)
    is_default = models.BooleanField(
        default=False,
        help_text="If true, this is the default workflow for the organization",
    )
    min_value_threshold = models.DecimalField(
        max_digits=15, decimal_places=2, null=True, blank=True,
        help_text="Minimum contract value to trigger this workflow",
    )
    max_value_threshold = models.DecimalField(
        max_digits=15, decimal_places=2, null=True, blank=True,
        help_text="Maximum contract value for this workflow",
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="created_workflows",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name

    @property
    def step_count(self):
        return self.steps.count()


class ApprovalStep(models.Model):
    """
    Individual step in an approval workflow.
    Steps are ordered and each has an assigned approver or role.
    """

    class StepType(models.TextChoices):
        SINGLE = "single", "Single Approver"
        ANY = "any", "Any One of Group"
        ALL = "all", "All of Group"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workflow = models.ForeignKey(
        ApprovalWorkflow,
        on_delete=models.CASCADE,
        related_name="steps",
    )
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, default="")
    order = models.PositiveIntegerField()
    step_type = models.CharField(
        max_length=10, choices=StepType.choices, default=StepType.SINGLE
    )
    approver = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="approval_steps",
        help_text="Specific user approver (for single type)",
    )
    approver_role = models.ForeignKey(
        "accounts.Role",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="approval_steps",
        help_text="Role-based approver (any user with this role can approve)",
    )
    auto_approve_after_hours = models.PositiveIntegerField(
        null=True, blank=True,
        help_text="Auto-approve after this many hours if no action taken",
    )
    is_required = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["order"]
        unique_together = ["workflow", "order"]

    def __str__(self):
        return f"{self.workflow.name} - Step {self.order}: {self.name}"


class ApprovalRequest(models.Model):
    """
    An instance of a contract going through an approval workflow.
    Tracks current step and overall status.
    """

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        IN_PROGRESS = "in_progress", "In Progress"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"
        CANCELLED = "cancelled", "Cancelled"
        ESCALATED = "escalated", "Escalated"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    contract = models.ForeignKey(
        "contracts.Contract",
        on_delete=models.CASCADE,
        related_name="approval_requests",
    )
    workflow = models.ForeignKey(
        ApprovalWorkflow,
        on_delete=models.CASCADE,
        related_name="requests",
    )
    current_step = models.ForeignKey(
        ApprovalStep,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="current_requests",
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True,
    )
    submitted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="submitted_approvals",
    )
    notes = models.TextField(blank=True, default="")
    decision_history = models.JSONField(
        default=list,
        help_text="History of approval/rejection decisions",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Approval for {self.contract.contract_number} - {self.status}"
