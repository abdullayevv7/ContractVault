"""
Notification models: Notification, NotificationPreference.
Handles in-app and email notifications for contract lifecycle events.
"""
import uuid

from django.conf import settings
from django.db import models


class Notification(models.Model):
    """
    In-app notification for contract lifecycle events.
    Notifications are created automatically by services and Celery tasks.
    """

    class NotificationType(models.TextChoices):
        CONTRACT_CREATED = "contract_created", "Contract Created"
        CONTRACT_UPDATED = "contract_updated", "Contract Updated"
        CONTRACT_EXPIRING = "contract_expiring", "Contract Expiring Soon"
        CONTRACT_EXPIRED = "contract_expired", "Contract Expired"
        CONTRACT_RENEWED = "contract_renewed", "Contract Renewed"
        APPROVAL_REQUESTED = "approval_requested", "Approval Requested"
        APPROVAL_APPROVED = "approval_approved", "Approval Approved"
        APPROVAL_REJECTED = "approval_rejected", "Approval Rejected"
        SIGNATURE_REQUESTED = "signature_requested", "Signature Requested"
        SIGNATURE_COMPLETED = "signature_completed", "Signature Completed"
        SIGNATURE_DECLINED = "signature_declined", "Signature Declined"
        AMENDMENT_CREATED = "amendment_created", "Amendment Created"
        COMPLIANCE_ALERT = "compliance_alert", "Compliance Alert"
        SYSTEM = "system", "System Notification"

    class Priority(models.TextChoices):
        LOW = "low", "Low"
        MEDIUM = "medium", "Medium"
        HIGH = "high", "High"
        URGENT = "urgent", "Urgent"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notifications",
    )
    notification_type = models.CharField(
        max_length=30,
        choices=NotificationType.choices,
        db_index=True,
    )
    title = models.CharField(max_length=500)
    message = models.TextField()
    priority = models.CharField(
        max_length=10,
        choices=Priority.choices,
        default=Priority.MEDIUM,
    )
    contract = models.ForeignKey(
        "contracts.Contract",
        on_delete=models.CASCADE,
        null=True, blank=True,
        related_name="notifications",
    )
    action_url = models.CharField(
        max_length=500, blank=True, default="",
        help_text="Frontend URL for the action related to this notification",
    )
    is_read = models.BooleanField(default=False, db_index=True)
    read_at = models.DateTimeField(null=True, blank=True)
    email_sent = models.BooleanField(default=False)
    email_sent_at = models.DateTimeField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["recipient", "is_read"]),
            models.Index(fields=["notification_type", "created_at"]),
        ]

    def __str__(self):
        return f"[{self.get_notification_type_display()}] {self.title}"


class NotificationPreference(models.Model):
    """
    Per-user notification preferences controlling which channels
    (in-app, email) receive which notification types.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notification_preferences",
    )
    contract_updates_email = models.BooleanField(default=True)
    contract_updates_inapp = models.BooleanField(default=True)
    approval_requests_email = models.BooleanField(default=True)
    approval_requests_inapp = models.BooleanField(default=True)
    signature_requests_email = models.BooleanField(default=True)
    signature_requests_inapp = models.BooleanField(default=True)
    expiration_alerts_email = models.BooleanField(default=True)
    expiration_alerts_inapp = models.BooleanField(default=True)
    compliance_alerts_email = models.BooleanField(default=True)
    compliance_alerts_inapp = models.BooleanField(default=True)
    daily_digest = models.BooleanField(
        default=False,
        help_text="Receive a daily email digest instead of individual emails",
    )
    quiet_hours_start = models.TimeField(
        null=True, blank=True,
        help_text="Start of quiet hours (no email notifications)",
    )
    quiet_hours_end = models.TimeField(
        null=True, blank=True,
        help_text="End of quiet hours",
    )
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Notification preferences for {self.user.email}"
