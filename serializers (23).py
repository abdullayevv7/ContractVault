"""
Serializers for approvals app.
"""
from rest_framework import serializers

from .models import ApprovalWorkflow, ApprovalStep, ApprovalRequest


class ApprovalStepSerializer(serializers.ModelSerializer):
    approver_name = serializers.CharField(
        source="approver.get_full_name", read_only=True, default=None
    )
    approver_role_name = serializers.CharField(
        source="approver_role.name", read_only=True, default=None
    )

    class Meta:
        model = ApprovalStep
        fields = [
            "id", "workflow", "name", "description", "order",
            "step_type", "approver", "approver_name",
            "approver_role", "approver_role_name",
            "auto_approve_after_hours", "is_required", "created_at",
        ]
        read_only_fields = ["id", "created_at"]


class ApprovalWorkflowListSerializer(serializers.ModelSerializer):
    step_count = serializers.IntegerField(read_only=True)
    contract_type_name = serializers.CharField(
        source="contract_type.name", read_only=True, default=None
    )

    class Meta:
        model = ApprovalWorkflow
        fields = [
            "id", "name", "description", "contract_type",
            "contract_type_name", "is_active", "is_default",
            "step_count", "min_value_threshold",
            "max_value_threshold", "created_at",
        ]


class ApprovalWorkflowDetailSerializer(serializers.ModelSerializer):
    steps = ApprovalStepSerializer(many=True, read_only=True)
    contract_type_name = serializers.CharField(
        source="contract_type.name", read_only=True, default=None
    )
    created_by_name = serializers.CharField(
        source="created_by.get_full_name", read_only=True, default=""
    )

    class Meta:
        model = ApprovalWorkflow
        fields = [
            "id", "organization", "name", "description",
            "contract_type", "contract_type_name", "is_active",
            "is_default", "min_value_threshold",
            "max_value_threshold", "steps", "created_by",
            "created_by_name", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class ApprovalWorkflowCreateSerializer(serializers.ModelSerializer):
    steps = ApprovalStepSerializer(many=True, required=False)

    class Meta:
        model = ApprovalWorkflow
        fields = [
            "name", "description", "contract_type", "is_active",
            "is_default", "min_value_threshold",
            "max_value_threshold", "steps",
        ]

    def create(self, validated_data):
        steps_data = validated_data.pop("steps", [])
        workflow = ApprovalWorkflow.objects.create(**validated_data)

        for idx, step_data in enumerate(steps_data):
            step_data.pop("workflow", None)
            step_data["order"] = step_data.get("order", idx + 1)
            ApprovalStep.objects.create(workflow=workflow, **step_data)

        return workflow


class ApprovalRequestListSerializer(serializers.ModelSerializer):
    contract_number = serializers.CharField(
        source="contract.contract_number", read_only=True
    )
    contract_title = serializers.CharField(
        source="contract.title", read_only=True
    )
    workflow_name = serializers.CharField(
        source="workflow.name", read_only=True
    )
    submitted_by_name = serializers.CharField(
        source="submitted_by.get_full_name", read_only=True, default=""
    )
    current_step_name = serializers.CharField(
        source="current_step.name", read_only=True, default=None
    )

    class Meta:
        model = ApprovalRequest
        fields = [
            "id", "contract", "contract_number", "contract_title",
            "workflow", "workflow_name", "current_step",
            "current_step_name", "status", "submitted_by",
            "submitted_by_name", "created_at", "updated_at",
            "completed_at",
        ]


class ApprovalRequestDetailSerializer(serializers.ModelSerializer):
    contract_number = serializers.CharField(
        source="contract.contract_number", read_only=True
    )
    contract_title = serializers.CharField(
        source="contract.title", read_only=True
    )
    workflow_name = serializers.CharField(
        source="workflow.name", read_only=True
    )
    submitted_by_name = serializers.CharField(
        source="submitted_by.get_full_name", read_only=True, default=""
    )
    current_step_detail = ApprovalStepSerializer(
        source="current_step", read_only=True
    )

    class Meta:
        model = ApprovalRequest
        fields = [
            "id", "contract", "contract_number", "contract_title",
            "workflow", "workflow_name", "current_step",
            "current_step_detail", "status", "submitted_by",
            "submitted_by_name", "notes", "decision_history",
            "created_at", "updated_at", "completed_at",
        ]


class ApprovalDecisionSerializer(serializers.Serializer):
    """Serializer for approve/reject actions."""

    decision = serializers.ChoiceField(choices=["approve", "reject"])
    comments = serializers.CharField(required=False, allow_blank=True, default="")
