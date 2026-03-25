"""
Celery tasks for contracts app.
Handles expiration alerts and periodic contract maintenance.
"""
import logging

from celery import shared_task
from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def check_contract_expirations(self):
    """
    Check for contracts nearing expiration and send alerts.
    Runs daily via Celery beat.
    """
    from .services import get_expiring_contracts, check_and_update_expired_contracts
    from apps.notifications.tasks import send_expiration_notification

    # First, update any contracts that have already expired
    expired_count = check_and_update_expired_contracts()
    logger.info("Updated %d expired contracts", expired_count)

    # Check for contracts expiring within configured thresholds
    thresholds = getattr(settings, "CONTRACT_EXPIRATION_ALERTS", [90, 60, 30, 14, 7, 1])

    total_alerts = 0
    for days in thresholds:
        contracts = get_expiring_contracts(days)
        for contract in contracts:
            days_left = contract.days_until_expiration
            if days_left is not None and days_left == days:
                send_expiration_notification.delay(
                    str(contract.id),
                    days_left,
                )
                total_alerts += 1

    logger.info(
        "Expiration check complete: %d expired, %d alerts sent",
        expired_count,
        total_alerts,
    )
    return {
        "expired_updated": expired_count,
        "alerts_sent": total_alerts,
    }


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def process_auto_renewals(self):
    """
    Process contracts that are set to auto-renew.
    """
    from .models import Contract
    from datetime import timedelta

    today = timezone.now().date()
    contracts = Contract.objects.filter(
        status=Contract.Status.ACTIVE,
        auto_renew=True,
        expiration_date__lte=today,
        renewal_period_days__isnull=False,
    )

    renewed_count = 0
    for contract in contracts:
        new_expiration = today + timedelta(days=contract.renewal_period_days)
        contract.expiration_date = new_expiration
        contract.renewal_date = today
        contract.save(update_fields=["expiration_date", "renewal_date", "updated_at"])
        renewed_count += 1
        logger.info(
            "Auto-renewed contract %s until %s",
            contract.contract_number,
            new_expiration,
        )

    return {"renewed_count": renewed_count}


@shared_task
def generate_contract_pdf_async(contract_id):
    """Generate a PDF for a contract asynchronously."""
    from .models import Contract
    from .services import generate_contract_pdf_file

    try:
        contract = Contract.objects.get(id=contract_id)
        pdf_path = generate_contract_pdf_file(contract)
        logger.info("Async PDF generated for contract %s", contract.contract_number)
        return {"contract_id": str(contract_id), "pdf_path": pdf_path}
    except Contract.DoesNotExist:
        logger.error("Contract %s not found for PDF generation", contract_id)
        return None
