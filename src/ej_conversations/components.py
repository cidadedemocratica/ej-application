from django.contrib import messages
from django.utils.html import escape


def member_toast(request, msg, **kwargs):
    """
    Insert a conversation member toast message in Django's message queue.
    """
    messages.info(request, escape(msg), **kwargs)
