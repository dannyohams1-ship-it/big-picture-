from django.core.mail import send_mail
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

def notify_team_of_lead(lead):
    """
    Notify your internal team when a user requests human help.
    """
    subject = f"🧭 New Chat Lead: {lead.email}"
    body = (
        f"Name: {lead.name or 'N/A'}\n"
        f"Email: {lead.email}\n"
        f"Phone: {lead.phone or 'N/A'}\n"
        f"Message: {lead.message or '—'}\n"
        f"Opt-in: {'Yes' if lead.opt_in else 'No'}\n"
        f"Created: {lead.created_at:%Y-%m-%d %H:%M}\n"
    )
    recipients = getattr(settings, "LEAD_NOTIFICATION_EMAILS", [])

    if not recipients:
        logger.warning("No LEAD_NOTIFICATION_EMAILS configured — skipping email alert.")
        return

    try:
        send_mail(subject, body, settings.DEFAULT_FROM_EMAIL, recipients)
        logger.info(f"Lead notification sent for {lead.email}")
    except Exception as e:
        logger.exception(f"Failed to send lead notification: {e}")
