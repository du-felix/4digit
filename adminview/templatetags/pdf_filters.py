import re

from django import template

register = template.Library()


@register.filter
def fmt_dates(value):
    """
    Convert ISO dates (YYYY-MM-DD) inside a string to European format (DD.MM.YYYY).
    Used to format the raw unterricht text stored in Anfrage.unterricht before
    rendering it inside the PDF template.
    """
    if not value:
        return value
    return re.sub(
        r'(\d{4})-(\d{2})-(\d{2})',
        lambda m: f"{m.group(3)}.{m.group(2)}.{m.group(1)}",
        value,
    )
