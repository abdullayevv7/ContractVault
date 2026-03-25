"""
Views for the amendments app.
"""
import logging

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import Amendment
from .serializers import (
    AmendmentListSerializer,
    AmendmentDetailSerializer,
    AmendmentCreateSerializer,
)
from .services import transition_amendment_status, execute_amendment

logger = logging.getLogger(__name__)


class AmendmentViewSet(viewsets.ModelViewSet):
    """Full CRUD and lifecycle management for contract amendments."""

    lookup_field = "id"

    def get_queryset(self):
        user = self.request.user
        qs = Amendment.objects.select_related(
            "contract", "created_by", "approved_by",
        ).prefetch_related("clause_changes")

        # Optional filter by contract
        contract_id = self.request.query_params.get("contract")
        if contract_id:
            qs = qs.filter(contract_id=contract_id)

        if user.is_superuser:
            return qs
        if user.organization:
            return qs.filter(contract__organization=user.organization)
        return qs.none()

    def get_serializer_class(self):
        if self.action == "list":
            return AmendmentListSerializer
        if self.action in ("create", "update", "partial_update"):
            return AmendmentCreateSerializer
        return AmendmentDetailSerializer

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    @action(detail=True, methods=["post"])
    def transition(self, request, id=None):
        """Transition an amendment to a new status."""
        amendment = self.get_object()
        new_status = request.data.get("status")
        if not new_status:
            return Response(
                {"error": "Status is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        amendment = transition_amendment_status(
            amendment, new_status, request.user,
        )
        return Response(AmendmentDetailSerializer(amendment).data)

    @action(detail=True, methods=["post"])
    def execute(self, request, id=None):
        """Execute an approved amendment, applying changes to the contract."""
        amendment = self.get_object()
        contract = execute_amendment(amendment, request.user)
        return Response({
            "success": True,
            "message": f"Amendment {amendment.amendment_number} executed successfully.",
            "contract_id": str(contract.id),
        })
