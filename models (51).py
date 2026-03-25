"""
Views for the notifications app.
"""
import logging

from django.utils import timezone
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import Notification, NotificationPreference
from .serializers import (
    NotificationSerializer,
    NotificationPreferenceSerializer,
    MarkReadSerializer,
)

logger = logging.getLogger(__name__)


class NotificationViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Read-only viewset for notifications.
    Users can list, read, and mark their notifications.
    """

    serializer_class = NotificationSerializer
    lookup_field = "id"

    def get_queryset(self):
        qs = Notification.objects.filter(recipient=self.request.user)

        # Optional filters
        is_read = self.request.query_params.get("is_read")
        if is_read is not None:
            qs = qs.filter(is_read=is_read.lower() in ("true", "1"))

        notification_type = self.request.query_params.get("type")
        if notification_type:
            qs = qs.filter(notification_type=notification_type)

        priority = self.request.query_params.get("priority")
        if priority:
            qs = qs.filter(priority=priority)

        return qs.select_related("contract")

    @action(detail=True, methods=["post"], url_path="mark-read")
    def mark_read(self, request, id=None):
        """Mark a single notification as read."""
        notification = self.get_object()
        if not notification.is_read:
            notification.is_read = True
            notification.read_at = timezone.now()
            notification.save(update_fields=["is_read", "read_at"])
        return Response(NotificationSerializer(notification).data)

    @action(detail=False, methods=["post"], url_path="mark-all-read")
    def mark_all_read(self, request):
        """Mark all or selected notifications as read."""
        serializer = MarkReadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        notification_ids = serializer.validated_data.get("notification_ids")
        qs = Notification.objects.filter(
            recipient=request.user,
            is_read=False,
        )

        if notification_ids:
            qs = qs.filter(id__in=notification_ids)

        count = qs.update(is_read=True, read_at=timezone.now())
        return Response(
            {"success": True, "marked_count": count}
        )

    @action(detail=False, methods=["get"])
    def summary(self, request):
        """Get a summary of notification counts by type and read status."""
        qs = Notification.objects.filter(recipient=request.user)
        total = qs.count()
        unread = qs.filter(is_read=False).count()

        by_type = {}
        for ntype, label in Notification.NotificationType.choices:
            count = qs.filter(notification_type=ntype, is_read=False).count()
            if count > 0:
                by_type[ntype] = {"label": label, "count": count}

        return Response({
            "total": total,
            "unread": unread,
            "by_type": by_type,
        })


class NotificationPreferenceViewSet(viewsets.ModelViewSet):
    """Manage notification preferences for the current user."""

    serializer_class = NotificationPreferenceSerializer
    lookup_field = "id"

    def get_queryset(self):
        return NotificationPreference.objects.filter(user=self.request.user)

    def list(self, request, *args, **kwargs):
        """Get or create preferences for the current user."""
        pref, _created = NotificationPreference.objects.get_or_create(
            user=request.user,
        )
        serializer = self.get_serializer(pref)
        return Response(serializer.data)

    def perform_update(self, serializer):
        serializer.save(user=self.request.user)
