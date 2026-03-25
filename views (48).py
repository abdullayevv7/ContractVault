"""
Serializers for the notifications app.
"""
from rest_framework import serializers

from .models import Notification, NotificationPreference


class NotificationSerializer(serializers.ModelSerializer):
    notification_type_display = serializers.CharField(
        source="get_notification_type_display", read_only=True,
    )
    contract_number = serializers.CharField(
        source="contract.contract_number", read_only=True, default=None,
    )

    class Meta:
        model = Notification
        fields = [
            "id", "recipient", "notification_type",
            "notification_type_display", "title", "message",
            "priority", "contract", "contract_number",
            "action_url", "is_read", "read_at", "email_sent",
            "metadata", "created_at",
        ]
        read_only_fields = [
            "id", "recipient", "notification_type", "title",
            "message", "priority", "contract", "action_url",
            "email_sent", "metadata", "created_at",
        ]


class NotificationPreferenceSerializer(serializers.ModelSerializer):
    class Meta:
        model = NotificationPreference
        fields = [
            "id", "user",
            "contract_updates_email", "contract_updates_inapp",
            "approval_requests_email", "approval_requests_inapp",
            "signature_requests_email", "signature_requests_inapp",
            "expiration_alerts_email", "expiration_alerts_inapp",
            "compliance_alerts_email", "compliance_alerts_inapp",
            "daily_digest", "quiet_hours_start", "quiet_hours_end",
            "updated_at",
        ]
        read_only_fields = ["id", "user", "updated_at"]


class MarkReadSerializer(serializers.Serializer):
    """Input serializer for marking notifications as read."""
    notification_ids = serializers.ListField(
        child=serializers.UUIDField(),
        required=False,
        help_text="Specific notification IDs to mark as read. If omitted, marks all.",
    )
