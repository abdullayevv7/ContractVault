"""
Serializers for the signatures app.
"""
from rest_framework import serializers

from .models import SignatureRequest, Signature, SignatureAuditLog


class SignatureSerializer(serializers.ModelSerializer):
    class Meta:
        model = Signature
        fields = [
            "id", "signature_request", "signature_type", "typed_name",
            "signature_image", "document_hash", "ip_address",
            "user_agent", "geolocation", "signed_at",
        ]
        read_only_fields = ["id", "signed_at"]


class SignatureAuditLogSerializer(serializers.ModelSerializer):
    action_display = serializers.CharField(
        source="get_action_display", read_only=True,
    )
    actor_name = serializers.CharField(
        source="actor.get_full_name", read_only=True, default="",
    )

    class Meta:
        model = SignatureAuditLog
        fields = [
            "id", "signature_request", "action", "action_display",
            "actor", "actor_name", "ip_address", "user_agent",
            "metadata", "created_at",
        ]
        read_only_fields = ["id", "created_at"]


class SignatureRequestListSerializer(serializers.ModelSerializer):
    contract_number = serializers.CharField(
        source="contract.contract_number", read_only=True,
    )
    contract_title = serializers.CharField(
        source="contract.title", read_only=True,
    )
    signer_full_name = serializers.CharField(
        source="signer.get_full_name", read_only=True, default="",
    )
    is_signed = serializers.SerializerMethodField()

    class Meta:
        model = SignatureRequest
        fields = [
            "id", "contract", "contract_number", "contract_title",
            "signer", "signer_full_name", "signer_email", "signer_name",
            "order", "status", "expires_at", "sent_at", "viewed_at",
            "completed_at", "is_signed", "created_at",
        ]

    def get_is_signed(self, obj):
        return hasattr(obj, "signature") and obj.signature is not None


class SignatureRequestDetailSerializer(serializers.ModelSerializer):
    contract_number = serializers.CharField(
        source="contract.contract_number", read_only=True,
    )
    contract_title = serializers.CharField(
        source="contract.title", read_only=True,
    )
    signer_full_name = serializers.CharField(
        source="signer.get_full_name", read_only=True, default="",
    )
    signature = SignatureSerializer(read_only=True)
    audit_logs = SignatureAuditLogSerializer(many=True, read_only=True)

    class Meta:
        model = SignatureRequest
        fields = [
            "id", "contract", "contract_number", "contract_title",
            "signer", "signer_full_name", "signer_email", "signer_name",
            "order", "status", "message", "expires_at",
            "sent_at", "viewed_at", "completed_at",
            "declined_reason", "signature", "audit_logs",
            "created_by", "created_at", "updated_at",
        ]


class SignatureRequestCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = SignatureRequest
        fields = [
            "contract", "signer", "signer_email", "signer_name",
            "order", "message", "expires_at",
        ]

    def validate(self, attrs):
        contract = attrs.get("contract")
        if contract and contract.status not in ("approved", "pending_signature"):
            raise serializers.ValidationError(
                "Contract must be approved or pending signature "
                "before sending signature requests."
            )
        return attrs


class SignContractSerializer(serializers.Serializer):
    """Input serializer for the sign action."""
    signature_type = serializers.ChoiceField(
        choices=Signature.SignatureType.choices,
    )
    typed_name = serializers.CharField(required=False, allow_blank=True, default="")
    signature_image = serializers.ImageField(required=False)

    def validate(self, attrs):
        sig_type = attrs.get("signature_type")
        if sig_type == "typed" and not attrs.get("typed_name"):
            raise serializers.ValidationError(
                {"typed_name": "Typed name is required for typed signatures."}
            )
        if sig_type in ("drawn", "uploaded") and not attrs.get("signature_image"):
            raise serializers.ValidationError(
                {"signature_image": "Signature image is required for drawn/uploaded signatures."}
            )
        return attrs
