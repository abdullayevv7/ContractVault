"""
Celery tasks for the notifications app.
Handles async email delivery and notification digests.
"""
import logging

from celery import shared_task
from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils import timezone

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=120)
def send_expiration_notification(self, contract_id, days_remaining):
    """
    Send an expiration warning notification for a contract.

    Args:
        contract_id: UUID of the contract
        days_remaining: Number of days until expiration
    """
    from apps.contracts.models import Contract
    from .models import Notification

    try:
        contract = Contract.objects.select_related(
            "organization", "created_by",
        ).get(id=contract_id)
    except Contract.DoesNotExist:
        logger.error("Contract %s not found for expiration notification", contract_id)
        return

    # Determine recipients: contract creator and org admins
    recipients = set()
    if contract.created_by:
        recipients.add(contract.created_by)

    from apps.accounts.models import User
    org_admins = User.objects.filter(
        organization=contract.organization,
        role__role_type="admin",
        is_active=True,
    )
    recipients.update(org_admins)

    subject = (
        f"Contract Expiring in {days_remaining} Day{'s' if days_remaining != 1 else ''}: "
        f"{contract.contract_number}"
    )
    message = (
        f"Contract \"{contract.title}\" ({contract.contract_number}) "
        f"will expire on {contract.expiration_date.strftime('%B %d, %Y')}. "
        f"That is {days_remaining} day{'s' if days_remaining != 1 else ''} from now."
    )

    for recipient in recipients:
        Notification.objects.create(
            recipient=recipient,
            notification_type=Notification.NotificationType.CONTRACT_EXPIRING,
            title=subject,
            message=message,
            priority=(
                Notification.Priority.URGENT if days_remaining <= 7
                else Notification.Priority.HIGH if days_remaining <= 30
                else Notification.Priority.MEDIUM
            ),
            contract=contract,
            action_url=f"/contracts/{contract.id}",
            metadata={"days_remaining": days_remaining},
        )

        # Send email if the user has email notifications enabled
        if recipient.email_notifications:
            _send_notification_email(
                recipient.email,
                subject,
                message,
                contract,
            )

    logger.info(
        "Sent expiration notifications for contract %s (%d days remaining) to %d recipients",
        contract.contract_number,
        days_remaining,
        len(recipients),
    )


@shared_task(bind=True, max_retries=3, default_retry_delay=120)
def send_approval_notification(self, approval_request_id, step_id):
    """
    Send a notification to the approver for a specific approval step.

    Args:
        approval_request_id: UUID of the ApprovalRequest
        step_id: UUID of the ApprovalStep
    """
    from apps.approvals.models import ApprovalRequest, ApprovalStep
    from .models import Notification

    try:
        approval_request = ApprovalRequest.objects.select_related(
            "contract", "workflow",
        ).get(id=approval_request_id)
        step = ApprovalStep.objects.select_related(
            "approver", "approver_role",
        ).get(id=step_id)
    except (ApprovalRequest.DoesNotExist, ApprovalStep.DoesNotExist):
        logger.error(
            "ApprovalRequest %s or step %s not found",
            approval_request_id,
            step_id,
        )
        return

    contract = approval_request.contract

    # Determine the approver(s)
    approvers = []
    if step.approver:
        approvers.append(step.approver)
    elif step.approver_role:
        from apps.accounts.models import User
        role_users = User.objects.filter(
            role=step.approver_role,
            organization=contract.organization,
            is_active=True,
        )
        approvers.extend(role_users)

    subject = f"Approval Required: {contract.contract_number} - {contract.title}"
    message = (
        f"Your approval is required for contract \"{contract.title}\" "
        f"({contract.contract_number}). "
        f"Step: {step.name}. "
        f"Workflow: {approval_request.workflow.name}."
    )

    for approver in approvers:
        Notification.objects.create(
            recipient=approver,
            notification_type=Notification.NotificationType.APPROVAL_REQUESTED,
            title=subject,
            message=message,
            priority=Notification.Priority.HIGH,
            contract=contract,
            action_url=f"/approvals/{approval_request.id}",
            metadata={
                "approval_request_id": str(approval_request.id),
                "step_id": str(step.id),
                "step_name": step.name,
            },
        )

        if approver.email_notifications:
            _send_notification_email(
                approver.email,
                subject,
                message,
                contract,
            )

    logger.info(
        "Sent approval notifications for request %s step '%s' to %d approvers",
        approval_request.id,
        step.name,
        len(approvers),
    )


@shared_task
def send_notification_digest():
    """
    Send daily digest emails to users who have opted in.
    Aggregates unread notifications from the past 24 hours.
    """
    from .models import Notification, NotificationPreference
    from datetime import timedelta

    cutoff = timezone.now() - timedelta(hours=24)

    prefs = NotificationPreference.objects.filter(
        daily_digest=True,
    ).select_related("user")

    sent_count = 0
    for pref in prefs:
        unread = Notification.objects.filter(
            recipient=pref.user,
            is_read=False,
            created_at__gte=cutoff,
        ).order_by("-created_at")

        if not unread.exists():
            continue

        items = []
        for n in unread[:20]:
            items.append(f"- [{n.get_notification_type_display()}] {n.title}")

        body = (
            f"Hi {pref.user.get_full_name()},\n\n"
            f"You have {unread.count()} unread notifications:\n\n"
            + "\n".join(items)
            + "\n\nVisit ContractVault to view details."
        )

        try:
            send_mail(
                subject=f"ContractVault Daily Digest - {unread.count()} notifications",
                message=body,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[pref.user.email],
                fail_silently=False,
            )
            sent_count += 1
        except Exception:
            logger.exception("Failed to send digest to %s", pref.user.email)

    logger.info("Sent %d daily digest emails", sent_count)
    return {"digests_sent": sent_count}


def _send_notification_email(to_email, subject, message, contract=None):
    """Helper to send a single notification email."""
    try:
        full_message = message
        if contract:
            frontend_url = getattr(settings, "FRONTEND_URL", "http://localhost:3000")
            full_message += (
                f"\n\nView contract: {frontend_url}/contracts/{contract.id}"
            )
        full_message += "\n\n-- ContractVault"

        send_mail(
            subject=f"ContractVault: {subject}",
            message=full_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[to_email],
            fail_silently=True,
        )
    except Exception:
        logger.exception("Failed to send notification email to %s", to_email)
