from django import template
from django.conf import settings
import os

register = template.Library()

@register.filter
def media_url_or_full(url):
    if url.startswith('http'):
        return url
    return os.path.join(settings.MEDIA_URL, url)
