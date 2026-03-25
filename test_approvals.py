"""
Views for templates_mgr app.
"""
import re
import logging

from django.db import transaction
from django.db.models import Q
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.contracts.models import Contract, ContractClause
from .models import ContractTemplate, TemplateField, TemplateClause
from .serializers import (
    ContractTemplateListSerializer,
    ContractTemplateDetailSerializer,
    ContractTemplateCreateSerializer,
    TemplateFieldSerializer,
    TemplateClauseSerializer,
    GenerateContractSerializer,
)

logger = logging.getLogger(__name__)


class ContractTemplateViewSet(viewsets.ModelViewSet):
    """Full CRUD for contract templates with contract generation."""

    lookup_field = "id"

    def get_queryset(self):
        user = self.request.user
        qs = ContractTemplate.objects.select_related("contract_type", "created_by")
        if user.is_superuser:
            return qs
        if user.organization:
            return qs.filter(
                Q(organization=user.organization) | Q(is_public=True)
            )
        return qs.filter(is_public=True)

    def get_serializer_class(self):
        if self.action == "list":
            return ContractTemplateListSerializer
        if self.action in ("create", "update", "partial_update"):
            return ContractTemplateCreateSerializer
        if self.action == "generate":
            return GenerateContractSerializer
        return ContractTemplateDetailSerializer

    def perform_create(self, serializer):
        serializer.save(
            organization=self.request.user.organization,
            created_by=self.request.user,
        )

    @action(detail=True, methods=["post"])
    def generate(self, request, id=None):
        """Generate a new contract from this template."""
        template = self.get_object()

        serializer = GenerateContractSerializer(
            data=request.data,
            context={"template": template, "request": request},
        )
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        field_values = data["field_values"]
        include_clause_ids = data.get("include_clauses")

        # Render template content by replacing placeholders
        rendered_content = template.content
        for key, value in field_values.items():
            rendered_content = re.sub(
                r"\{\{\s*" + re.escape(key) + r"\s*\}\}",
                value,
                rendered_content,
            )

        # Determine which clauses to include
        if include_clause_ids is not None:
            template_clauses = template.clauses.filter(id__in=include_clause_ids)
        else:
            template_clauses = template.clauses.filter(is_optional=False)

        with transaction.atomic():
            contract = Contract.objects.create(
                organization=request.user.organization,
                title=data["title"],
                description=rendered_content,
                contract_type=template.contract_type,
                priority=data.get("priority", "medium"),
                total_value=data.get("total_value", template.default_value),
                currency=template.default_currency,
                effective_date=data.get("effective_date"),
                expiration_date=data.get("expiration_date"),
                metadata={
                    "template_id": str(template.id),
                    "template_name": template.name,
                    "template_version": template.version,
                    "field_values": field_values,
                },
                created_by=request.user,
                updated_by=request.user,
            )

            for tc in template_clauses:
                clause_content = tc.content
                for key, value in field_values.items():
                    clause_content = re.sub(
                        r"\{\{\s*" + re.escape(key) + r"\s*\}\}",
                        value,
                        clause_content,
                    )

                ContractClause.objects.create(
                    contract=contract,
                    title=tc.title,
                    content=clause_content,
                    clause_type=tc.clause_type,
                    order=tc.order,
                )

            template.usage_count += 1
            template.save(update_fields=["usage_count"])

        from apps.contracts.serializers import ContractDetailSerializer
        return Response(
            ContractDetailSerializer(contract).data,
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=["post"])
    def duplicate(self, request, id=None):
        """Create a copy of this template."""
        template = self.get_object()

        with transaction.atomic():
            new_template = ContractTemplate.objects.create(
                organization=request.user.organization,
                name=f"Copy of {template.name}",
                description=template.description,
                category=template.category,
                contract_type=template.contract_type,
                content=template.content,
                header_content=template.header_content,
                footer_content=template.footer_content,
                default_duration_days=template.default_duration_days,
                default_value=template.default_value,
                default_currency=template.default_currency,
                created_by=request.user,
            )

            for field in template.fields.all():
                TemplateField.objects.create(
                    template=new_template,
                    name=field.name,
                    label=field.label,
                    field_type=field.field_type,
                    placeholder=field.placeholder,
                    default_value=field.default_value,
                    help_text=field.help_text,
                    is_required=field.is_required,
                    validation_regex=field.validation_regex,
                    options=field.options,
                    order=field.order,
                )

            for clause in template.clauses.all():
                TemplateClause.objects.create(
                    template=new_template,
                    title=clause.title,
                    content=clause.content,
                    clause_type=clause.clause_type,
                    is_optional=clause.is_optional,
                    order=clause.order,
                )

        return Response(
            ContractTemplateDetailSerializer(new_template).data,
            status=status.HTTP_201_CREATED,
        )


class TemplateFieldViewSet(viewsets.ModelViewSet):
    """CRUD for template fields."""

    serializer_class = TemplateFieldSerializer
    lookup_field = "id"

    def get_queryset(self):
        template_id = self.kwargs.get("template_id")
        qs = TemplateField.objects.all()
        if template_id:
            qs = qs.filter(template_id=template_id)
        user = self.request.user
        if not user.is_superuser and user.organization:
            qs = qs.filter(template__organization=user.organization)
        return qs

    def perform_create(self, serializer):
        template_id = self.kwargs.get("template_id")
        if template_id:
            serializer.save(template_id=template_id)
        else:
            serializer.save()


class TemplateClauseViewSet(viewsets.ModelViewSet):
    """CRUD for template clauses."""

    serializer_class = TemplateClauseSerializer
    lookup_field = "id"

    def get_queryset(self):
        template_id = self.kwargs.get("template_id")
        qs = TemplateClause.objects.all()
        if template_id:
            qs = qs.filter(template_id=template_id)
        user = self.request.user
        if not user.is_superuser and user.organization:
            qs = qs.filter(template__organization=user.organization)
        return qs

    def perform_create(self, serializer):
        template_id = self.kwargs.get("template_id")
        if template_id:
            serializer.save(template_id=template_id)
        else:
            serializer.save()
