"""
Views for the signatures app.
"""
import logging

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import SignatureRequest, Signature
from .serializers import (
    SignatureRequestListSerializer,
    SignatureRequestDetailSerializer,
    SignatureRequestCreateSerializer,
    SignContractSerializer,
    SignatureAuditLogSerializer,
)
from .services import (
    create_signature_requests,
    record_signature,
    decline_signature,
)

logger = logging.getLogger(__name__)


class SignatureRequestViewSet(viewsets.ModelViewSet):
    """Manage signature requests for contracts."""

    lookup_field = "id"

    def get_queryset(self):
        user = self.request.user
        qs = SignatureRequest.objects.select_related(
            "contract", "signer", "created_by",
        ).prefetch_related("audit_logs")

        if user.is_superuser:
            return qs
        if user.organization:
            return qs.filter(contract__organization=user.organization)
        return qs.filter(signer=user)

    def get_serializer_class(self):
        if self.action == "list":
            return SignatureRequestListSerializer
        if self.action == "create":
            return SignatureRequestCreateSerializer
        if self.action == "sign":
            return SignContractSerializer
        return SignatureRequestDetailSerializer

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    @action(detail=False, methods=["post"], url_path="bulk-create")
    def bulk_create(self, request):
        """Create multiple signature requests for a single contract."""
        contract_id = request.data.get("contract_id")
        signers = request.data.get("signers", [])

        if not contract_id or not signers:
            return Response(
                {"error": "contract_id and signers are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        from apps.contracts.models import Contract
        try:
            contract = Contract.objects.get(id=contract_id)
        except Contract.DoesNotExist:
            return Response(
                {"error": "Contract not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        sig_requests = create_signature_requests(
            contract, signers, request.user,
        )
        serializer = SignatureRequestListSerializer(sig_requests, many=True)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"])
    def sign(self, request, id=None):
        """Sign a contract via this signature request."""
        sig_request = self.get_object()
        serializer = SignContractSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        ip_address = self._get_client_ip(request)
        user_agent = request.META.get("HTTP_USER_AGENT", "")

        signature = record_signature(
            signature_request=sig_request,
            signature_type=serializer.validated_data["signature_type"],
            ip_address=ip_address,
            user_agent=user_agent,
            typed_name=serializer.validated_data.get("typed_name", ""),
            signature_image=serializer.validated_data.get("signature_image"),
        )
        return Response(
            {
                "success": True,
                "message": "Contract signed successfully.",
                "signature_id": str(signature.id),
            }
        )

    @action(detail=True, methods=["post"])
    def decline(self, request, id=None):
        """Decline to sign a contract."""
        sig_request = self.get_object()
        reason = request.data.get("reason", "")

        ip_address = self._get_client_ip(request)
        user_agent = request.META.get("HTTP_USER_AGENT", "")

        decline_signature(sig_request, reason, ip_address, user_agent)
        return Response(
            {"success": True, "message": "Signature request declined."}
        )

    @action(detail=True, methods=["get"], url_path="audit-log")
    def audit_log(self, request, id=None):
        """Get the audit log for a specific signature request."""
        sig_request = self.get_object()
        logs = sig_request.audit_logs.all()
        serializer = SignatureAuditLogSerializer(logs, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=["get"], url_path="my-pending")
    def my_pending(self, request):
        """Get all pending signature requests for the current user."""
        pending = self.get_queryset().filter(
            signer=request.user,
            status__in=["pending", "viewed"],
        )
        serializer = SignatureRequestListSerializer(pending, many=True)
        return Response(serializer.data)

    @staticmethod
    def _get_client_ip(request):
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded_for:
            return x_forwarded_for.split(",")[0].strip()
        return request.META.get("REMOTE_ADDR", "127.0.0.1")
