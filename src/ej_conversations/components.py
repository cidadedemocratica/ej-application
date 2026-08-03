from django.contrib import messages
from django.utils.html import escape


MEMBER_TOAST_TAG = "member-toast"


def member_toast(request, msg, **kwargs):
    """
    Insert a conversation member toast message in Django's message queue.
    """
    extra_tags = kwargs.pop("extra_tags", "")
    extra_tags = " ".join(tag for tag in [MEMBER_TOAST_TAG, extra_tags] if tag)
    messages.info(request, escape(msg), extra_tags=extra_tags, **kwargs)
