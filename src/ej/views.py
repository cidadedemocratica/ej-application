import os
from constance import config
from pprint import pformat

from django.http import Http404
from django.shortcuts import render
from django.urls import reverse
from django.conf import settings
from django.views.generic import DetailView, RedirectView


class IndexView(RedirectView):
    permanent = False

    def get_redirect_url(self, **kwargs):
        if self.request.user.is_authenticated:
            return reverse("profile:home")
        else:
            return config.EJ_LANDING_PAGE_DOMAIN


class InfoStylesView(DetailView):
    template_name = "pages/info-styles.jinja2"

    def get(self, request):
        if not request.user.is_superuser:
            raise Http404
        return render(request, self.template_name)


class InfoDjangoSettingsView(DetailView):
    template_name = "pages/info-django-settings.jinja2"

    def get(self, request):
        if not request.user.is_superuser:
            raise Http404
        return render(request, self.template_name, self.get_context_data())

    def get_context_data(self, **kwargs):
        data = [
            (name, pformat(getattr(settings, name)))
            for name in dir(settings)
            if name.isupper()
        ]
        return {"settings_data": sorted(data)}


class InfoEnvironView(DetailView):
    template_name = "pages/info-environ.jinja2"

    def get(self, request):
        if not request.user.is_superuser:
            raise Http404
        return render(request, self.template_name, self.get_context_data())

    def get_context_data(self, **kwargs):
        return {"settings_data": sorted(os.environ.items())}


#
# Non-html data
#
class ServiceWorkerView(DetailView):
    def get(self, request):
        return render(
            request, "js/sw.js", {}, content_type="application/javascript"
        )
