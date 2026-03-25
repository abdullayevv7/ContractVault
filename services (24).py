"""
Business logic services for approvals app.
"""
import logging

from django.db import transaction
from django.utils import timezone

from utils.exceptions import ApprovalFlowError
from .models import ApprovalWorkflow, ApprovalStep, ApprovalRequest

logger = logging.getLogger(__name__)


def get_workflow_for_contract(contract):
    """
    Determine the appropriate approval workflow for a contract.

    Priority:
    1. Workflow matching contract type and value range
    2. Workflow matching contract type
    3. Default workflow for the organization
    """
    org = contract.organization

    # Try to match by contract type and value range
    if contract.contract_type and contract.total_value:
        workflow = ApprovalWorkflow.objects.filter(
            organization=org,
            contract_type=contract.contract_type,
            is_active=True,
            min_value_threshold__lte=contract.total_value,
        ).filter(
            models__isnull=True
        ).first()

        # Simpler query without complex value range
        workflow = ApprovalWorkflow.objects.filter(
            organization=org,
            contract_type=contract.contract_type,
            is_active=True,
        ).first()

        if workflow:
            return workflow

    # Try contract type match only
    if contract.contract_type:
        workflow = ApprovalWorkflow.objects.filter(
            organization=org,
            contract_type=contract.contract_type,
            is_active=True,
        ).first()
        if workflow:
            return workflow

    # Fall back to default workflow
    workflow = ApprovalWorkflow.objects.filter(
        organization=org,
        is_default=True,
        is_active=True,
    ).first()

    if not workflow:
        # Try any active workflow
        workflow = ApprovalWorkflow.objects.filter(
            organization=org,
            is_active=True,
        ).first()

    return workflow


@transaction.atomic
def create_approval_request(contract, submitted_by):
    """
    Create a new approval request for a contract.

    Args:
        contract: Contract instance
        submitted_by: User submitting for approval

    Returns:
        ApprovalRequest instance

    Raises:
        ApprovalFlowError: If no workflow is found
    """
    workflow = get_workflow_for_contract(contract)
    if not workflow:
        raise ApprovalFlowError(
            "No approval workflow configured for this contract type. "
            "Please ask an administrator to create one."
        )

    first_step = workflow.steps.order_by("order").first()
    if not first_step:
        raise ApprovalFlowError(
            f"Workflow '{workflow.name}' has no approval steps configured."
        )

    # Cancel any existing pending requests for this contract
    ApprovalRequest.objects.filter(
        contract=contract,
        status__in=[
            ApprovalRequest.Status.PENDING,
            ApprovalRequest.Status.IN_PROGRESS,
        ],
    ).update(status=ApprovalRequest.Status.CANCELLED)

    approval_request = ApprovalRequest.objects.create(
        contract=contract,
        workflow=workflow,
        current_step=first_step,
        status=ApprovalRequest.Status.IN_PROGRESS,
        submitted_by=submitted_by,
    )

    # Send notification to the first approver
    _notify_approver(approval_request, first_step)

    logger.info(
        "Created approval request %s for contract %s using workflow %s",
        approval_request.id,
        contract.contract_number,
        workflow.name,
    )
    return approval_request


@transaction.atomic
def process_approval_decision(approval_request, user, decision, comments=""):
    """
    Process an approve or reject decision on an approval request.

    Args:
        approval_request: ApprovalRequest instance
        user: User making the decision
        decision: "approve" or "reject"
        comments: Optional comments

    Returns:
        Updated ApprovalRequest instance

    Raises:
        ApprovalFlowError: If the decision cannot be processed
    """
    if approval_request.status not in [
        ApprovalRequest.Status.IN_PROGRESS,
        ApprovalRequest.Status.PENDING,
    ]:
        raise ApprovalFlowError(
            f"Cannot process decision on a request with status '{approval_request.status}'."
        )

    current_step = approval_request.current_step
    if not current_step:
        raise ApprovalFlowError("No current step found for this approval request.")

    # Verify the user can approve this step
    if not _can_user_approve_step(user, current_step):
        raise ApprovalFlowError(
            "You are not authorized to approve or reject this step."
        )

    # Record the decision
    decision_record = {
        "step_id": str(current_step.id),
        "step_name": current_step.name,
        "step_order": current_step.order,
        "user_id": str(user.id),
        "user_name": user.get_full_name(),
        "decision": decision,
        "comments": comments,
        "timestamp": timezone.now().isoformat(),
    }

    history = approval_request.decision_history or []
    history.append(decision_record)
    approval_request.decision_history = history

    if decision == "reject":
        approval_request.status = ApprovalRequest.Status.REJECTED
        approval_request.completed_at = timezone.now()
        approval_request.save()

        # Transition contract back to rejected
        from apps.contracts.services import transition_contract_status
        transition_contract_status(approval_request.contract, "rejected", user)

        logger.info(
            "Approval request %s rejected by %s at step %s",
            approval_request.id, user, current_step.name,
        )
    elif decision == "approve":
        # Move to the next step
        next_step = (
            approval_request.workflow.steps
            .filter(order__gt=current_step.order)
            .order_by("order")
            .first()
        )

        if next_step:
            approval_request.current_step = next_step
            approval_request.save()
            _notify_approver(approval_request, next_step)
            logger.info(
                "Approval request %s advanced to step %s by %s",
                approval_request.id, next_step.name, user,
            )
        else:
            # All steps completed - fully approved
            approval_request.status = ApprovalRequest.Status.APPROVED
            approval_request.completed_at = timezone.now()
            approval_request.save()

            # Transition contract to approved
            from apps.contracts.services import transition_contract_status
            transition_contract_status(approval_request.contract, "approved", user)

            logger.info(
                "Approval request %s fully approved. Contract %s is now approved.",
                approval_request.id,
                approval_request.contract.contract_number,
            )

    return approval_request


def _can_user_approve_step(user, step):
    """Check if a user is authorized to approve a given step."""
    if user.is_superuser:
        return True

    # Check direct approver assignment
    if step.approver and step.approver == user:
        return True

    # Check role-based approval
    if step.approver_role and user.role == step.approver_role:
        return True

    # If no specific approver is set, any user with approval permission can approve
    if not step.approver and not step.approver_role:
        return user.has_permission("can_approve_contracts")

    return False


def _notify_approver(approval_request, step):
    """Send notification to the approver for a step."""
    from apps.notifications.tasks import send_approval_notification

    try:
        send_approval_notification.delay(
            str(approval_request.id),
            str(step.id),
        )
    except Exception:
        logger.exception(
            "Failed to send approval notification for request %s step %s",
            approval_request.id,
            step.id,
        )
