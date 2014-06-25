from django import template
from django.conf import settings

register = template.Library()

ALLOWED_VALUES = ("CELERY_LOGFILE",)

@register.filter
def from_settings(name):
    """ Returns an allowed settings value.
    """
    if name in ALLOWED_VALUES:
        return getattr(settings, name, '')
    else:
        return ''
