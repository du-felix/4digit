from django.utils import timezone

from .models import Antrag, Anfrage


class WorkflowTransitionError(Exception):
    pass


ANTRAG_ALLOWED_TRANSITIONS = {
    Antrag.STATUS_IN_PROGRESS: {Antrag.STATUS_ACCEPTED, Antrag.STATUS_DECLINED},
    Antrag.STATUS_ACCEPTED: set(),
    Antrag.STATUS_DECLINED: set(),
}

ANFRAGE_ALLOWED_TRANSITIONS = {
    Anfrage.NOT_RESPONDED: {Anfrage.ACCEPTED, Anfrage.DECLINED},
    Anfrage.ACCEPTED: set(),
    Anfrage.DECLINED: set(),
}


def transition_antrag(antrag, new_status):
    allowed = ANTRAG_ALLOWED_TRANSITIONS.get(antrag.status, set())
    if new_status not in allowed:
        raise WorkflowTransitionError(f"Invalid Antrag transition: {antrag.status} -> {new_status}")
    antrag.status = new_status
    antrag.save(update_fields=["status"])


def transition_anfrage(anfrage, new_response, reason=None):
    allowed = ANFRAGE_ALLOWED_TRANSITIONS.get(anfrage.response, set())
    if new_response not in allowed:
        raise WorkflowTransitionError(f"Invalid Anfrage transition: {anfrage.response} -> {new_response}")
    anfrage.response = new_response
    anfrage.responded_at = timezone.now()
    if reason is not None:
        anfrage.reason = reason
        anfrage.save(update_fields=["response", "responded_at", "reason"])
    else:
        anfrage.save(update_fields=["response", "responded_at"])


def ensure_pending(anfrage):
    if anfrage.response != Anfrage.NOT_RESPONDED:
        raise WorkflowTransitionError("Anfrage already processed")


def all_requests_responded(antrag):
    return not Anfrage.objects.filter(antrag=antrag, response=Anfrage.NOT_RESPONDED).exists()
