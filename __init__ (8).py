"""
Amendment models: Amendment, AmendmentClause.
Tracks formal modifications to executed contracts.
"""
import uuid

from django.conf import settings
from django.db import models


class Amendment(models.Model):
    """
    A formal amendment to an existing active contract.
    Amendments go through their own approval and signature lifecycle.
    """

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        PENDING_APPROVAL = "pending_approval", "Pending Approval"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"
        PENDING_SIGNATURE = "pending_signature", "Pending Signature"
        EXECUTED = "executed", "Executed"
        CANCELLED = "cancelled", "Cancelled"

    class AmendmentType(models.TextChoices):
        MODIFICATION = "modification", "Term Modification"
        ADDENDUM = "addendum", "Addendum"
        EXTENSION = "extension", "Extension"
        REDUCTION = "reduction", "Scope Reduction"
        FINANCIAL = "financial", "Financial Adjustment"
        TERMINATION = "termination", "Early Termination"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    contract = models.ForeignKey(
        "contracts.Contract",
        on_delete=models.CASCADE,
        related_name="contract_amendments",
    )
    amendment_number = models.CharField(max_length=50, unique=True)
    title = models.CharField(max_length=500)
    description = models.TextField(blank=True, default="")
    amendment_type = models.CharField(
        max_length=20,
        choices=AmendmentType.choices,
        default=AmendmentType.MODIFICATION,
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT,
        db_index=True,
    )
    reason = models.TextField(
        help_text="Business justification for the amendment",
    )

    # Financial impact
    previous_value = models.DecimalField(
        max_digits=15, decimal_places=2, null=True, blank=True,
        help_text="Contract value before this amendment",
    )
    new_value = models.DecimalField(
        max_digits=15, decimal_places=2, null=True, blank=True,
        help_text="Contract value after this amendment",
    )

    # Date changes
    previous_expiration = models.DateField(null=True, blank=True)
    new_expiration = models.DateField(null=True, blank=True)

    effective_date = models.DateField(
        null=True, blank=True,
        help_text="When this amendment takes effect",
    )
    document = models.FileField(
        upload_to="amendments/documents/", null=True, blank=True,
    )

    changes_summary = models.JSONField(
        default=list,
        help_text="Structured list of changes: [{field, old_value, new_value}]",
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="created_amendments",
    )
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="approved_amendments",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    executed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["contract", "status"]),
        ]

    def __str__(self):
        return f"{self.amendment_number} - {self.title}"

    def save(self, *args, **kwargs):
        if not self.amendment_number:
            self.amendment_number = self._generate_amendment_number()
        super().save(*args, **kwargs)

    def _generate_amendment_number(self):
        existing = Amendment.objects.filter(contract=self.contract).count()
        return f"{self.contract.contract_number}-AMD-{existing + 1:03d}"

    @property
    def value_change(self):
        if self.previous_value is not None and self.new_value is not None:
            return self.new_value - self.previous_value
        return None


class AmendmentClause(models.Model):
    """
    Individual clause changes within an amendment.
    Tracks which clauses are added, modified, or removed.
    """

    class ChangeType(models.TextChoices):
        ADDED = "added", "Added"
        MODIFIED = "modified", "Modified"
        REMOVED = "removed", "Removed"
        UNCHANGED = "unchanged", "Unchanged (for reference)"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    amendment = models.ForeignKey(
        Amendment,
        on_delete=models.CASCADE,
        related_name="clause_changes",
    )
    original_clause = models.ForeignKey(
        "contracts.ContractClause",
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="amendment_changes",
        help_text="Reference to the original clause being modified",
    )
    change_type = models.CharField(
        max_length=20,
        choices=ChangeType.choices,
    )
    title = models.CharField(max_length=255)
    original_content = models.TextField(
        blank=True, default="",
        help_text="Content before amendment (for modified/removed)",
    )
    new_content = models.TextField(
        blank=True, default="",
        help_text="Content after amendment (for added/modified)",
    )
    order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["order"]

    def __str__(self):
        return f"{self.get_change_type_display()}: {self.title}"
