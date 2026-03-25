"""
Template models: ContractTemplate, TemplateField, TemplateClause.
"""
import uuid

from django.conf import settings
from django.db import models


class ContractTemplate(models.Model):
    """
    Reusable contract templates that can be used to generate new contracts.
    Templates contain variable fields that get filled in during contract creation.
    """

    class Category(models.TextChoices):
        NDA = "nda", "Non-Disclosure Agreement"
        MSA = "msa", "Master Service Agreement"
        SOW = "sow", "Statement of Work"
        EMPLOYMENT = "employment", "Employment Agreement"
        LEASE = "lease", "Lease Agreement"
        PURCHASE = "purchase", "Purchase Agreement"
        LICENSING = "licensing", "Licensing Agreement"
        PARTNERSHIP = "partnership", "Partnership Agreement"
        OTHER = "other", "Other"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        "accounts.Organization",
        on_delete=models.CASCADE,
        related_name="contract_templates",
    )
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, default="")
    category = models.CharField(
        max_length=20, choices=Category.choices, default=Category.OTHER
    )
    contract_type = models.ForeignKey(
        "contracts.ContractType",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="templates",
    )
    content = models.TextField(
        help_text="Template content with variable placeholders using {{variable_name}} syntax"
    )
    header_content = models.TextField(blank=True, default="")
    footer_content = models.TextField(blank=True, default="")

    default_duration_days = models.PositiveIntegerField(null=True, blank=True)
    default_value = models.DecimalField(
        max_digits=15, decimal_places=2, null=True, blank=True
    )
    default_currency = models.CharField(max_length=3, default="USD")

    is_active = models.BooleanField(default=True)
    is_public = models.BooleanField(
        default=False,
        help_text="If true, this template is available to all organizations",
    )
    version = models.PositiveIntegerField(default=1)
    usage_count = models.PositiveIntegerField(default=0)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="created_templates",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]

    def __str__(self):
        return f"{self.name} (v{self.version})"


class TemplateField(models.Model):
    """
    Variable fields within a template that need to be filled in during generation.
    """

    class FieldType(models.TextChoices):
        TEXT = "text", "Text"
        TEXTAREA = "textarea", "Text Area"
        NUMBER = "number", "Number"
        DECIMAL = "decimal", "Decimal"
        DATE = "date", "Date"
        EMAIL = "email", "Email"
        SELECT = "select", "Select"
        CHECKBOX = "checkbox", "Checkbox"
        PARTY_NAME = "party_name", "Party Name"
        PARTY_ADDRESS = "party_address", "Party Address"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    template = models.ForeignKey(
        ContractTemplate,
        on_delete=models.CASCADE,
        related_name="fields",
    )
    name = models.CharField(max_length=100)
    label = models.CharField(max_length=255)
    field_type = models.CharField(
        max_length=20, choices=FieldType.choices, default=FieldType.TEXT
    )
    placeholder = models.CharField(max_length=255, blank=True, default="")
    default_value = models.CharField(max_length=500, blank=True, default="")
    help_text = models.CharField(max_length=500, blank=True, default="")
    is_required = models.BooleanField(default=True)
    validation_regex = models.CharField(max_length=500, blank=True, default="")
    options = models.JSONField(
        default=list,
        blank=True,
        help_text="Options for select fields as a JSON array",
    )
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order", "name"]

    def __str__(self):
        return f"{self.label} ({self.template.name})"


class TemplateClause(models.Model):
    """
    Predefined clauses that are part of a template.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    template = models.ForeignKey(
        ContractTemplate,
        on_delete=models.CASCADE,
        related_name="clauses",
    )
    title = models.CharField(max_length=255)
    content = models.TextField(
        help_text="Clause content with optional {{variable_name}} placeholders"
    )
    clause_type = models.CharField(
        max_length=20,
        choices=[
            ("standard", "Standard"),
            ("negotiable", "Negotiable"),
            ("mandatory", "Mandatory"),
            ("optional", "Optional"),
        ],
        default="standard",
    )
    is_optional = models.BooleanField(default=False)
    order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["order"]

    def __str__(self):
        return f"{self.title} ({self.template.name})"
