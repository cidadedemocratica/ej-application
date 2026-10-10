import logging

from allauth.account.adapter import DefaultAccountAdapter
from allauth.core import context
from allauth.core.exceptions import ImmediateHttpResponse
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.shortcuts import redirect
from django.utils.http import url_has_allowed_host_and_scheme
from django.utils.translation import gettext_lazy as _

from ej_govbr.constants import GOVBR_PROVIDER_ID


User = get_user_model()
log = logging.getLogger("ej")


def _sociallogin_has_verified_email(sociallogin):
    user = sociallogin.user
    return bool(user.email) and any(
        address.verified and address.email.lower() == user.email.lower()
        for address in sociallogin.email_addresses
    )


class SocialAccountAdapter(DefaultSocialAccountAdapter):
    def is_auto_signup_allowed(self, request, sociallogin):
        if sociallogin.account.provider == GOVBR_PROVIDER_ID:
            return _sociallogin_has_verified_email(sociallogin)
        return super().is_auto_signup_allowed(request, sociallogin)

    def pre_social_login(self, request, sociallogin):
        user = sociallogin.user
        if user.id:
            return
        if not user.email:
            return
        if (
            sociallogin.account.provider == GOVBR_PROVIDER_ID
            and not _sociallogin_has_verified_email(sociallogin)
        ):
            return

        try:
            user = User.objects.get(email=user.email)
            sociallogin.connect(request, user)
        except User.DoesNotExist:
            pass
        except Exception as e:
            log.exception("Social adapter failure - {}".format(e))

    def populate_user(self, request, sociallogin, data):
        user = super().populate_user(request, sociallogin, data)
        if sociallogin.account.provider == GOVBR_PROVIDER_ID:
            user.name = data.get("name") or ""
        return user

    def on_authentication_error(
        self, request, provider, error=None, exception=None, extra_context=None
    ):
        if getattr(provider, "id", None) == GOVBR_PROVIDER_ID:
            log.info("GOV.BR authentication error: %s", error)
            messages.error(
                request, _("Unable to sign in with GOV.BR. Please try again.")
            )
            raise ImmediateHttpResponse(redirect("auth:login"))
        return super().on_authentication_error(
            request,
            provider,
            error=error,
            exception=exception,
            extra_context=extra_context,
        )


class AccountAdapter(DefaultAccountAdapter):
    def is_safe_url(self, url):
        request = self.request or context.request
        if request is None:
            return False
        return url_has_allowed_host_and_scheme(
            url,
            allowed_hosts={request.get_host()},
            require_https=request.is_secure(),
        )

    def get_email_verification_redirect_url(self, email_address):
        request = self.request or context.request
        redirect_url = request.session.pop(
            "govbr_email_confirmation_next", None
        )
        if redirect_url and url_has_allowed_host_and_scheme(
            redirect_url,
            allowed_hosts={request.get_host()},
            require_https=request.is_secure(),
        ):
            return redirect_url
        return super().get_email_verification_redirect_url(email_address)
