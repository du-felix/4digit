import logging

from django.core.mail import send_mail as django_send_mail


logger = logging.getLogger(__name__)


def send_mail_logged(subject, body, from_email, recipients, suppress_exceptions=True):
    try:
        sent_count = django_send_mail(
            subject=subject,
            message=body,
            from_email=from_email,
            recipient_list=recipients,
            fail_silently=False,
        )
        if sent_count == 0:
            logger.warning(
                "Mail backend accepted call but sent_count=0",
                extra={"subject": subject, "recipients": recipients},
            )
        return sent_count
    except Exception:
        logger.exception(
            "Mail send failed",
            extra={"subject": subject, "recipients": recipients},
        )
        if suppress_exceptions:
            return 0
        raise
