"""
Views for the approvals app.
"""
import logging

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import ApprovalWorkflow, ApprovalStep, ApprovalRequest
from .serializers import (
    ApprovalWorkflowListSerializer,
    ApprovalWorkflowDetailSerializer,
    ApprovalWorkflowCreateSerializer,
    ApprovalStepSerializer,
    ApprovalRequestListSerializer,
    ApprovalRequestDetailSerializer,
    ApprovalDecisionSerializer,
)
from .services import process_approval_decision

logger = logging.getLogger(__name__)


class ApprovalWorkflowViewSet(viewsets.ModelViewSet):
    """CRUD for approval workflows."""

    lookup_field = "id"

    def get_queryset(self):
        user = self.request.user
        qs = ApprovalWorkflow.objects.select_related(
            "contract_type", "created_by",
        ).prefetch_related("steps")

        if user.is_superuser:
            return qs
        if user.organization:
            return qs.filter(organization=user.organization)
        return qs.none()

    def get_serializer_class(self):
        if self.action == "list":
            return ApprovalWorkflowListSerializer
        if self.action in ("create", "update", "partial_update"):
            return ApprovalWorkflowCreateSerializer
        return ApprovalWorkflowDetailSerializer

    def perform_create(self, serializer):
        serializer.save(
            organization=self.request.user.organization,
            created_by=self.request.user,
        )


class ApprovalStepViewSet(viewsets.ModelViewSet):
    """CRUD for approval steps within a workflow."""

    serializer_class = ApprovalStepSerializer
    lookup_field = "id"

    def get_queryset(self):
        workflow_id = self.kwargs.get("workflow_id")
        qs = ApprovalStep.objects.select_related(
            "workflow", "approver", "approver_role",
        )
        if workflow_id:
            qs = qs.filter(workflow_id=workflow_id)
        user = self.request.user
        if not user.is_superuser and user.organization:
            qs = qs.filter(workflow__organization=user.organization)
        return qs

    def perform_create(self, serializer):
        workflow_id = self.kwargs.get("workflow_id")
        if workflow_id:
            serializer.save(workflow_id=workflow_id)
        else:
            serializer.save()


class ApprovalRequestViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Read-only viewset for approval requests.
    Approve/reject actions are exposed via custom actions.
    """

    lookup_field = "id"

    def get_queryset(self):
        user = self.request.user
        qs = ApprovalRequest.objects.select_related(
            "contract", "workflow", "current_step", "submitted_by",
        )
        if user.is_superuser:
            return qs
        if user.organization:
            return qs.filter(contract__organization=user.organization)
        return qs.none()

    def get_serializer_class(self):
        if self.action == "list":
            return ApprovalRequestListSerializer
        return ApprovalRequestDetailSerializer

    @action(detail=True, methods=["post"])
    def decide(self, request, id=None):
        """Approve or reject an approval request at the current step."""
        approval_request = self.get_object()
        serializer = ApprovalDecisionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        decision = serializer.validated_data["decision"]
        comments = serializer.validated_data.get("comments", "")

        updated_request = process_approval_decision(
            approval_request, request.user, decision, comments,
        )
        return Response(
            ApprovalRequestDetailSerializer(updated_request).data,
        )

    @action(detail=False, methods=["get"], url_path="my-pending")
    def my_pending(self, request):
        """Get all approval requests awaiting the current user's action."""
        qs = self.get_queryset().filter(
            status__in=["pending", "in_progress"],
        )

        # Filter to requests where the current user can approve the current step
        pending_for_user = []
        for req in qs:
            if req.current_step:
                step = req.current_step
                if step.approver == request.user:
                    pending_for_user.append(req)
                elif step.approver_role and request.user.role == step.approver_role:
                    pending_for_user.append(req)
                elif not step.approver and not step.approver_role:
                    if request.user.has_permission("can_approve_contracts"):
                        pending_for_user.append(req)

        serializer = ApprovalRequestListSerializer(pending_for_user, many=True)
        return Response(serializer.data)
