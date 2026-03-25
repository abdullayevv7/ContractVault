"""
Business logic services for the amendments app.
Handles amendment execution and application to the parent contract.
"""
import logging

from django.db import transaction
from django.utils import timezone

from utils.exceptions import ContractStateError
from .models import Amendment, AmendmentClause

logger = logging.getLogger(__name__)

VALID_AMENDMENT_TRANSITIONS = {
    "draft": ["pending_approval", "cancelled"],
    "pending_approval": ["approved", "rejected", "draft"],
    "approved": ["pending_signature", "executed", "cancelled"],
    "rejected": ["draft"],
    "pending_signature": ["executed", "approved"],
    "executed": [],
    "cancelled": [],
}


def transition_amendment_status(amendment, new_status, user=None):
    """
    Transition an amendment to a new status with validation.

    Args:
        amendment: Amendment instance
        new_status: target status string
        user: User performing the transition

    Raises:
        ContractStateError: if the transition is invalid
    """
    current = amendment.status
    allowed = VALID_AMENDMENT_TRANSITIONS.get(current, [])

    if new_status not in allowed:
        raise ContractStateError(
            f"Cannot transition amendment from '{current}' to '{new_status}'. "
            f"Allowed: {', '.join(allowed) if allowed else 'none'}."
        )

    amendment.status = new_status

    if new_status == "executed":
        amendment.executed_at = timezone.now()
    if new_status == "approved" and user:
        amendment.approved_by = user

    amendment.save()

    logger.info(
        "Amendment %s transitioned from %s to %s by %s",
        amendment.amendment_number,
        current,
        new_status,
        user,
    )
    return amendment


@transaction.atomic
def execute_amendment(amendment, user):
    """
    Execute an approved amendment: apply its changes to the parent contract
    and create a version snapshot.

    Args:
        amendment: Amendment instance (must be in 'approved' or 'pending_signature')
        user: User executing the amendment

    Returns:
        Updated Contract instance

    Raises:
        ContractStateError: if the amendment cannot be executed
    """
    from apps.contracts.models import ContractClause
    from apps.contracts.services import create_contract_version

    if amendment.status not in ("approved", "pending_signature"):
        raise ContractStateError(
            "Only approved amendments can be executed."
        )

    contract = amendment.contract

    # Create a version snapshot before applying changes
    create_contract_version(
        contract,
        user,
        f"Pre-amendment snapshot before {amendment.amendment_number}",
    )

    # Apply financial changes
    if amendment.new_value is not None:
        contract.total_value = amendment.new_value

    # Apply date changes
    if amendment.new_expiration is not None:
        contract.expiration_date = amendment.new_expiration

    contract.updated_by = user
    contract.save()

    # Apply clause changes
    for clause_change in amendment.clause_changes.all():
        if clause_change.change_type == AmendmentClause.ChangeType.ADDED:
            ContractClause.objects.create(
                contract=contract,
                title=clause_change.title,
                content=clause_change.new_content,
                clause_type="custom",
                order=clause_change.order,
                metadata={"added_by_amendment": str(amendment.id)},
            )
        elif clause_change.change_type == AmendmentClause.ChangeType.MODIFIED:
            if clause_change.original_clause:
                original = clause_change.original_clause
                original.content = clause_change.new_content
                original.metadata["last_amended_by"] = str(amendment.id)
                original.save()
        elif clause_change.change_type == AmendmentClause.ChangeType.REMOVED:
            if clause_change.original_clause:
                clause_change.original_clause.is_active = False
                clause_change.original_clause.save(update_fields=["is_active"])

    # Build structured changes summary
    changes = []
    if amendment.previous_value != amendment.new_value:
        changes.append({
            "field": "total_value",
            "old_value": str(amendment.previous_value),
            "new_value": str(amendment.new_value),
        })
    if amendment.previous_expiration != amendment.new_expiration:
        changes.append({
            "field": "expiration_date",
            "old_value": str(amendment.previous_expiration),
            "new_value": str(amendment.new_expiration),
        })
    amendment.changes_summary = changes

    # Transition the amendment to executed
    transition_amendment_status(amendment, "executed", user)

    # Create a post-amendment version snapshot
    create_contract_version(
        contract,
        user,
        f"Applied amendment {amendment.amendment_number}",
    )

    logger.info(
        "Executed amendment %s on contract %s",
        amendment.amendment_number,
        contract.contract_number,
    )
    return contract
