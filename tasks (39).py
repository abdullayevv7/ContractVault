"""
Serializers for contracts app.
"""
from rest_framework import serializers

from .models import Contract, ContractType, ContractVersion, ContractParty, ContractClause


class ContractTypeSerializer(serializers.ModelSerializer):
    contract_count = serializers.SerializerMethodField()

    class Meta:
        model = ContractType
        fields = [
            "id", "name", "description", "prefix", "requires_approval",
            "requires_signature", "default_duration_days", "is_active",
            "contract_count", "created_at",
        ]
        read_only_fields = ["id", "created_at"]

    def get_contract_count(self, obj):
        return obj.contracts.count()


class ContractPartySerializer(serializers.ModelSerializer):
    class Meta:
        model = ContractParty
        fields = [
            "id", "contract", "name", "email", "phone",
            "organization_name", "role", "address", "user",
            "is_primary", "created_at",
        ]
        read_only_fields = ["id", "created_at"]


class ContractClauseSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContractClause
        fields = [
            "id", "contract", "title", "content", "clause_type",
            "order", "is_active", "parent_clause", "metadata",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class ContractVersionSerializer(serializers.ModelSerializer):
    created_by_name = serializers.CharField(
        source="created_by.get_full_name", read_only=True, default=""
    )

    class Meta:
        model = ContractVersion
        fields = [
            "id", "contract", "version_number", "title",
            "description", "content_snapshot", "document",
            "change_summary", "created_by", "created_by_name",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]


class ContractListSerializer(serializers.ModelSerializer):
    """Lighter serializer for list views."""

    contract_type_name = serializers.CharField(
        source="contract_type.name", read_only=True, default=None
    )
    created_by_name = serializers.CharField(
        source="created_by.get_full_name", read_only=True, default=""
    )
    days_until_expiration = serializers.IntegerField(read_only=True)
    party_count = serializers.SerializerMethodField()

    class Meta:
        model = Contract
        fields = [
            "id", "contract_number", "title", "status", "priority",
            "contract_type", "contract_type_name", "total_value",
            "currency", "effective_date", "expiration_date",
            "days_until_expiration", "version", "created_by_name",
            "party_count", "tags", "created_at", "updated_at",
        ]

    def get_party_count(self, obj):
        return obj.parties.count()


class ContractDetailSerializer(serializers.ModelSerializer):
    """Full serializer for detail views."""

    contract_type_name = serializers.CharField(
        source="contract_type.name", read_only=True, default=None
    )
    created_by_name = serializers.CharField(
        source="created_by.get_full_name", read_only=True, default=""
    )
    updated_by_name = serializers.CharField(
        source="updated_by.get_full_name", read_only=True, default=""
    )
    parties = ContractPartySerializer(many=True, read_only=True)
    clauses = ContractClauseSerializer(many=True, read_only=True)
    days_until_expiration = serializers.IntegerField(read_only=True)
    is_expired = serializers.BooleanField(read_only=True)

    class Meta:
        model = Contract
        fields = [
            "id", "organization", "contract_number", "title",
            "description", "contract_type", "contract_type_name",
            "status", "priority", "total_value", "currency",
            "effective_date", "expiration_date", "termination_date",
            "renewal_date", "auto_renew", "renewal_period_days",
            "document", "pdf_file", "version", "parent_contract",
            "created_by", "created_by_name", "updated_by",
            "updated_by_name", "compliance_requirements", "tags",
            "metadata", "parties", "clauses", "days_until_expiration",
            "is_expired", "created_at", "updated_at",
        ]
        read_only_fields = [
            "id", "contract_number", "version", "created_at", "updated_at",
        ]


class ContractCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating contracts."""

    parties = ContractPartySerializer(many=True, required=False)
    clauses = ContractClauseSerializer(many=True, required=False)

    class Meta:
        model = Contract
        fields = [
            "title", "description", "contract_type", "priority",
            "total_value", "currency", "effective_date",
            "expiration_date", "auto_renew", "renewal_period_days",
            "document", "compliance_requirements", "tags",
            "metadata", "parties", "clauses",
        ]

    def create(self, validated_data):
        parties_data = validated_data.pop("parties", [])
        clauses_data = validated_data.pop("clauses", [])

        contract = Contract.objects.create(**validated_data)

        for party_data in parties_data:
            party_data.pop("contract", None)
            ContractParty.objects.create(contract=contract, **party_data)

        for clause_data in clauses_data:
            clause_data.pop("contract", None)
            ContractClause.objects.create(contract=contract, **clause_data)

        return contract

    def update(self, instance, validated_data):
        validated_data.pop("parties", None)
        validated_data.pop("clauses", None)
        return super().update(instance, validated_data)
