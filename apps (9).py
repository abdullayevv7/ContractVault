"""
Serializers for the amendments app.
"""
from rest_framework import serializers

from .models import Amendment, AmendmentClause


class AmendmentClauseSerializer(serializers.ModelSerializer):
    class Meta:
        model = AmendmentClause
        fields = [
            "id", "amendment", "original_clause", "change_type",
            "title", "original_content", "new_content", "order",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]


class AmendmentListSerializer(serializers.ModelSerializer):
    contract_number = serializers.CharField(
        source="contract.contract_number", read_only=True,
    )
    contract_title = serializers.CharField(
        source="contract.title", read_only=True,
    )
    created_by_name = serializers.CharField(
        source="created_by.get_full_name", read_only=True, default="",
    )
    value_change = serializers.DecimalField(
        max_digits=15, decimal_places=2, read_only=True,
    )
    clause_change_count = serializers.SerializerMethodField()

    class Meta:
        model = Amendment
        fields = [
            "id", "contract", "contract_number", "contract_title",
            "amendment_number", "title", "amendment_type", "status",
            "previous_value", "new_value", "value_change",
            "effective_date", "clause_change_count",
            "created_by_name", "created_at", "updated_at",
        ]

    def get_clause_change_count(self, obj):
        return obj.clause_changes.count()


class AmendmentDetailSerializer(serializers.ModelSerializer):
    contract_number = serializers.CharField(
        source="contract.contract_number", read_only=True,
    )
    contract_title = serializers.CharField(
        source="contract.title", read_only=True,
    )
    created_by_name = serializers.CharField(
        source="created_by.get_full_name", read_only=True, default="",
    )
    approved_by_name = serializers.CharField(
        source="approved_by.get_full_name", read_only=True, default=None,
    )
    clause_changes = AmendmentClauseSerializer(many=True, read_only=True)
    value_change = serializers.DecimalField(
        max_digits=15, decimal_places=2, read_only=True,
    )

    class Meta:
        model = Amendment
        fields = [
            "id", "contract", "contract_number", "contract_title",
            "amendment_number", "title", "description", "amendment_type",
            "status", "reason", "previous_value", "new_value",
            "value_change", "previous_expiration", "new_expiration",
            "effective_date", "document", "changes_summary",
            "clause_changes", "created_by", "created_by_name",
            "approved_by", "approved_by_name",
            "created_at", "updated_at", "executed_at",
        ]
        read_only_fields = [
            "id", "amendment_number", "created_at", "updated_at", "executed_at",
        ]


class AmendmentCreateSerializer(serializers.ModelSerializer):
    clause_changes = AmendmentClauseSerializer(many=True, required=False)

    class Meta:
        model = Amendment
        fields = [
            "contract", "title", "description", "amendment_type",
            "reason", "new_value", "new_expiration",
            "effective_date", "document", "clause_changes",
        ]

    def create(self, validated_data):
        clause_data = validated_data.pop("clause_changes", [])
        contract = validated_data["contract"]

        # Capture current contract values
        validated_data["previous_value"] = contract.total_value
        validated_data["previous_expiration"] = contract.expiration_date

        amendment = Amendment.objects.create(**validated_data)

        for cd in clause_data:
            cd.pop("amendment", None)
            AmendmentClause.objects.create(amendment=amendment, **cd)

        return amendment
