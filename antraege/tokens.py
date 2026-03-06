import uuid

from django.conf import settings
from django.core import signing

from .models import Anfrage


TOKEN_SALT = "antraege.approval-token"


class TokenValidationError(Exception):
    pass


def _token_max_age_seconds():
    return int(getattr(settings, "ANFRAGE_TOKEN_MAX_AGE_SECONDS", 60 * 60 * 24 * 7))


def make_token_pair():
    raw_token = uuid.uuid4().hex
    public_token = signing.dumps({"t": raw_token}, salt=TOKEN_SALT)
    return raw_token, public_token


def sign_existing_raw_token(raw_token):
    return signing.dumps({"t": raw_token}, salt=TOKEN_SALT)


def resolve_anfrage_from_public_token(public_token):
    try:
        data = signing.loads(
            public_token,
            salt=TOKEN_SALT,
            max_age=_token_max_age_seconds(),
        )
    except signing.BadSignature as exc:
        raise TokenValidationError("invalid or expired token") from exc

    raw_token = data.get("t")
    if not raw_token:
        raise TokenValidationError("missing token payload")

    anfrage = Anfrage.objects.filter(token=raw_token).order_by("-id").first()
    if anfrage is None:
        raise TokenValidationError("request token no longer exists")
    return anfrage
