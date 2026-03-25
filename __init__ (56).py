"""
Business logic services for the signatures app.
Handles signature request creation, signing, and verification workflows.
"""
import hashlib
import logging

from django.db import transaction
from django.utils import timezone

from utils.exceptions import SignatureError
from .models import SignatureRequest, Signature, SignatureAuditLog

logger = logging.getLogger(__name__)


@transaction.atomic
def create_signature_requests(contract, signers_data, created_by):
    """
    Create signature requests for a contract.

    Args:
        contract: Contract instance
        signers_data: list of dicts with keys: signer, signer_email,
                      signer_name, order, message, expires_at
        created_by: User creating the requests

    Returns:
        list[SignatureRequest]
    """
    from apps.contracts.services import transition_contract_status

    if contract.status == "approved":
        transition_contract_status(contract, "pending_signature", created_by)

    requests = []
    for data in signers_data:
        sig_req = SignatureRequest.objects.create(
            contract=contract,
            created_by=created_by,
            **data,
        )

        SignatureAuditLog.objects.create(
            signature_request=sig_req,
            action=SignatureAuditLog.Action.CREATED,
            actor=created_by,
        )
        requests.append(sig_req)

    logger.info(
        "Created %d signature requests for contract %s",
        len(requests),
        contract.contract_number,
    )
    return requests


@transaction.atomic
def record_signature(signature_request, signature_type, ip_address,
                     user_agent="", typed_name="", signature_image=None,
                     certificate_data=""):
    """
    Record a signature for a pending signing request.

    Args:
        signature_request: SignatureRequest instance
        signature_type: one of Signature.SignatureType values
        ip_address: signer's IP address
        user_agent: browser user agent
        typed_name: typed name for typed signatures
        signature_image: image file for drawn/uploaded signatures
        certificate_data: PEM data for certificate signatures

    Returns:
        Signature instance

    Raises:
        SignatureError: if the request is not in a signable state
    """
    if signature_request.status not in (
        SignatureRequest.Status.PENDING,
        SignatureRequest.Status.VIEWED,
    ):
        raise SignatureError(
            f"Cannot sign a request with status '{signature_request.get_status_display()}'."
        )

    if signature_request.expires_at and signature_request.expires_at < timezone.now():
        signature_request.status = SignatureRequest.Status.EXPIRED
        signature_request.save(update_fields=["status", "updated_at"])
        raise SignatureError("This signature request has expired.")

    # Compute document hash from the contract PDF or document file
    document_hash = _compute_document_hash(signature_request.contract)

    signature = Signature.objects.create(
        signature_request=signature_request,
        signature_type=signature_type,
        typed_name=typed_name,
        signature_image=signature_image,
        certificate_data=certificate_data,
        document_hash=document_hash,
        ip_address=ip_address,
        user_agent=user_agent,
    )

    signature_request.status = SignatureRequest.Status.SIGNED
    signature_request.completed_at = timezone.now()
    signature_request.save(update_fields=["status", "completed_at", "updated_at"])

    SignatureAuditLog.objects.create(
        signature_request=signature_request,
        action=SignatureAuditLog.Action.SIGNED,
        actor=signature_request.signer,
        ip_address=ip_address,
        user_agent=user_agent,
        metadata={"signature_type": signature_type, "document_hash": document_hash},
    )

    # Check if all signature requests for the contract are complete
    _check_all_signed(signature_request.contract)

    logger.info(
        "Signature recorded for request %s by %s",
        signature_request.id,
        signature_request.signer_email,
    )
    return signature


def decline_signature(signature_request, reason, ip_address, user_agent=""):
    """
    Decline a signing request with a reason.

    Args:
        signature_request: SignatureRequest instance
        reason: text reason for declining
        ip_address: signer's IP address
        user_agent: browser user agent

    Returns:
        Updated SignatureRequest

    Raises:
        SignatureError: if the request cannot be declined
    """
    if signature_request.status not in (
        SignatureRequest.Status.PENDING,
        SignatureRequest.Status.VIEWED,
    ):
        raise SignatureError("This request cannot be declined in its current state.")

    signature_request.status = SignatureRequest.Status.DECLINED
    signature_request.declined_reason = reason
    signature_request.completed_at = timezone.now()
    signature_request.save(
        update_fields=["status", "declined_reason", "completed_at", "updated_at"]
    )

    SignatureAuditLog.objects.create(
        signature_request=signature_request,
        action=SignatureAuditLog.Action.DECLINED,
        actor=signature_request.signer,
        ip_address=ip_address,
        user_agent=user_agent,
        metadata={"reason": reason},
    )

    logger.info(
        "Signature request %s declined by %s: %s",
        signature_request.id,
        signature_request.signer_email,
        reason,
    )
    return signature_request


def _compute_document_hash(contract):
    """Compute SHA-256 hash of the contract's document or PDF."""
    if contract.pdf_file:
        try:
            contract.pdf_file.open("rb")
            content = contract.pdf_file.read()
            contract.pdf_file.close()
            return hashlib.sha256(content).hexdigest()
        except Exception:
            pass

    if contract.document:
        try:
            contract.document.open("rb")
            content = contract.document.read()
            contract.document.close()
            return hashlib.sha256(content).hexdigest()
        except Exception:
            pass

    # Fallback: hash contract metadata
    hash_input = f"{contract.id}{contract.contract_number}{contract.version}"
    return hashlib.sha256(hash_input.encode()).hexdigest()


def _check_all_signed(contract):
    """
    Check if all signature requests for a contract have been signed.
    If yes, transition the contract to 'active' status.
    """
    from apps.contracts.services import transition_contract_status

    all_requests = contract.signature_requests.all()
    if not all_requests.exists():
        return

    all_signed = all(
        req.status == SignatureRequest.Status.SIGNED
        for req in all_requests
    )

    if all_signed and contract.status == "pending_signature":
        transition_contract_status(contract, "active")
        logger.info(
            "All signatures collected for contract %s; status set to active",
            contract.contract_number,
        )
