"""
Celery configuration for ContractVault.
"""
import os

from celery import Celery
from celery.schedules import crontab

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.production")

app = Celery("contractvault")

app.config_from_object("django.conf:settings", namespace="CELERY")

app.autodiscover_tasks()

# Periodic tasks schedule
app.conf.beat_schedule = {
    "check-contract-expirations-daily": {
        "task": "apps.contracts.tasks.check_contract_expirations",
        "schedule": crontab(hour=8, minute=0),
        "kwargs": {},
    },
    "send-pending-notification-digests": {
        "task": "apps.notifications.tasks.send_notification_digest",
        "schedule": crontab(hour=9, minute=0),
        "kwargs": {},
    },
    "cleanup-expired-signature-requests": {
        "task": "apps.signatures.services.cleanup_expired_requests",
        "schedule": crontab(hour=0, minute=0),
        "kwargs": {},
    },
}


@app.task(bind=True, ignore_result=True)
def debug_task(self):
    """Debug task to verify Celery is running."""
    print(f"Request: {self.request!r}")
