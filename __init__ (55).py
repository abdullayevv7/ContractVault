"""
Signature models: SignatureRequest, Signature, SignatureAuditLog.
Handles the electronic signature workflow for contracts.
"""
import hashlib
import uuid

from django.conf import settings
from django.db import models


class SignatureRequest(models.Model):
    """
    A request for a specific user to sign a contract.
    One contract may have multiple signature requests (one per signer).
    """

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        VIEWED = "viewed", "Viewed"
        SIGNED = "signed", "Signed"
        DECLINED = "declined", "Declined"
        EXPIRED = "expired", "Expired"
        CANCELLED = "cancelled", "Cancelled"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    contract = models.ForeignKey(
        "contracts.Contract",
        on_delete=models.CASCADE,
        related_name="signature_requests",
    )
    signer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="signature_requests",
    )
    signer_email = models.EmailField(
        help_text="Email address of the signer, used for external signers",
    )
    signer_name = models.CharField(max_length=255, blank=True, default="")
    order = models.PositiveIntegerField(
        default=1,
        help_text="Signing order; lower numbers sign first",
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True,
    )
    message = models.TextField(
        blank=True, default="",
        help_text="Optional message to include in the signing invitation",
    )
    access_token = models.CharField(
        max_length=128, unique=True, editable=False,
        help_text="Token for accessing the signing page without login",
    )
    expires_at = models.DateTimeField(
        null=True, blank=True,
        help_text="When this signing request expires",
    )
    sent_at = models.DateTimeField(null=True, blank=True)
    viewed_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    declined_reason = models.TextField(blank=True, default="")

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="created_signature_requests",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["order", "created_at"]
        unique_together = ["contract", "signer"]

    def __str__(self):
        return (
            f"Signature request for {self.signer_email} on "
            f"{self.contract.contract_number}"
        )

    def save(self, *args, **kwargs):
        if not self.access_token:
            self.access_token = hashlib.sha256(
                f"{uuid.uuid4()}{self.signer_email}".encode()
            ).hexdigest()
        if not self.signer_email and self.signer:
            self.signer_email = self.signer.email
        if not self.signer_name and self.signer:
            self.signer_name = self.signer.get_full_name()
        super().save(*args, **kwargs)


class Signature(models.Model):
    """
    Recorded electronic signature for a signing request.
    Contains the cryptographic hash and IP provenance for legal validity.
    """

    class SignatureType(models.TextChoices):
        TYPED = "typed", "Typed Name"
        DRAWN = "drawn", "Drawn Signature"
        UPLOADED = "uploaded", "Uploaded Image"
        CERTIFICATE = "certificate", "Digital Certificate"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    signature_request = models.OneToOneField(
        SignatureRequest,
        on_delete=models.CASCADE,
        related_name="signature",
    )
    signature_type = models.CharField(
        max_length=20,
        choices=SignatureType.choices,
        default=SignatureType.TYPED,
    )
    typed_name = models.CharField(
        max_length=255, blank=True, default="",
        help_text="For typed signatures: the signer's typed name",
    )
    signature_image = models.ImageField(
        upload_to="signatures/images/",
        null=True, blank=True,
        help_text="For drawn or uploaded signatures",
    )
    certificate_data = models.TextField(
        blank=True, default="",
        help_text="PEM-encoded certificate for digital certificate signatures",
    )
    document_hash = models.CharField(
        max_length=128,
        help_text="SHA-256 hash of the document at the time of signing",
    )
    ip_address = models.GenericIPAddressField(
        help_text="IP address of the signer at the time of signing",
    )
    user_agent = models.TextField(
        blank=True, default="",
        help_text="Browser user agent string of the signer",
    )
    geolocation = models.JSONField(
        default=dict, blank=True,
        help_text="Optional geolocation data at time of signing",
    )
    signed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-signed_at"]

    def __str__(self):
        return (
            f"Signature by {self.signature_request.signer_name} "
            f"on {self.signature_request.contract.contract_number}"
        )


class SignatureAuditLog(models.Model):
    """
    Immutable audit trail for all signature-related events.
    Each action (send, view, sign, decline) creates a log entry.
    """

    class Action(models.TextChoices):
        CREATED = "created", "Request Created"
        SENT = "sent", "Invitation Sent"
        VIEWED = "viewed", "Document Viewed"
        SIGNED = "signed", "Document Signed"
        DECLINED = "declined", "Signing Declined"
        EXPIRED = "expired", "Request Expired"
        CANCELLED = "cancelled", "Request Cancelled"
        REMINDED = "reminded", "Reminder Sent"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    signature_request = models.ForeignKey(
        SignatureRequest,
        on_delete=models.CASCADE,
        related_name="audit_logs",
    )
    action = models.CharField(max_length=20, choices=Action.choices)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
    )
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True, default="")
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return (
            f"{self.get_action_display()} - "
            f"{self.signature_request.signer_email} - "
            f"{self.created_at.isoformat()}"
        )
