from allauth.account.internal.flows.login import (
    AUTHENTICATION_METHODS_SESSION_KEY,
)
from django.contrib.auth.signals import user_logged_in
from django.dispatch import receiver

from .constants import GOVBR_AUTHENTICATED_SESSION_KEY, GOVBR_PROVIDER_ID


@receiver(user_logged_in)
def mark_govbr_session(sender, user, request, **kwargs):
    methods = request.session.get(AUTHENTICATION_METHODS_SESSION_KEY, [])
    if (
        methods
        and methods[-1].get("method") == "socialaccount"
        and methods[-1].get("provider") == GOVBR_PROVIDER_ID
    ):
        request.session[GOVBR_AUTHENTICATED_SESSION_KEY] = True
