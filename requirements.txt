"""
Serializers for templates_mgr app.
"""
import re

from rest_framework import serializers
from django.db import transaction

from .models import ContractTemplate, TemplateField, TemplateClause


class TemplateFieldSerializer(serializers.ModelSerializer):
    class Meta:
        model = TemplateField
        fields = [
            "id", "template", "name", "label", "field_type",
            "placeholder", "default_value", "help_text",
            "is_required", "validation_regex", "options", "order",
        ]
        read_only_fields = ["id"]


class TemplateClauseSerializer(serializers.ModelSerializer):
    class Meta:
        model = TemplateClause
        fields = [
            "id", "template", "title", "content", "clause_type",
            "is_optional", "order", "created_at",
        ]
        read_only_fields = ["id", "created_at"]


class ContractTemplateListSerializer(serializers.ModelSerializer):
    created_by_name = serializers.CharField(
        source="created_by.get_full_name", read_only=True, default=""
    )
    field_count = serializers.SerializerMethodField()
    clause_count = serializers.SerializerMethodField()

    class Meta:
        model = ContractTemplate
        fields = [
            "id", "name", "description", "category", "contract_type",
            "is_active", "is_public", "version", "usage_count",
            "field_count", "clause_count", "created_by_name",
            "created_at", "updated_at",
        ]

    def get_field_count(self, obj):
        return obj.fields.count()

    def get_clause_count(self, obj):
        return obj.clauses.count()


class ContractTemplateDetailSerializer(serializers.ModelSerializer):
    fields_list = TemplateFieldSerializer(source="fields", many=True, read_only=True)
    clauses = TemplateClauseSerializer(many=True, read_only=True)
    created_by_name = serializers.CharField(
        source="created_by.get_full_name", read_only=True, default=""
    )

    class Meta:
        model = ContractTemplate
        fields = [
            "id", "organization", "name", "description", "category",
            "contract_type", "content", "header_content", "footer_content",
            "default_duration_days", "default_value", "default_currency",
            "is_active", "is_public", "version", "usage_count",
            "fields_list", "clauses", "created_by", "created_by_name",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "version", "usage_count", "created_at", "updated_at"]


class ContractTemplateCreateSerializer(serializers.ModelSerializer):
    fields_list = TemplateFieldSerializer(many=True, required=False)
    clauses = TemplateClauseSerializer(many=True, required=False)

    class Meta:
        model = ContractTemplate
        fields = [
            "name", "description", "category", "contract_type",
            "content", "header_content", "footer_content",
            "default_duration_days", "default_value", "default_currency",
            "is_active", "is_public", "fields_list", "clauses",
        ]

    @transaction.atomic
    def create(self, validated_data):
        fields_data = validated_data.pop("fields_list", [])
        clauses_data = validated_data.pop("clauses", [])

        template = ContractTemplate.objects.create(**validated_data)

        for field_data in fields_data:
            field_data.pop("template", None)
            TemplateField.objects.create(template=template, **field_data)

        for clause_data in clauses_data:
            clause_data.pop("template", None)
            TemplateClause.objects.create(template=template, **clause_data)

        return template

    def update(self, instance, validated_data):
        validated_data.pop("fields_list", None)
        validated_data.pop("clauses", None)
        instance.version += 1
        return super().update(instance, validated_data)


class GenerateContractSerializer(serializers.Serializer):
    """Serializer for generating a contract from a template."""

    title = serializers.CharField(max_length=500)
    field_values = serializers.DictField(
        child=serializers.CharField(allow_blank=True),
        help_text="Key-value pairs of template field names and their values",
    )
    include_clauses = serializers.ListField(
        child=serializers.UUIDField(),
        required=False,
        help_text="List of clause IDs to include (omit for all non-optional)",
    )
    effective_date = serializers.DateField(required=False)
    expiration_date = serializers.DateField(required=False)
    priority = serializers.ChoiceField(
        choices=["low", "medium", "high", "critical"],
        default="medium",
    )
    total_value = serializers.DecimalField(
        max_digits=15, decimal_places=2, required=False
    )

    def validate_field_values(self, value):
        template = self.context.get("template")
        if not template:
            return value

        required_fields = template.fields.filter(is_required=True)
        for field in required_fields:
            if field.name not in value or not value[field.name]:
                raise serializers.ValidationError(
                    f"Required field '{field.label}' is missing."
                )

        # Validate regex patterns
        for field in template.fields.all():
            if field.name in value and field.validation_regex:
                if not re.match(field.validation_regex, value[field.name]):
                    raise serializers.ValidationError(
                        f"Field '{field.label}' does not match the required format."
                    )

        return value
