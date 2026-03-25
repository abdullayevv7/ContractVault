"""
Views for contracts app.
"""
import logging

from django.http import HttpResponse
from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend

from .models import Contract, ContractType, ContractVersion, ContractParty, ContractClause
from .serializers import (
    ContractListSerializer,
    ContractDetailSerializer,
    ContractCreateSerializer,
    ContractTypeSerializer,
    ContractVersionSerializer,
    ContractPartySerializer,
    ContractClauseSerializer,
)
from .services import (
    transition_contract_status,
    create_contract_version,
    submit_for_approval,
    generate_contract_pdf_file,
    duplicate_contract,
)
from utils.pdf_generator import generate_contract_pdf

logger = logging.getLogger(__name__)


class ContractTypeViewSet(viewsets.ModelViewSet):
    """CRUD for contract types."""

    serializer_class = ContractTypeSerializer
    lookup_field = "id"

    def get_queryset(self):
        user = self.request.user
        if user.is_superuser:
            return ContractType.objects.all()
        if user.organization:
            return ContractType.objects.filter(organization=user.organization)
        return ContractType.objects.none()

    def perform_create(self, serializer):
        serializer.save(organization=self.request.user.organization)


class ContractViewSet(viewsets.ModelViewSet):
    """Full CRUD with lifecycle management for contracts."""

    lookup_field = "id"
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["status", "priority", "contract_type", "auto_renew"]
    search_fields = ["title", "contract_number", "description"]
    ordering_fields = ["created_at", "updated_at", "expiration_date", "total_value", "title"]
    ordering = ["-created_at"]

    def get_queryset(self):
        user = self.request.user
        qs = Contract.objects.select_related(
            "contract_type", "created_by", "updated_by", "organization"
        )
        if user.is_superuser:
            return qs
        if user.organization:
            return qs.filter(organization=user.organization)
        return qs.none()

    def get_serializer_class(self):
        if self.action == "list":
            return ContractListSerializer
        if self.action in ("create", "update", "partial_update"):
            return ContractCreateSerializer
        return ContractDetailSerializer

    def perform_create(self, serializer):
        serializer.save(
            organization=self.request.user.organization,
            created_by=self.request.user,
            updated_by=self.request.user,
        )

    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)

    @action(detail=True, methods=["post"])
    def submit_for_approval(self, request, id=None):
        """Submit a draft contract for approval."""
        contract = self.get_object()
        approval_request = submit_for_approval(contract, request.user)
        return Response(
            {
                "success": True,
                "message": "Contract submitted for approval.",
                "approval_request_id": str(approval_request.id),
            }
        )

    @action(detail=True, methods=["post"])
    def transition(self, request, id=None):
        """Transition contract to a new status."""
        contract = self.get_object()
        new_status = request.data.get("status")
        if not new_status:
            return Response(
                {"error": "Status is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        contract = transition_contract_status(contract, new_status, request.user)
        return Response(ContractDetailSerializer(contract).data)

    @action(detail=True, methods=["post"])
    def create_version(self, request, id=None):
        """Create a version snapshot of the contract."""
        contract = self.get_object()
        change_summary = request.data.get("change_summary", "")
        version = create_contract_version(contract, request.user, change_summary)
        return Response(ContractVersionSerializer(version).data)

    @action(detail=True, methods=["get"])
    def versions(self, request, id=None):
        """List all versions of a contract."""
        contract = self.get_object()
        versions = contract.versions.select_related("created_by").all()
        serializer = ContractVersionSerializer(versions, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=["post"])
    def generate_pdf(self, request, id=None):
        """Generate and download a PDF of the contract."""
        contract = self.get_object()
        pdf_content = generate_contract_pdf(contract)
        response = HttpResponse(pdf_content, content_type="application/pdf")
        response["Content-Disposition"] = (
            f'attachment; filename="contract_{contract.contract_number}.pdf"'
        )
        return response

    @action(detail=True, methods=["post"])
    def duplicate(self, request, id=None):
        """Duplicate a contract as a new draft."""
        contract = self.get_object()
        new_contract = duplicate_contract(contract, request.user)
        return Response(
            ContractDetailSerializer(new_contract).data,
            status=status.HTTP_201_CREATED,
        )


class ContractPartyViewSet(viewsets.ModelViewSet):
    """CRUD for contract parties."""

    serializer_class = ContractPartySerializer
    lookup_field = "id"

    def get_queryset(self):
        user = self.request.user
        qs = ContractParty.objects.select_related("contract")
        contract_id = self.kwargs.get("contract_id")
        if contract_id:
            qs = qs.filter(contract_id=contract_id)
        if not user.is_superuser and user.organization:
            qs = qs.filter(contract__organization=user.organization)
        return qs

    def perform_create(self, serializer):
        contract_id = self.kwargs.get("contract_id")
        if contract_id:
            serializer.save(contract_id=contract_id)
        else:
            serializer.save()


class ContractClauseViewSet(viewsets.ModelViewSet):
    """CRUD for contract clauses."""

    serializer_class = ContractClauseSerializer
    lookup_field = "id"

    def get_queryset(self):
        user = self.request.user
        qs = ContractClause.objects.select_related("contract")
        contract_id = self.kwargs.get("contract_id")
        if contract_id:
            qs = qs.filter(contract_id=contract_id)
        if not user.is_superuser and user.organization:
            qs = qs.filter(contract__organization=user.organization)
        return qs

    def perform_create(self, serializer):
        contract_id = self.kwargs.get("contract_id")
        if contract_id:
            serializer.save(contract_id=contract_id)
        else:
            serializer.save()
