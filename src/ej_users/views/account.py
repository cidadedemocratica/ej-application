import logging
from typing import Any, Dict

from django.contrib import auth
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse
from django.utils.decorators import method_decorator
from django.utils.translation import gettext_lazy as _
from django.shortcuts import render
from django.views.generic import TemplateView
from django.views.generic.edit import FormView

from .. import forms
from .. import models

User = get_user_model()

app_name = "ej_users"
log = logging.getLogger("ej")


#
# Account management
#
@method_decorator([login_required], name="dispatch")
class IndexView(TemplateView):
    template_name = "account/index.jinja2"

    def get_context_data(self, **kwargs):
        user = self.request.user
        return {"user": user, "profile": getattr(user, "profile", None)}


@method_decorator([login_required], name="dispatch")
class LogoutView(TemplateView):
    template_name = "account/logout.jinja2"

    def post(self, request: HttpRequest) -> HttpResponse:
        auth.logout(request)
        return render(request, self.template_name, {"has_logout": True})

    def get_context_data(self, **kwargs: Any):
        return {"has_logout": False}


@method_decorator([login_required], name="dispatch")
class RemoveAccountView(FormView):
    template_name = "account/remove-account.jinja2"
    farewell_message = None

    def post(
        self, request: HttpRequest, *args: str, **kwargs: Any
    ) -> HttpResponse:
        form = forms.RemoveAccountForm(request=request)
        if form.is_valid_post():
            user = request.user
            if form.cleaned_data["confirm"] is False:
                form.add_error(
                    "confirm",
                    _("You must confirm that you want to remove your account."),
                )
            elif form.cleaned_data["email"] != user.email:
                form.add_error("email", _("Wrong e-mail address"))
            elif user.is_superuser:
                form.add_error(None, _("Cannot remove superuser accounts"))
            else:
                models.remove_account(user)
                self.farewell_message = _(
                    "We are sorry to see you go :(<br><br>Good luck in your journey."
                )
                log.info(f"User {request.user} removed their EJ account.")
        return render(
            request,
            "account/remove-account.jinja2",
            self.get_context_data(form=form),
        )

    def get_context_data(self, **kwargs: Any) -> Dict[str, Any]:
        form = self.kwargs.get(
            "form", forms.RemoveAccountForm(request=self.request)
        )
        return {"form": form, "farewell_message": self.farewell_message}
