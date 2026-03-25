"""
Admin configuration for accounts app.
"""
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import User, Organization, Role


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = [
        "email", "first_name", "last_name", "organization",
        "role", "is_active", "date_joined",
    ]
    list_filter = ["is_active", "is_staff", "organization", "role"]
    search_fields = ["email", "first_name", "last_name"]
    ordering = ["email"]

    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Personal info", {"fields": ("first_name", "last_name", "phone", "avatar")}),
        ("Organization", {"fields": ("organization", "role", "job_title", "department")}),
        ("Preferences", {"fields": ("timezone", "email_notifications")}),
        (
            "Permissions",
            {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")},
        ),
        ("Important dates", {"fields": ("last_login", "last_active_at", "date_joined")}),
    )
    readonly_fields = ["date_joined", "last_login", "last_active_at"]

    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": (
                    "email", "password1", "password2",
                    "first_name", "last_name", "organization",
                ),
            },
        ),
    )


@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = ["name", "slug", "is_active", "created_at"]
    list_filter = ["is_active"]
    search_fields = ["name", "slug"]
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = [
        "name", "organization", "role_type",
        "can_create_contracts", "can_approve_contracts",
    ]
    list_filter = ["organization", "role_type"]
    search_fields = ["name"]
