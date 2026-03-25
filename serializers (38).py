"""
Contract models: Contract, ContractType, ContractVersion, ContractParty, ContractClause.
"""
import uuid

from django.conf import settings
from django.db import models


class ContractType(models.Model):
    """Categorize contracts by type (NDA, MSA, SOW, etc.)."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        "accounts.Organization",
        on_delete=models.CASCADE,
        related_name="contract_types",
    )
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, default="")
    prefix = models.CharField(
        max_length=10,
        help_text="Prefix used in contract numbers, e.g. NDA, MSA",
    )
    requires_approval = models.BooleanField(default=True)
    requires_signature = models.BooleanField(default=True)
    default_duration_days = models.PositiveIntegerField(
        null=True, blank=True,
        help_text="Default contract duration in days",
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]
        unique_together = ["organization", "name"]

    def __str__(self):
        return self.name


class Contract(models.Model):
    """Core contract model with full lifecycle tracking."""

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        PENDING_APPROVAL = "pending_approval", "Pending Approval"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"
        PENDING_SIGNATURE = "pending_signature", "Pending Signature"
        ACTIVE = "active", "Active"
        EXPIRED = "expired", "Expired"
        TERMINATED = "terminated", "Terminated"
        RENEWED = "renewed", "Renewed"
        ARCHIVED = "archived", "Archived"

    class Priority(models.TextChoices):
        LOW = "low", "Low"
        MEDIUM = "medium", "Medium"
        HIGH = "high", "High"
        CRITICAL = "critical", "Critical"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        "accounts.Organization",
        on_delete=models.CASCADE,
        related_name="contracts",
    )
    contract_number = models.CharField(max_length=50, unique=True)
    title = models.CharField(max_length=500)
    description = models.TextField(blank=True, default="")
    contract_type = models.ForeignKey(
        ContractType,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="contracts",
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT,
        db_index=True,
    )
    priority = models.CharField(
        max_length=10,
        choices=Priority.choices,
        default=Priority.MEDIUM,
    )
    total_value = models.DecimalField(
        max_digits=15, decimal_places=2, null=True, blank=True
    )
    currency = models.CharField(max_length=3, default="USD")

    effective_date = models.DateField(null=True, blank=True)
    expiration_date = models.DateField(null=True, blank=True)
    termination_date = models.DateField(null=True, blank=True)
    renewal_date = models.DateField(null=True, blank=True)
    auto_renew = models.BooleanField(default=False)
    renewal_period_days = models.PositiveIntegerField(null=True, blank=True)

    document = models.FileField(
        upload_to="contracts/documents/", null=True, blank=True
    )
    pdf_file = models.FileField(
        upload_to="contracts/pdfs/", null=True, blank=True
    )

    version = models.PositiveIntegerField(default=1)
    parent_contract = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="amendments",
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="created_contracts",
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="updated_contracts",
    )

    compliance_requirements = models.JSONField(default=list, blank=True)
    tags = models.JSONField(default=list, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status", "organization"]),
            models.Index(fields=["expiration_date"]),
            models.Index(fields=["contract_number"]),
        ]

    def __str__(self):
        return f"{self.contract_number} - {self.title}"

    def save(self, *args, **kwargs):
        if not self.contract_number:
            self.contract_number = self._generate_contract_number()
        super().save(*args, **kwargs)

    def _generate_contract_number(self):
        prefix = "CV"
        if self.contract_type and self.contract_type.prefix:
            prefix = self.contract_type.prefix

        last_contract = (
            Contract.objects.filter(
                organization=self.organization,
                contract_number__startswith=prefix,
            )
            .order_by("-contract_number")
            .first()
        )

        if last_contract:
            try:
                last_num = int(last_contract.contract_number.split("-")[-1])
                new_num = last_num + 1
            except (ValueError, IndexError):
                new_num = 1
        else:
            new_num = 1

        return f"{prefix}-{new_num:06d}"

    @property
    def is_expired(self):
        if self.expiration_date:
            from django.utils import timezone
            return self.expiration_date < timezone.now().date()
        return False

    @property
    def days_until_expiration(self):
        if self.expiration_date:
            from django.utils import timezone
            delta = self.expiration_date - timezone.now().date()
            return delta.days
        return None


class ContractVersion(models.Model):
    """Track version history of contracts."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    contract = models.ForeignKey(
        Contract, on_delete=models.CASCADE, related_name="versions"
    )
    version_number = models.PositiveIntegerField()
    title = models.CharField(max_length=500)
    description = models.TextField(blank=True, default="")
    content_snapshot = models.JSONField(
        default=dict,
        help_text="Snapshot of all contract data at this version",
    )
    document = models.FileField(
        upload_to="contracts/versions/", null=True, blank=True
    )
    change_summary = models.TextField(blank=True, default="")
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-version_number"]
        unique_together = ["contract", "version_number"]

    def __str__(self):
        return f"{self.contract.contract_number} v{self.version_number}"


class ContractParty(models.Model):
    """Parties involved in a contract."""

    class PartyRole(models.TextChoices):
        OWNER = "owner", "Contract Owner"
        COUNTERPARTY = "counterparty", "Counterparty"
        WITNESS = "witness", "Witness"
        GUARANTOR = "guarantor", "Guarantor"
        BENEFICIARY = "beneficiary", "Beneficiary"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    contract = models.ForeignKey(
        Contract, on_delete=models.CASCADE, related_name="parties"
    )
    name = models.CharField(max_length=255)
    email = models.EmailField(blank=True, default="")
    phone = models.CharField(max_length=20, blank=True, default="")
    organization_name = models.CharField(max_length=255, blank=True, default="")
    role = models.CharField(
        max_length=20, choices=PartyRole.choices, default=PartyRole.COUNTERPARTY
    )
    address = models.TextField(blank=True, default="")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="contract_participations",
    )
    is_primary = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-is_primary", "name"]
        verbose_name_plural = "Contract parties"

    def __str__(self):
        return f"{self.name} ({self.get_role_display()}) - {self.contract.contract_number}"


class ContractClause(models.Model):
    """Individual clauses within a contract."""

    class ClauseType(models.TextChoices):
        STANDARD = "standard", "Standard"
        NEGOTIABLE = "negotiable", "Negotiable"
        MANDATORY = "mandatory", "Mandatory"
        OPTIONAL = "optional", "Optional"
        CUSTOM = "custom", "Custom"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    contract = models.ForeignKey(
        Contract, on_delete=models.CASCADE, related_name="clauses"
    )
    title = models.CharField(max_length=255)
    content = models.TextField()
    clause_type = models.CharField(
        max_length=20, choices=ClauseType.choices, default=ClauseType.STANDARD
    )
    order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    parent_clause = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="sub_clauses",
    )
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["order", "created_at"]

    def __str__(self):
        return f"{self.title} ({self.contract.contract_number})"
