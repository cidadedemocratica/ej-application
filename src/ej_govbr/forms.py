from allauth.account.app_settings import EmailVerificationMethod
from allauth.account.internal.flows.signup import complete_signup
from allauth.socialaccount.forms import SignupForm as AllauthSocialSignupForm
from allauth.socialaccount.internal.flows.login import record_authentication
from django import forms
from django.core.exceptions import ValidationError
from django.utils.http import url_has_allowed_host_and_scheme
from django.utils.translation import gettext_lazy as _

from ej_users.forms import PrivacyPolicyWidget, TermsWidget

from .constants import GOVBR_PROVIDER_ID


class SignupFormRouter:
    @staticmethod
    def get_form_class(sociallogin):
        if sociallogin.account.provider == GOVBR_PROVIDER_ID:
            return GovBrSignupForm
        return AllauthSocialSignupForm

    def __new__(cls, *args, **kwargs):
        form_class = cls.get_form_class(kwargs["sociallogin"])
        return form_class(*args, **kwargs)


class GovBrSignupForm(AllauthSocialSignupForm):
    agree_with_terms = forms.BooleanField(
        label=_("Terms of use"), widget=TermsWidget, required=True
    )
    agree_with_privacy_policy = forms.BooleanField(
        label=_("Privacy policy"), widget=PrivacyPolicyWidget, required=True
    )

    def validate_unique_email(self, value):
        value = super().validate_unique_email(value)
        if self.account_already_exists:
            raise ValidationError(
                _("An account already exists with this email address.")
            )
        return value

    def signup(self, request, user):
        user.agree_with_terms = self.cleaned_data["agree_with_terms"]
        user.agree_with_privacy_policy = self.cleaned_data[
            "agree_with_privacy_policy"
        ]
        user.save(
            update_fields=["agree_with_terms", "agree_with_privacy_policy"]
        )

    def try_save(self, request):
        user, response = super().try_save(request)
        if response:
            return user, response

        redirect_url = self.sociallogin.get_redirect_url(request)
        if redirect_url and url_has_allowed_host_and_scheme(
            redirect_url,
            allowed_hosts={request.get_host()},
            require_https=request.is_secure(),
        ):
            request.session["govbr_email_confirmation_next"] = redirect_url
        record_authentication(request, self.sociallogin)
        response = complete_signup(
            request,
            user=user,
            email_verification=EmailVerificationMethod.MANDATORY,
            redirect_url=redirect_url,
            signal_kwargs={"sociallogin": self.sociallogin},
        )
        return user, response
