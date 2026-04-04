from django import forms
from django.conf import settings
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _
from django.template.loader import get_template
from django.core.exceptions import ValidationError


from ej.forms import EjForm, EjModelForm

User = get_user_model()


class TermsWidget(forms.CheckboxInput):
    template_name = "ej_users/includes/terms.jinja2"
    renderer = get_template(template_name)

    def render(self, name, value, attrs=None, renderer=None):
        from django.contrib.flatpages.models import FlatPage

        try:
            terms = FlatPage.objects.get(url="/usage/").content
        except Exception:
            terms = ""
        context = self.get_context(name, value, attrs)
        context["widget"]["terms"] = terms
        return self.renderer.render(context)


class PrivacyPolicyWidget(forms.CheckboxInput):
    template_name = "ej_users/includes/privacy-policy.jinja2"
    renderer = get_template(template_name)

    def render(self, name, value, attrs=None, renderer=None):
        from django.contrib.flatpages.models import FlatPage

        try:
            privacy_policy = FlatPage.objects.get(
                url="/privacy-policy/"
            ).content
        except Exception:
            privacy_policy = ""
        context = self.get_context(name, value, attrs)
        context["widget"]["privacy_policy"] = privacy_policy
        return self.renderer.render(context)


class PasswordForm(EjForm):
    """
    Recover User Password
    """

    password = forms.CharField(
        label=_("Password"), required=True, widget=forms.PasswordInput
    )
    password_confirm = forms.CharField(
        label=_("Password confirmation"),
        required=True,
        widget=forms.PasswordInput,
    )

    def _post_clean(self):
        super()._post_clean()
        data = self.cleaned_data
        if data.get("password") != data.get("password_confirm"):
            self.add_error("password", _("Passwords do not match"))


class RegistrationForm(PasswordForm, EjModelForm):
    """
    Register new user
    """

    class Meta:
        model = User
        fields = [
            "name",
            "email",
            "password",
            "password_confirm",
            "agree_with_terms",
            "agree_with_privacy_policy",
        ]
        help_texts = {k: None for k in fields}
        help_texts["email"] = "E-mail"
        widgets = {
            "agree_with_terms": TermsWidget,
            "agree_with_privacy_policy": PrivacyPolicyWidget,
        }


class LoginForm(EjForm):
    """
    User login: email and password fields.
    """

    email_field_class = (
        forms.CharField
        if getattr(settings, "ALLOW_USERNAME_LOGIN", False)
        else forms.EmailField
    )
    email = email_field_class(label=_("E-mail"))
    password = forms.CharField(label=_("Password"), widget=forms.PasswordInput)


class EmailForm(EjForm):
    """
    Form with a single e-mail field.
    """

    email = forms.EmailField(label=_("E-mail"))


class RemoveAccountForm(EmailForm):
    """
    E-mail + confirmation checkbox.
    """

    confirm = forms.BooleanField(label=_("Yes, I understand the consequences."))


class ChangePasswordForm(PasswordForm):
    current_password = forms.CharField(
        label=_("Current password"), required=True, widget=forms.PasswordInput
    )

    def __init__(self, user, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user

    def clean_current_password(self):
        password = self.cleaned_data["current_password"]
        if not self.user.check_password(password):
            raise ValidationError(_("Incorrect current password"))

    def save(self, commit=True, **kwargs):
        self.user.set_password(self.cleaned_data["password"])
        self.user.save()
        return self.user
