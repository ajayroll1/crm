from django import template
from django.core.files.storage import default_storage
from django.conf import settings

register = template.Library()

@register.filter
def get_item(dictionary, key):
    """Get item from dictionary by key"""
    if dictionary is None:
        return None
    return dictionary.get(key, [])

@register.filter
def media_url(path):
    """Return an absolute media URL for a stored file path."""
    if not path:
        return ''
    path_str = str(path)
    if path_str.startswith(('http://', 'https://')):
        return path_str
    normalized = path_str.lstrip('/')
    try:
        return default_storage.url(normalized)
    except Exception:
        return f"{settings.MEDIA_URL}{normalized}"

