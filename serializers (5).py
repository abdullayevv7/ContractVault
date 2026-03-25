"""
Views for accounts app.
"""
from django.utils import timezone
from rest_framework import generics, status, viewsets, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import User, Organization, Role
from .serializers import (
    UserSerializer,
    UserCreateSerializer,
    UserProfileSerializer,
    LoginSerializer,
    ChangePasswordSerializer,
    OrganizationSerializer,
    RoleSerializer,
)


class RegisterView(generics.CreateAPIView):
    """Register a new user."""

    serializer_class = UserCreateSerializer
    permission_classes = [permissions.AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        login_serializer = LoginSerializer(context={"request": request})
        tokens = login_serializer.get_tokens(user)

        return Response(
            {
                "success": True,
                "user": UserSerializer(user).data,
                "tokens": tokens,
            },
            status=status.HTTP_201_CREATED,
        )


class LoginView(APIView):
    """Authenticate user and return JWT tokens."""

    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data["user"]

        user.last_active_at = timezone.now()
        user.save(update_fields=["last_active_at"])

        tokens = serializer.get_tokens(user)

        return Response(
            {
                "success": True,
                "user": UserSerializer(user).data,
                "tokens": tokens,
            }
        )


class ProfileView(generics.RetrieveUpdateAPIView):
    """Get or update the current user's profile."""

    serializer_class = UserProfileSerializer

    def get_object(self):
        return self.request.user


class ChangePasswordView(APIView):
    """Change the current user's password."""

    def post(self, request):
        serializer = ChangePasswordSerializer(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(
            {"success": True, "message": "Password changed successfully."}
        )


class OrganizationViewSet(viewsets.ModelViewSet):
    """CRUD operations for organizations."""

    serializer_class = OrganizationSerializer
    lookup_field = "id"

    def get_queryset(self):
        user = self.request.user
        if user.is_superuser:
            return Organization.objects.all()
        if user.organization:
            return Organization.objects.filter(id=user.organization_id)
        return Organization.objects.none()

    def perform_create(self, serializer):
        org = serializer.save()
        user = self.request.user
        if not user.organization:
            # Create default admin role
            admin_role = Role.objects.create(
                organization=org,
                name="Administrator",
                role_type=Role.RoleType.ADMIN,
                can_create_contracts=True,
                can_edit_contracts=True,
                can_delete_contracts=True,
                can_approve_contracts=True,
                can_sign_contracts=True,
                can_manage_templates=True,
                can_view_analytics=True,
                can_manage_users=True,
            )
            user.organization = org
            user.role = admin_role
            user.save(update_fields=["organization", "role"])


class RoleViewSet(viewsets.ModelViewSet):
    """CRUD operations for roles within an organization."""

    serializer_class = RoleSerializer
    lookup_field = "id"

    def get_queryset(self):
        user = self.request.user
        if user.is_superuser:
            return Role.objects.all()
        if user.organization:
            return Role.objects.filter(organization=user.organization)
        return Role.objects.none()

    def perform_create(self, serializer):
        serializer.save(organization=self.request.user.organization)


class UserViewSet(viewsets.ModelViewSet):
    """CRUD operations for users within an organization."""

    serializer_class = UserSerializer
    lookup_field = "id"

    def get_queryset(self):
        user = self.request.user
        if user.is_superuser:
            return User.objects.all()
        if user.organization:
            return User.objects.filter(organization=user.organization)
        return User.objects.filter(id=user.id)

    @action(detail=True, methods=["post"])
    def deactivate(self, request, id=None):
        target_user = self.get_object()
        if target_user == request.user:
            return Response(
                {"error": "You cannot deactivate your own account."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        target_user.is_active = False
        target_user.save(update_fields=["is_active"])
        return Response({"success": True, "message": "User deactivated."})

    @action(detail=True, methods=["post"])
    def activate(self, request, id=None):
        target_user = self.get_object()
        target_user.is_active = True
        target_user.save(update_fields=["is_active"])
        return Response({"success": True, "message": "User activated."})
