from logging import getLogger

from django.contrib.auth.decorators import login_required
from django.http import Http404
from django.shortcuts import get_object_or_404, render
from django.utils.decorators import method_decorator
from django.utils.translation import gettext_lazy as _
from django.views.generic import DetailView

from . import models
from .enums import Choice

log = getLogger("ej")


@method_decorator([login_required], name="dispatch")
class CommentDetailView(DetailView):
    template_name = "ej_conversations/comments/detail.jinja2"
    model = models.Comment
    show_actions = True
    message = None

    def post(self, request, comment_id: int, hex_hash: str):
        user = request.user
        comment = self.get_object()
        vote = request.POST["vote"]

        comment.vote(user, vote)
        log.info(f"user {user.id} voted {vote} on comment {comment.id}")
        self.show_actions = False
        self.message = _("Your vote has been computed :-)")

        return render(request, self.template_name, self.get_context_data())

    def get_object(self) -> models.Comment:
        comment = get_object_or_404(models.Comment, id=self.kwargs["comment_id"])
        if self.kwargs["hex_hash"] != comment.comment_url_hash():
            raise Http404
        return comment

    def get_context_data(self, **kwargs):
        comment = self.get_object()
        user = self.request.user

        qs = models.Vote.objects.filter(comment=comment, author=user)
        if qs and qs.first().choice != Choice.SKIP:
            self.show_actions = False
            self.message = _(
                "You already voted in this comment as <strong>{vote}</strong>. "
                "You cannot change your vote."
            ).format(vote=qs.first().choice.description)

        return {
            "conversation": comment.conversation,
            "comment": comment,
            "message": self.message,
            "show_actions": self.show_actions,
        }
