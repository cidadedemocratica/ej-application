from django.views.generic import (
    ListView,
    CreateView,
    UpdateView,
    RedirectView,
    DeleteView,
)
from django.shortcuts import redirect, render
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _

from ej_boards.models import Board
from .forms import BoardForm
from ej.decorators import can_edit_board


@method_decorator([login_required], name="dispatch")
class BoardListView(ListView):
    model = Board
    template_name = "ej_boards/board-list.jinja2"

    def get_context_data(self):
        user = self.request.user
        boards = user.boards.all()
        can_add_board = user.has_perm("ej.can_add_board")

        return {"boards": boards, "can_add_board": can_add_board}

    def get(self, *args):
        context = self.get_context_data()
        # Redirect to user's unique board, if that is the case
        if (
            not context["can_add_board"]
            and self.request.user.boards.count() == 1
        ):
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
            "user_boards": Board.objects.filter(owner=self.request.user),
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
        form = BoardForm(instance=board, request=self.request)
        form.fields["slug"].help_text = _("You cannot change this value")
        form.fields["slug"].disabled = True

        return {
            "form": form,
            "board": board,
            "user_boards": Board.objects.filter(owner=self.request.user),
            "current_page": board.slug,
        }

    def get_object(self) -> Board:
        board_slug = self.kwargs["board_slug"]
        return Board.objects.get(slug=board_slug)


@method_decorator([login_required, can_edit_board], name="dispatch")
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
