from django.core.exceptions import ValidationError


def validate_afra_email(email: str) -> str:
    if not email or not email.endswith("@afra.lernsax.de"):
        raise ValidationError('Nur E-Mail-Adressen, die mit "@afra.lernsax.de" enden, sind zulässig.')
    return email
