from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.validators import RegexValidator
from django.db import models
from django.utils.translation import ugettext_lazy as _

from ej.utils import JSONField
from .manager import RCConfigManager
from .validators import WhiteListedURLValidator, requires_setup_for_blank

CAN_LOGIN_PERM = "ej_rocketchat.can_create_account"


class RCAccount(models.Model):
    """
    Register subscription of a EJ user into rocket
    """

    config = models.ForeignKey("RCConfig", on_delete=models.CASCADE)
    user = models.OneToOneField(
        get_user_model(), on_delete=models.CASCADE, related_name="rocketchat_subscription"
    )
    username = models.CharField(
        _("Username"),
        max_length=50,
        help_text=_(
            "Username that identifies you in the Rocket.Chat platform.\n"
            "Use small names with letters and dashes such as @my-user-name."
        ),
        validators=[
            RegexValidator(
                r"^\@?(\w+-)*\w+$", message=_("Username must consist of letters, numbers and dashes.")
            )
        ],
    )
    password = models.CharField(_("Password"), max_length=50, blank=True)
    user_rc_email = models.EmailField(_("E-mail used to create RC account"))
    user_rc_id = models.CharField(_("Rocketchat user id"), max_length=50)
    auth_token = models.CharField(_("Rocketchat user token"), max_length=50, blank=True)
    account_data = JSONField(
        _("Account data"), null=True, blank=True, help_text=_("JSON-encoded data for user account.")
    )
    is_active = models.BooleanField(
        _("Is user active?"), default=True, help_text=_("True for active Rocket.Chat accounts.")
    )
    rc_username = property(lambda self: f"ej-user-{self.user.id}")
    can_login_perm = CAN_LOGIN_PERM

    class Meta:
        verbose_name = _("Rocket.Chat Account")
        verbose_name_plural = _("Rocket.Chat Accounts")
        permissions = [(CAN_LOGIN_PERM.partition(".")[-1], _("Can login in the Rocket.Chat instance."))]

    def __str__(self):
        return f"{self.user} ({self.user_rc_id})"

    def update_info(self, commit=True):
        """
        Update user info from Rocket.Chat and user permissions.
        """
        config = RCConfig.objects.default_config()
        self.user_rc_id, self.auth_token = config.user_info(self.user)
        if commit:
            self.save()


class RCConfig(models.Model):
    """
    Store Rocket.Chat configuration.
    """

    url = models.URLField(
        _("Rocket.Chat URL"),
        default=settings.EJ_ROCKETCHAT_URL,
        help_text=_("Public URL in which the Rocket.Chat instance is installed."),
    )
    api_url = models.CharField(
        _("Rocket.Chat private URL"),
        blank=True,
        null=True,
        max_length=200,
        help_text=_(
            "A private URL used only for API calls. Can be used to override "
            "the public URL if Rocket.Chat is also available from an internal "
            "address in your network."
        ),
        validators=[WhiteListedURLValidator()],
    )
    admin_username = models.CharField(
        _("Admin username"),
        max_length=50,
        default="ej-admin",
        help_text=_("Username for Rocket.Chat admin user"),
    )
    admin_id = models.CharField(
        _("Admin user id"), max_length=50, help_text=_("Id string for the Rocket.Chat admin user.")
    )
    admin_token = models.CharField(
        _("Login token"),
        max_length=50,
        help_text=_("Login token for the Rocket.Chat admin user."),
        blank=True,
    )
    admin_password = models.CharField(
        _("Admin password"),
        max_length=50,
        help_text=_("Password for the Rocket.Chat admin user."),
        blank=True,
        validators=[requires_setup_for_blank],
    )
    is_active = models.BooleanField(
        _("Is active"),
        default=True,
        help_text=_("Set to false to temporarily disable RocketChat integration."),
    )

    objects = RCConfigManager()

    class Meta:
        verbose_name = _("Rocket.Chat Configuration")
        verbose_name_plural = _("Rocket.Chat Configurations")

    def __str__(self):
        return f"Rocket config: {self.url} ({self.admin_id})"
