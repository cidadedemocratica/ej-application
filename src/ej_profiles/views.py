from django.contrib.auth.decorators import login_required
from django.contrib.auth import update_session_auth_hash
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.views.generic import DetailView, ListView
from django.views.generic.edit import UpdateView
from django.http import HttpResponse
from django.utils.translation import gettext_lazy as _

from ej.components.builtins import toast
from ej_boards.models import Board
from ej_conversations.models import Conversation, ConversationTag
from ej_integrations.utils import get_host_with_schema
from ej_users.forms import ChangePasswordForm

from . import forms
from .models import Profile


@method_decorator([login_required], name="dispatch")
class DetailView(DetailView):
    template_name = "ej_profiles/detail.jinja2"

    def get_object(self) -> Profile:
        return self.request.user.get_profile()

    def get_context_data(self, **kwargs):
        profile = self.get_object()

        return {
            "profile": profile,
            "n_conversations": profile.conversations.count(),
            "n_boards": profile.boards.count(),
            "n_favorites": profile.favorite_conversations.count(),
            "n_comments": profile.user.comments.count(),
            "n_votes": profile.votes.count(),
            "achievements_href": None,
            "user_boards": Board.objects.filter(owner=self.request.user),
            "change_password_form": ChangePasswordForm(self.request.user),
            "go_to_password": False,
            "current_page": "detail-profile",
        }

    def post(self, request):
        change_password_form = ChangePasswordForm(self.request.user, request=request)
        if change_password_form.is_valid():
            change_password_form.save()
            update_session_auth_hash(request, request.user)
            toast(request, _("Password changed successfully."))
            return render(request, self.template_name, self.get_context_data())

        context = self.get_context_data()
        context["change_password_form"] = change_password_form
        context["go_to_password"] = True
        return render(request, self.template_name, context)


@method_decorator([login_required], name="dispatch")
class EditView(UpdateView):
    template_name = "ej_profiles/edit.jinja2"
    form_class = forms.ProfileForm

    def post(self, request):
        form = self.form_class(instance=self.get_object(), request=self.request)
        form_profile_photo = forms.ProfileFormProfilePhoto(
            request.POST, request.FILES, instance=self.get_object()
        )
        has_changed = False

        if form.is_valid_post():
            form.save()
            has_changed = True

        if form_profile_photo.is_valid():
            form_profile_photo.save()
            has_changed = True

        if has_changed:
            return redirect("/profile/")

        return render(request, self.template_name, self.get_context_data())

    def get_object(self) -> Profile:
        return self.request.user.get_profile()

    def get_context_data(self, **kwargs):
        profile = self.get_object()

        return {
            "form": self.form_class(instance=profile, request=self.request),
            "profile": profile,
            "current_page": "edit-profile",
            "user_boards": Board.objects.filter(owner=self.request.user),
        }


@method_decorator([login_required], name="dispatch")
class HomeView(ListView):
    template_name = "ej_profiles/home.jinja2"
    queryset = Conversation.objects.filter(is_promoted=True).order_by("-created")

    def get(self, request, *args, **kwargs):
        user = request.user
        tour_url = reverse("profile:tour")
        if user.get_profile().completed_tour:
            return super().get(request, *args, **kwargs)
        return redirect(tour_url)

    def get_context_data(self, **kwargs):
        public_conversations = self.get_queryset()
        profile = self.request.user.profile
        profile_conversations_tags = list(
            profile.participated_public_tags().values_list("tag__name", flat=True)
        )
        public_tags = list(
            ConversationTag.objects.filter(content_object__is_promoted=True)
            .distinct("tag")
            .values_list("tag__name", flat=True)
        )
        profile_selected_tags = list(
            ConversationTag.objects.filter(content_object__author=self.request.user)
            .distinct("tag")
            .values_list("tag__name", flat=True)
        )
        contributions_data = profile.get_contributions_data()

        return {
            "user_boards": Board.objects.filter(owner=self.request.user),
            "public_conversations": list(public_conversations),
            "participated_tags": list(profile_conversations_tags),
            "all_tags": list(public_tags),
            "my_tags": profile_selected_tags,
            "host": get_host_with_schema(self.request),
            "has_filtered_tag": self.request.user.profile.filtered_home_tag,
            "current_page": "home",
            **contributions_data,
        }


@method_decorator([login_required], name="dispatch")
class TourView(HomeView):
    def _get_tour_step_template(self, step: str):
        if not step:
            return "ej_profiles/tour.jinja2"
        return f"ej_profiles/includes/tour-page{step}.jinja2"

    def get(self, *args, **kwargs):
        user = self.request.user
        user_profile = user.get_profile()

        if self.request.GET.get("completedTour") == "false":
            user_profile.completed_tour = False
            user_profile.save()

        if user_profile.completed_tour:
            return redirect(reverse("profile:home"))

        tour_step = self.request.GET.get("step")
        template_name = self._get_tour_step_template(tour_step)
        return render(self.request, template_name, self.get_context_data())

    def post(self, *args, **kwargs):
        user = self.request.user
        response = HttpResponse()
        if self.request.GET.get("step") in ["skip", "end"]:
            profile = user.get_profile()
            profile.completed_tour = True
            profile.save()
            """
            Tour page utilizes HTMX library to make backend AJAX requests.
            In order to make a redirect with HTMX,
            we need to include HX-Redirect header in the response.
            For more information, access https://htmx.org/reference/.
            """
            response.status_code = 302
            response["HX-Redirect"] = reverse("profile:home")
        return response
