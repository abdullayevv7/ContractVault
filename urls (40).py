"""
Business logic services for contracts app.
"""
import logging
from datetime import date

from django.db import transaction
from django.utils import timezone

from utils.exceptions import ContractStateError
from utils.pdf_generator import save_contract_pdf

logger = logging.getLogger(__name__)

# Valid state transitions
VALID_TRANSITIONS = {
    "draft": ["pending_approval", "archived"],
    "pending_approval": ["approved", "rejected", "draft"],
    "approved": ["pending_signature", "active", "archived"],
    "rejected": ["draft"],
    "pending_signature": ["active", "approved"],
    "active": ["expired", "terminated", "renewed", "archived"],
    "expired": ["renewed", "archived"],
    "terminated": ["archived"],
    "renewed": ["active", "archived"],
    "archived": [],
}


def transition_contract_status(contract, new_status, user=None):
    """
    Transition a contract to a new status with validation.

    Args:
        contract: Contract instance
        new_status: Target status string
        user: User performing the transition

    Raises:
        ContractStateError: If the transition is invalid
    """
    current_status = contract.status
    allowed = VALID_TRANSITIONS.get(current_status, [])

    if new_status not in allowed:
        raise ContractStateError(
            f"Cannot transition from '{current_status}' to '{new_status}'. "
            f"Allowed transitions: {', '.join(allowed) if allowed else 'none'}."
        )

    contract.status = new_status
    if user:
        contract.updated_by = user

    if new_status == "active" and not contract.effective_date:
        contract.effective_date = timezone.now().date()

    if new_status == "terminated":
        contract.termination_date = timezone.now().date()

    contract.save()
    logger.info(
        "Contract %s transitioned from %s to %s by %s",
        contract.contract_number,
        current_status,
        new_status,
        user,
    )
    return contract


@transaction.atomic
def create_contract_version(contract, user, change_summary=""):
    """
    Create a version snapshot of the current contract state.

    Args:
        contract: Contract instance
        user: User creating the version
        change_summary: Description of changes

    Returns:
        ContractVersion instance
    """
    from .models import ContractVersion

    content_snapshot = {
        "title": contract.title,
        "description": contract.description,
        "status": contract.status,
        "total_value": str(contract.total_value) if contract.total_value else None,
        "effective_date": str(contract.effective_date) if contract.effective_date else None,
        "expiration_date": str(contract.expiration_date) if contract.expiration_date else None,
        "clauses": list(
            contract.clauses.values("title", "content", "clause_type", "order")
        ),
        "parties": list(
            contract.parties.values("name", "email", "role", "organization_name")
        ),
        "compliance_requirements": contract.compliance_requirements,
        "tags": contract.tags,
    }

    version = ContractVersion.objects.create(
        contract=contract,
        version_number=contract.version,
        title=contract.title,
        description=contract.description,
        content_snapshot=content_snapshot,
        change_summary=change_summary,
        created_by=user,
    )

    contract.version += 1
    contract.updated_by = user
    contract.save(update_fields=["version", "updated_by", "updated_at"])

    logger.info(
        "Created version %d for contract %s",
        version.version_number,
        contract.contract_number,
    )
    return version


def submit_for_approval(contract, user):
    """
    Submit a contract for approval.
    Creates an approval request using the appropriate workflow.
    """
    from apps.approvals.services import create_approval_request

    transition_contract_status(contract, "pending_approval", user)
    create_contract_version(contract, user, "Submitted for approval")

    approval_request = create_approval_request(contract, user)
    return approval_request


def generate_contract_pdf_file(contract):
    """Generate and attach a PDF to the contract."""
    try:
        pdf_path = save_contract_pdf(contract)
        contract.pdf_file = pdf_path
        contract.save(update_fields=["pdf_file"])
        logger.info("PDF generated for contract %s", contract.contract_number)
        return pdf_path
    except Exception:
        logger.exception("Failed to generate PDF for contract %s", contract.contract_number)
        raise


def check_and_update_expired_contracts():
    """
    Check all active contracts and update expired ones.
    Called by the Celery beat schedule.
    """
    from .models import Contract

    today = timezone.now().date()
    expired_contracts = Contract.objects.filter(
        status=Contract.Status.ACTIVE,
        expiration_date__lt=today,
    )

    count = 0
    for contract in expired_contracts:
        contract.status = Contract.Status.EXPIRED
        contract.save(update_fields=["status", "updated_at"])
        count += 1
        logger.info("Contract %s has expired", contract.contract_number)

    return count


def get_expiring_contracts(days_threshold):
    """
    Get contracts expiring within the given number of days.

    Args:
        days_threshold: Number of days to look ahead

    Returns:
        QuerySet of contracts
    """
    from .models import Contract
    from datetime import timedelta

    today = timezone.now().date()
    threshold_date = today + timedelta(days=days_threshold)

    return Contract.objects.filter(
        status=Contract.Status.ACTIVE,
        expiration_date__lte=threshold_date,
        expiration_date__gte=today,
    ).select_related("organization", "contract_type", "created_by")


def duplicate_contract(contract, user):
    """
    Create a duplicate of an existing contract as a new draft.

    Args:
        contract: Contract to duplicate
        user: User performing the duplication

    Returns:
        New Contract instance
    """
    from .models import Contract, ContractParty, ContractClause

    with transaction.atomic():
        new_contract = Contract(
            organization=contract.organization,
            title=f"Copy of {contract.title}",
            description=contract.description,
            contract_type=contract.contract_type,
            status=Contract.Status.DRAFT,
            priority=contract.priority,
            total_value=contract.total_value,
            currency=contract.currency,
            auto_renew=contract.auto_renew,
            renewal_period_days=contract.renewal_period_days,
            compliance_requirements=contract.compliance_requirements,
            tags=contract.tags,
            metadata=contract.metadata,
            created_by=user,
        )
        new_contract.save()

        for party in contract.parties.all():
            ContractParty.objects.create(
                contract=new_contract,
                name=party.name,
                email=party.email,
                phone=party.phone,
                organization_name=party.organization_name,
                role=party.role,
                address=party.address,
                is_primary=party.is_primary,
            )

        for clause in contract.clauses.all():
            ContractClause.objects.create(
                contract=new_contract,
                title=clause.title,
                content=clause.content,
                clause_type=clause.clause_type,
                order=clause.order,
                metadata=clause.metadata,
            )

    logger.info(
        "Duplicated contract %s as %s by %s",
        contract.contract_number,
        new_contract.contract_number,
        user,
    )
    return new_contract
