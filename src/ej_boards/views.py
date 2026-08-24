from logging import getLogger
from urllib.parse import urlencode

from django.views.generic import (
    ListView,
    CreateView,
    UpdateView,
    RedirectView,
    DeleteView,
    DetailView,
)
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.db import IntegrityError, transaction
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.decorators import method_decorator
from django.urls import reverse, reverse_lazy
from django.utils.translation import gettext_lazy as _

from ej_boards.models import Board, BoardManagerInvitation
from ej_boards.rules import can_manage_board_members
from ej_conversations.components import member_toast
from ej_integrations.utils import get_host_with_schema
from ej_users.models import User

from .forms import BoardForm
from ej.decorators import can_delete_board, can_edit_board
from .tasks import send_board_manager_invitation_email

log = getLogger("ej")


@method_decorator([login_required], name="dispatch")
class BoardListView(ListView):
    model = Board
    template_name = "ej_boards/board-list.jinja2"

    def get_context_data(self):
        user = self.request.user
        boards = Board.objects.accessible_by(user)
        can_add_board = user.has_perm("ej.can_add_board")

        return {"boards": boards, "can_add_board": can_add_board}

    def get(self, *args):
        context = self.get_context_data()
        # Redirect to user's unique board, if that is the case
        if not context["can_add_board"] and context["boards"].count() == 1:
            return redirect(f"{context['boards'][0].get_absolute_url()}")
        return render(self.request, self.template_name, context)


@method_decorator([login_required], name="dispatch")
class BoardCreateView(CreateView):
    model = Board
    template_name = "ej_boards/board-create.jinja2"

    def post(self, *args, **kwargs):
        context = self.get_context_data()
        form = context["form"]
        if form.is_valid_post():
            board = form.save(owner=self.request.user)
            return redirect(board.get_absolute_url())
        return render(self.request, self.template_name, context)

    def get_context_data(self):
        form = BoardForm(request=self.request)
        return {
            "form": form,
            "user_boards": Board.objects.accessible_by(self.request.user),
        }


@method_decorator([can_edit_board], name="dispatch")
class BoardEditView(UpdateView):
    model = Board
    template_name = "ej_boards/board-edit.jinja2"

    def post(self, board, board_slug, **kwargs):
        context = self.get_context_data()
        if context["form"].is_valid_post():
            context["form"].save()
            return redirect(context["board"].get_absolute_url())
        return render(self.request, self.template_name, context)

    def get_context_data(self):
        board = self.get_object()
        can_manage_members = can_manage_board_members(self.request.user, board)
        form = BoardForm(instance=board, request=self.request)
        form.fields["slug"].help_text = _("You cannot change this value")
        form.fields["slug"].disabled = True

        return {
            "form": form,
            "board": board,
            "user_boards": Board.objects.accessible_by(self.request.user),
            "current_page": board.slug,
            "can_manage_members": can_manage_members,
            "existing_members": (
                board.manager_invitations.active() if can_manage_members else []
            ),
        }

    def get_object(self) -> Board:
        board_slug = self.kwargs["board_slug"]
        return Board.objects.get(slug=board_slug)


@method_decorator(login_required, name="dispatch")
class BoardManagerInvitationView(DetailView):
    model = Board
    http_method_names = ["post", "delete"]

    def get_queryset(self):
        return Board.objects.select_related("owner")

    def get_object(self, queryset=None) -> Board:
        queryset = queryset or self.get_queryset()
        return get_object_or_404(queryset, slug=self.kwargs["board_slug"])

    def post(self, request, *args, **kwargs):
        board = self.get_object()

        if not self._has_permission(request, board):
            return redirect("auth:login")

        email, email_error = self._validate_email(request)
        is_owner, owner_error = self._is_owner(email, board)
        already_invited, invitation_error = self._already_invited(email, board)
        error = email_error or owner_error or invitation_error
        if email_error or is_owner or already_invited:
            return HttpResponse(error, status=400)

        user = User.objects.filter(email__iexact=email).first()
        try:
            with transaction.atomic():
                invitation = BoardManagerInvitation.objects.create(
                    board=board,
                    email=email,
                    user=user,
                    invited_by=request.user,
                )
        except IntegrityError:
            return HttpResponse(
                _("This member is already invited."), status=400
            )
        self._send_invitation(request, invitation)
        return HttpResponse(status=201)

    def delete(self, request, *args, **kwargs):
        board = self.get_object()

        if not self._has_permission(request, board):
            return redirect("auth:login")

        invitation = get_object_or_404(
            BoardManagerInvitation,
            id=self.kwargs["invitation_id"],
            board=board,
        )
        with transaction.atomic():
            invitation.delete_manager()
        return HttpResponse(status=204)

    def _has_permission(self, request, board):
        return can_manage_board_members(request.user, board)

    def _validate_email(self, request):
        email = BoardManagerInvitation.normalize_email(
            request.POST.get("email")
        )
        try:
            validate_email(email)
            return email, None
        except ValidationError:
            return None, _("Enter a valid email address.")

    def _is_owner(self, email, board):
        if not email:
            return False, None

        is_owner = email.lower() == board.owner.email.lower()
        if not is_owner:
            return False, None

        return True, _("The board owner cannot be added as a manager.")

    def _already_invited(self, email, board):
        if not email:
            return False, None

        user = User.objects.filter(email__iexact=email).first()
        has_active_invitation = BoardManagerInvitation.objects.filter(
            board=board, email__iexact=email, is_active=True
        ).exists()
        is_manager = (
            user is not None and board.managers.filter(user=user).exists()
        )
        if not has_active_invitation and not is_manager:
            return False, None

        return True, _("This member is already invited.")

    def _send_invitation(self, request, invitation):
        try:
            send_board_manager_invitation_email.delay(
                invitation.id,
                get_host_with_schema(request),
            )
        except Exception:
            log.exception(
                "Could not enqueue board manager invitation email %s.",
                invitation.id,
            )


class BoardManagerInvitationAcceptView(DetailView):
    model = BoardManagerInvitation
    http_method_names = ["get"]
    slug_field = "accept_token"
    slug_url_kwarg = "accept_token"

    def get(self, request, *args, **kwargs):
        invitation = self.get_object()

        if not request.user.is_authenticated:
            auth_route = self._auth_route_for_invitation(invitation)
            return self._redirect_to_auth(auth_route)

        if not invitation.matches_user_email(request.user):
            member_toast(
                request,
                _("This invitation was sent to a different email address."),
            )
            return redirect(request.user.profile.default_url())

        try:
            invitation.accept(request.user)
        except ValidationError:
            raise Http404
        member_toast(request, _("Invitation accepted."))
        return redirect(invitation.get_board_url())

    def get_queryset(self):
        return (
            BoardManagerInvitation.objects.pending()
            .select_related("board", "user")
            .filter(board__slug=self.kwargs["board_slug"])
        )

    def _auth_route_for_invitation(self, invitation):
        user_exists = User.objects.filter(
            email__iexact=invitation.email
        ).exists()
        return "auth:login" if user_exists else "auth:register"

    def _redirect_to_auth(self, auth_route):
        url = reverse(auth_route)
        query = urlencode({"next": self.request.get_full_path()})
        return redirect(f"{url}?{query}")


@method_decorator([login_required, can_delete_board], name="dispatch")
class BoardDeleteView(DeleteView):
    model = Board

    def post(self, *args, **kwargs):
        board = self.get_object()

        if self.request.user.has_more_than_one_board():
            board.delete()
        return redirect(reverse_lazy("profile:home"))

    def get_object(self) -> Board:
        board_slug = self.kwargs["board_slug"]
        return Board.objects.get(slug=board_slug)


class BoardBaseView(RedirectView):
    permanent = False

    def get_redirect_url(self, board_slug):
        board_slug = self.kwargs["board_slug"]
        board = Board.objects.get(slug=board_slug)
        return board.get_absolute_url()
