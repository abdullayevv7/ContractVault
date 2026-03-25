"""
Account models: User, Organization, Role, and Membership.
"""
import uuid

from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models


class Organization(models.Model):
    """
    Organization represents a tenant in the multi-tenant system.
    All contracts and data are scoped to an organization.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True)
    domain = models.CharField(max_length=255, blank=True, default="")
    logo = models.ImageField(upload_to="organizations/logos/", blank=True, null=True)
    address = models.TextField(blank=True, default="")
    phone = models.CharField(max_length=20, blank=True, default="")
    website = models.URLField(blank=True, default="")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Role(models.Model):
    """
    Roles define permissions within an organization.
    """

    class RoleType(models.TextChoices):
        ADMIN = "admin", "Administrator"
        MANAGER = "manager", "Contract Manager"
        LEGAL = "legal", "Legal Counsel"
        APPROVER = "approver", "Approver"
        VIEWER = "viewer", "Viewer"
        SIGNER = "signer", "Signer"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="roles"
    )
    name = models.CharField(max_length=100)
    role_type = models.CharField(max_length=20, choices=RoleType.choices, default=RoleType.VIEWER)
    description = models.TextField(blank=True, default="")

    can_create_contracts = models.BooleanField(default=False)
    can_edit_contracts = models.BooleanField(default=False)
    can_delete_contracts = models.BooleanField(default=False)
    can_approve_contracts = models.BooleanField(default=False)
    can_sign_contracts = models.BooleanField(default=False)
    can_manage_templates = models.BooleanField(default=False)
    can_view_analytics = models.BooleanField(default=False)
    can_manage_users = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["organization", "name"]
        unique_together = ["organization", "name"]

    def __str__(self):
        return f"{self.name} ({self.organization.name})"


class UserManager(BaseUserManager):
    """Custom user manager that uses email as the unique identifier."""

    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("The Email field must be set")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")

        return self.create_user(email, password, **extra_fields)


class User(AbstractUser):
    """
    Custom user model using email as the primary identifier.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    username = None
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=20, blank=True, default="")
    job_title = models.CharField(max_length=100, blank=True, default="")
    department = models.CharField(max_length=100, blank=True, default="")
    avatar = models.ImageField(upload_to="users/avatars/", blank=True, null=True)
    timezone = models.CharField(max_length=50, default="UTC")
    organization = models.ForeignKey(
        Organization,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="members",
    )
    role = models.ForeignKey(
        Role,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="users",
    )
    email_notifications = models.BooleanField(default=True)
    last_active_at = models.DateTimeField(null=True, blank=True)

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["first_name", "last_name"]

    class Meta:
        ordering = ["email"]

    def __str__(self):
        return self.email

    def get_full_name(self):
        full_name = f"{self.first_name} {self.last_name}".strip()
        return full_name or self.email

    @property
    def has_org(self):
        return self.organization_id is not None

    def has_permission(self, permission_name):
        """Check if user has a specific permission via their role."""
        if self.is_superuser:
            return True
        if not self.role:
            return False
        return getattr(self.role, permission_name, False)
