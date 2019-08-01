from logging import getLogger

from django import forms
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.exceptions import ImproperlyConfigured
from django.utils.translation import ugettext_lazy as _

from ej.forms import PlaceholderForm
from . import models
from .exceptions import ApiError
from .rocket import rocket

log = getLogger("ej")
User = get_user_model()
PASSWORD_MSG = _(
    """Password for Rocket.Chat admin user.
It is important to configure your Rocket.Chat instance with a unique password since
this value will be stored in plain text into Django's own database."""
)


class RocketIntegrationForm(PlaceholderForm, forms.Form):
    """
    Form that asks basic configuration about a Rocket.Chat instance.
    """

    # URLFields explicitly disallow local domains (except for localhost)
    rocketchat_url = forms.CharField(
        label=_("Rocket.Chat URL"),
        help_text=_("Required URL for Rocket.Chat admin instance."),
        initial=settings.EJ_ROCKETCHAT_URL,
    )
    api_url = forms.CharField(
        label=_("Internal URL"),
        help_text=_("Optional URL used for communication with Rocket.Chat in the internal network."),
        required=False,
    )
    username = forms.CharField(label=_("Username"), help_text=_("Username for Rocket.Chat admin user."))

    password = forms.CharField(
        widget=forms.PasswordInput, required=False, label=_("Password"), help_text=PASSWORD_MSG
    )
    config = None

    def get_config(self):
        """
        Return Rocket.Chat config from form data.
        """
        if self.config is None:
            return self._clean_config()
        else:
            return self.config

    def full_clean(self):
        super().full_clean()

        try:
            self._clean_config(self.cleaned_data)
        except (AttributeError, ImproperlyConfigured, KeyError):
            pass

    def _clean_config(self, data):
        """
        Return a saved RCConfig instance from form data.
        """
        url = data["rocketchat_url"]
        api_url = data["api_url"] or url
        config = models.RCConfig(url=api_url)
        response = config.api_call(
            "login", payload={"username": data["username"], "password": data["password"]}, raises=False
        )
        if response.get("status") == "success":
            self.config = self._save_config(response["data"])
            return config
        elif response.get("error") in ("JSONDecodeError", "ConnectionError"):
            self.add_error("rocketchat_url", _("Error connecting to server"))
        elif response.get("error", "Unauthorized"):
            self.add_error("username", _("Invalid username or password"))
        else:
            log.error(f"Invalid response: {response}")
            self.add_error(None, _("Error registering on Rocket.Chat server"))

    def _save_config(self, data):
        url = self.cleaned_data["rocketchat_url"]
        api_url = self.cleaned_data["api_url"] or ""
        user_id = data["userId"]
        auth_token = data["authToken"]

        # Save config
        config, _ = models.RCConfig.objects.get_or_create(url=url)
        config.api_url = api_url
        config.admin_id = user_id
        config.admin_token = auth_token
        config.admin_username = self.cleaned_data["username"]
        config.admin_password = self.cleaned_data["password"]
        config.is_active = True
        config.save()
        return config


class CreateUsernameForm(PlaceholderForm, forms.ModelForm):
    """
    Asks user for a new username for its Rocket.Chat account.
    """

    class Meta:
        model = models.RCAccount
        fields = ["username"]

    def __init__(self, *args, user, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user

    def full_clean(self):
        super().full_clean()
        try:
            username = self.cleaned_data["username"].lstrip("@")
        except (KeyError, AttributeError):
            return
        try:
            self.instance = rocket.register(self.user, username)
        except ApiError as error:
            msg = error.args[0]
            error = msg.get("error", "")
            if f"{username} is already in use" in error:
                self.add_error("username", _("Username already in use."))
            elif f"{self.user.email} is already in use" in error:
                email = self.user.email
                msg = _(f"User with {email} e-mail already exists.")
                self.add_error("username", msg)
            else:
                raise
        else:
            rocket.login(self.user)
