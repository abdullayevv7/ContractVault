"""
Admin configuration for contracts app.
"""
from django.contrib import admin

from .models import Contract, ContractType, ContractVersion, ContractParty, ContractClause


class ContractPartyInline(admin.TabularInline):
    model = ContractParty
    extra = 0


class ContractClauseInline(admin.TabularInline):
    model = ContractClause
    extra = 0
    ordering = ["order"]


@admin.register(Contract)
class ContractAdmin(admin.ModelAdmin):
    list_display = [
        "contract_number", "title", "status", "priority",
        "contract_type", "total_value", "effective_date",
        "expiration_date", "organization", "created_at",
    ]
    list_filter = ["status", "priority", "contract_type", "organization"]
    search_fields = ["contract_number", "title", "description"]
    readonly_fields = ["contract_number", "version", "created_at", "updated_at"]
    inlines = [ContractPartyInline, ContractClauseInline]
    date_hierarchy = "created_at"

    fieldsets = (
        (None, {"fields": ("contract_number", "title", "description", "contract_type")}),
        ("Status", {"fields": ("status", "priority", "version")}),
        ("Financial", {"fields": ("total_value", "currency")}),
        (
            "Dates",
            {"fields": (
                "effective_date", "expiration_date", "termination_date",
                "renewal_date", "auto_renew", "renewal_period_days",
            )},
        ),
        ("Files", {"fields": ("document", "pdf_file")}),
        ("Compliance", {"fields": ("compliance_requirements", "tags", "metadata")}),
        ("Organization", {"fields": ("organization", "created_by", "updated_by")}),
        ("Timestamps", {"fields": ("created_at", "updated_at")}),
    )


@admin.register(ContractType)
class ContractTypeAdmin(admin.ModelAdmin):
    list_display = ["name", "prefix", "organization", "requires_approval", "is_active"]
    list_filter = ["organization", "is_active"]
    search_fields = ["name"]


@admin.register(ContractVersion)
class ContractVersionAdmin(admin.ModelAdmin):
    list_display = ["contract", "version_number", "created_by", "created_at"]
    list_filter = ["created_at"]
    search_fields = ["contract__contract_number"]
    readonly_fields = ["created_at"]


@admin.register(ContractParty)
class ContractPartyAdmin(admin.ModelAdmin):
    list_display = ["name", "contract", "role", "email", "organization_name"]
    list_filter = ["role"]
    search_fields = ["name", "email"]


@admin.register(ContractClause)
class ContractClauseAdmin(admin.ModelAdmin):
    list_display = ["title", "contract", "clause_type", "order", "is_active"]
    list_filter = ["clause_type", "is_active"]
    search_fields = ["title"]
