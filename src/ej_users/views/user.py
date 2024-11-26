import logging
from functools import lru_cache
from typing import Any, Dict
from django.apps import apps
from django.conf import settings
from django.contrib import auth
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.db import IntegrityError
from django.http import Http404, HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import redirect, render, get_object_or_404
from django.template.loader import get_template
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.views.generic.edit import CreateView, FormView
from rest_framework import status
from rest_framework.authtoken.models import Token
from sidekick import record

from ej.components.builtins import toast
from .. import forms
from ej_users.models import PasswordResetToken
from .. import password_reset_token
from ..socialbuttons import social_buttons


User = get_user_model()


log = logging.getLogger("ej")


class LoginView(FormView):
    template_name = "ej_users/login.jinja2"
    next_url = None

    def post(self, request, *args: Any, **kwargs: Any):
        form = forms.LoginForm(request=request)
        fast = request.GET.get("fast", "false") == "true" or "fast" in request.GET

        if form.is_valid_post():
            data = form.cleaned_data
            email, password = data["email"], data["password"]

            try:
                user = User.objects.get_by_email(email)
                user = auth.authenticate(request, email=user.email, password=password)

                if user is None:
                    raise User.DoesNotExist

                auth.login(request, user, backend=user.backend)
                self.next_url = request.GET.get("next", user.profile.default_url())
                log.info(f"user {user} ({email}) successfully authenticated")
            except User.DoesNotExist:
                form.add_error(None, _("Invalid email or password"))
                log.info(f"invalid login attempt: {email}")
            else:
                toast(request, _("Welcome to EJ!"))
                return redirect(self.next_url)

        elif fast and request.user.is_authenticated:
            self.next_url = request.GET.get("next", user.profile.default_url())
            return redirect(self.next_url)

        return render(request, self.template_name, self.get_context_data(form=form))

    def get_context_data(self, **kwargs: Any) -> Dict[str, Any]:
        return {
            "user": self.request.user,
            "form": kwargs.get("form", forms.LoginForm(request=self.request)),
            "next": self.next_url,
            "social_js": social_js_template().render(request=self.request),
            "social_buttons": social_buttons(self.request),
        }


class RegisterView(CreateView):
    template_name = "ej_users/register.jinja2"
    next_url = None

    def post(self, request):
        form = forms.RegistrationForm(request=request)

        if form.is_valid():
            data = form.cleaned_data
            name, email, password = (
                data["name"],
                data["email"],
                data["password"],
            )

            try:
                user = self.create_user(
                    request,
                    email,
                    password,
                    name=name,
                )
                authenticated_user = auth.authenticate(
                    request, email=user.email, password=password
                )
                auth.login(request, authenticated_user)
                self.next_url = request.GET.get(
                    "next", authenticated_user.profile.default_url()
                )
                response = redirect(self.next_url)
                response.set_cookie("show_welcome_window", "true")
                return response
            except IntegrityError as ex:
                form.add_error(None, str(ex))
                log.info(f"invalid register attempt: {email}")

        return render(request, self.template_name, self.get_context_data(form=form))

    def create_user(self, request, email, password, **extra_fields):
        session_key = request.GET.get("sessionKey")
        try:
            if session_key:
                user = User.objects.create_user_from_session(
                    session_key, email, password, **extra_fields
                )
            else:
                user = User.objects.create_user(email, password, **extra_fields)

            log.info(f"user {user} ({email}) successfully created")
        except Exception as e:
            raise IntegrityError(f"{e}: não foi possível cadastrar o usuário!")
        return user

    def get_context_data(self, **kwargs: Any) -> Dict[str, Any]:
        return {
            "user": self.request.user,
            "form": kwargs.get("form", forms.RegistrationForm(request=self.request)),
            "next": self.next_url,
            "social_js": social_js_template().render(request=self.request),
            "social_buttons": social_buttons(self.request),
        }


class RecoverPasswordView(FormView):
    template_name = "ej_users/recover-password.jinja2"
    success = False
    user = None

    def post(self, request: HttpRequest) -> HttpResponse:
        form = forms.EmailForm(request=request)

        if form.is_valid():
            email = form.cleaned_data["email"]
            self.user = User.objects.filter(email=email).first()

            if self.user:
                self.send_recover_password_email(request, self.user, email)
                self.success = True

        return render(request, self.template_name, self.get_context_data(form=form))

    def get_next_url(self):
        return self.request.GET.get("next", "/login/")

    def send_recover_password_email(self, request, user, email):
        token = password_reset_token(user)
        from_email = settings.DEFAULT_FROM_EMAIL
        if settings.DEFAULT_FROM_NAME:
            from_email = f"{settings.DEFAULT_FROM_NAME} <{from_email}>"
        path = reverse("auth:recover-password-token", kwargs={"token": token.url})
        template = get_template("ej_users/recover-password-message.jinja2")
        email_body = template.render(
            {"url": self.raw_url(request, path)}, request=request
        )
        send_mail(
            subject=_("Please reset your password"),
            message=email_body,
            from_email=from_email,
            recipient_list=[email],
        )
        log.info(f"user {user} requested a password reset.")

    def raw_url(self, request, path):
        if not path.startswith("/"):
            path = request.path.rstrip("/") + "/" + path
        return f"{request.scheme}://{request.get_host()}{path}"

    def get_context_data(self, **kwargs: Any) -> Dict[str, Any]:
        return {
            "user": self.user,
            "form": kwargs.get("form", forms.EmailForm(request=self.request)),
            "success": self.success,
            "next": self.get_next_url(),
        }


class RecoverPasswordToken(FormView):
    template_name = "ej_users/recover-password-token.jinja2"

    def post(
        self, request: HttpRequest, token: str, *args: str, **kwargs: Any
    ) -> HttpResponse:
        reset_token = self.get_reset_token()
        user = reset_token.user
        form = forms.PasswordForm(request=request)

        if form.is_valid_post() and not (reset_token.is_expired or reset_token.is_used):
            password = form.cleaned_data["password"]
            user.set_password(password)
            user.save()
            reset_token.delete()
            return redirect(self.get_next_url())

        return render(
            request,
            self.template_name,
            self.get_context_data(reset_token=reset_token, form=form),
        )

    def get_next_url(self):
        return self.request.GET.get("next", "/login/")

    def get_reset_token(self):
        return get_object_or_404(PasswordResetToken, url=self.kwargs["token"])

    def get_context_data(self, **kwargs: Any) -> Dict[str, Any]:
        reset_token = self.kwargs.get("reset_token", self.get_reset_token())
        form = self.kwargs.get("form", forms.PasswordForm(request=self.request))

        return {
            "user": reset_token.user,
            "form": form,
            "next": self.get_next_url(),
            "is_expired": reset_token.is_expired,
        }


#
# Registration via API + jsCookies
#
def api_key(request):
    if request.user.id is None:
        raise Http404
    token = Token.objects.get_or_create(user=request.user)
    return JsonResponse({"key": token[0].key}, status=status.HTTP_200_OK)


#
# Auxiliary functions and templates
#
@lru_cache(1)
def social_js_template():
    if apps.is_installed("allauth.socialaccount"):
        return get_template("socialaccount/snippets/login_extra.html")
    else:
        return record(render=lambda *args, **kwargs: "")
