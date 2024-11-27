from logging import getLogger
from typing import Any, Dict

from django.contrib.auth.decorators import login_required
from django.contrib.flatpages.models import FlatPage
from django.db import transaction
from django.db.models import F
from django.db.models.query import QuerySet
from django.http import HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from django.urls import reverse, reverse_lazy
from django.utils.decorators import method_decorator
from django.utils.translation import gettext_lazy as _
from django.views.generic import DetailView, ListView
from django.views.generic.edit import CreateView, UpdateView, DeleteView

from ej.decorators import (
    can_acess_list_view,
    can_edit_conversation,
    can_moderate_conversation,
    check_conversation_overdue,
    is_superuser,
)
from ej_boards.models import Board
from ej_conversations.rules import max_comments_per_conversation
from ej_integrations.utils import get_host_with_schema
from ej_users.models import User

from . import forms
from .decorators import redirect_to_conversation_detail, user_can_post_anonymously
from .forms import CommentForm, ConversationForm
from .models import Comment, Conversation
from .utils import handle_detail_comment, handle_detail_favorite, handle_detail_vote

log = getLogger("ej")


class ConversationCommonView:
    """
    Implements common behaviors for some ej_conversations views.
    """

    queryset = Conversation.objects.all()
    form_class = CommentForm
    model = Conversation
    ctx = {}

    def get_comment(self, conversation: Conversation, user):
        """
        returns a comment to vote based on self.request.method.

        if self.request.method == 'GET', returns always the same unvoted comment.
        if self.request.method == 'POST', returns a random unvoted comment.
        """
        if self.request.method == "GET":
            # on "GET" requests, returns always the same unvoted comment
            return conversation.next_comment(user, random=False)
        return conversation.next_comment(user, random=True)

    def get_statistics(self, conversation: Conversation, user: User):
        if not user.is_anonymous:
            n_comments = user.comments.filter(conversation=conversation).count()
            n_user_final_votes = conversation.current_comment_count(user)
            user_boards = Board.objects.filter(owner=user)
            return [n_comments, n_user_final_votes, user_boards]
        else:
            return [0, 0, []]

    def get_privacy_policy_content(self):
        try:
            return FlatPage.objects.get(url="/privacy-policy/").content
        except FlatPage.DoesNotExist:
            return ""

    def get_context_data(self, *args, **kwargs):
        conversation: Conversation = self.get_object()
        user = User.get_or_create_from_session(conversation, self.request)
        comment = self.get_comment(conversation, user)
        max_comments = max_comments_per_conversation()
        conversation.set_request(self.request)
        n_comments, n_user_final_votes, user_boards = self.get_statistics(
            conversation, user
        )
        host = get_host_with_schema(self.request)

        return {
            "background_image_url": conversation.get_background_image_url(host),
            "logo_image_url": conversation.get_logo_image_url(host),
            "conversation": conversation,
            "comment": comment,
            "comment_form": self.form_class(conversation=conversation),
            "user_is_author": conversation.author == user,
            "user_progress_percentage": conversation.user_progress_percentage(user),
            "n_comments": n_comments,
            "max_comments": max_comments,
            "n_user_final_votes": n_user_final_votes,
            "user_boards": user_boards,
            "privacy_policy": self.get_privacy_policy_content(),
            "current_page": "voting",
            "form": forms.CommentForm(conversation=conversation),
            **self.ctx,
            **kwargs,
        }


class ConversationView(ListView):
    def get_queryset(self) -> QuerySet[Any]:
        user = self.request.user
        board_slug = self.kwargs.get("board_slug", None)
        annotations = (
            "n_votes",
            "n_comments",
            "n_user_votes",
            "first_tag",
            "n_favorites",
            "author_name",
        )

        if board_slug:
            board = Board.objects.get(slug=board_slug)
            queryset = board.conversations.annotate_attr(board=board)
        else:
            queryset = Conversation.objects.filter(is_promoted=True)

        return queryset.cache_annotations(*annotations, user=user).order_by("-created")

    def get_context_data(self, **kwargs: Any) -> Dict[str, Any]:
        return super().get_context_data(**kwargs)


class PublicConversationView(ConversationView):
    template_name = template_name = "ej_conversations/list.jinja2"

    def get_context_data(self, **kwargs: Any) -> Dict[str, Any]:
        user = self.request.user
        user_boards = Board.objects.filter(owner=user) if user.is_authenticated else []

        return {
            "conversations": self.get_queryset(),
            "user_boards": user_boards,
        }


@method_decorator([login_required], name="dispatch")
class ConversationsFilterByTag(ListView):
    template_name = "ej_conversations/includes/conversation-card-list.jinja2"
    model = Conversation

    def get_queryset(self) -> QuerySet[Any]:
        queryset = Conversation.objects.all()
        search_text = self.request.GET.get("search_text", None)
        tags = self.request.GET.getlist("tags")

        self.request.user.profile.filtered_home_tag = True
        self.request.user.profile.save()
        queryset = self.initial_queryset(queryset)
        queryset = queryset.filter_by_tags(tags)

        queryset = queryset.filter_by_text_and_tag(search_text)

        return queryset

    def get_button_text(self):
        return _("Participate")

    def initial_queryset(self, queryset):
        return Conversation.objects.all()

    def get_context_data(self, **kwargs: Any) -> Dict[str, Any]:
        return {
            "conversations": self.get_queryset(),
            "button_text": self.get_button_text(),
        }


@method_decorator([login_required], name="dispatch")
class PromotedConversationsFilterByTag(ConversationsFilterByTag):
    def initial_queryset(self, queryset):
        return queryset.filter(is_promoted=True)


@method_decorator([login_required], name="dispatch")
class UserConversationsFilterByTag(ConversationsFilterByTag):
    def get_button_text(self):
        return _("Manage!")

    def initial_queryset(self, queryset):
        return queryset.filter(author=self.request.user)


@method_decorator([login_required, can_acess_list_view], name="dispatch")
class BoardConversationsView(ConversationView):
    template_name = "ej_conversations/board-conversations-list.jinja2"

    def get_queryset(self) -> QuerySet[Any]:
        user = self.request.user
        board_slug = self.kwargs.get("board_slug", None)
        annotations = (
            "n_votes",
            "n_comments",
            "n_user_votes",
            "first_tag",
            "n_favorites",
            "author_name",
        )

        if board_slug:
            board = Board.objects.get(slug=board_slug)
            queryset = board.conversations.annotate_attr(board=board)
        else:
            queryset = Conversation.objects.filter(is_promoted=True)

        return queryset.cache_annotations(*annotations, user=user).order_by("-created")

    def get_context_data(self, **kwargs: Any) -> Dict[str, Any]:
        user = self.request.user
        board_slug = self.kwargs.get("board_slug", None)
        board = Board.objects.get(slug=board_slug)
        user_boards = Board.objects.filter(owner=user)

        return {
            "conversations": self.get_queryset(),
            "title": _(board.title),
            "subtitle": _("Participate voting and creating comments!"),
            "board": board,
            "user_boards": user_boards,
            "current_page": board.slug,
            "can_delete_board": user.has_more_than_one_board(),
        }


class ConversationWelcomeView(ConversationCommonView, DetailView):
    queryset = Conversation.objects.all()
    form_class = CommentForm
    model = Conversation
    template_name = "ej_conversations/conversation-welcome.jinja2"

    @redirect_to_conversation_detail
    def get(self, request, *args, **kwargs):
        return super().get(request)


@method_decorator([check_conversation_overdue], name="dispatch")
class ConversationCommentView(ConversationCommonView, DetailView):
    template_name = "ej_conversations/comments/add-comment.jinja2"

    def get(self, request, *args, **kwargs):
        context = self.get_context_data()
        conversation = context["conversation"]
        user = User.get_or_create_from_session(conversation, self.request)
        context["comment"] = conversation.next_comment(user, random=False)
        return render(
            request,
            self.template_name,
            context,
        )

    @user_can_post_anonymously
    def post(self, request, conversation_id, slug, board_slug, *args, **kwargs):
        conversation = self.get_object()
        request.user = User.get_or_create_from_session(conversation, request)

        # TODO: create a rule for this check
        if (
            conversation.participants_can_add_comments
            or request.user.id == conversation.author.id
        ):
            self.ctx = handle_detail_comment(request, conversation)

        return render(
            request,
            self.template_name,
            self.get_context_data(),
        )


@method_decorator([check_conversation_overdue], name="dispatch")
class ConversationDetailContentView(ConversationCommonView, DetailView):
    form_class = CommentForm
    model = Conversation
    template_name = "ej_conversations/includes/conversation-detail-content.jinja2"
    ctx = {}


@method_decorator([check_conversation_overdue], name="dispatch")
class ConversationDetailView(ConversationCommonView, DetailView):
    form_class = CommentForm
    model = Conversation
    template_name = "ej_conversations/conversation-detail.jinja2"
    ctx = {}


@method_decorator([check_conversation_overdue], name="dispatch")
class ConversationFavoriteView(ConversationCommonView, DetailView):
    template_name = "ej_conversations/conversation-detail.jinja2"

    @user_can_post_anonymously
    def post(self, request, *args, **kwargs):
        conversation: Conversation = self.get_object()
        request.user = User.get_or_create_from_session(conversation, request)
        self.ctx = handle_detail_favorite(request, conversation)
        return render(
            request,
            self.template_name,
            {
                **self.get_context_data(),
                "background_image_url": None,
            },
        )


@method_decorator([check_conversation_overdue], name="dispatch")
class ConversationVoteView(ConversationCommonView, DetailView):
    form_class = CommentForm
    model = Conversation
    ctx = {}

    def get(self, request, *args, **kwargs):
        conversation = self.get_object()
        request.user = User.get_or_create_from_session(conversation, request)
        return render(
            request, "ej_conversations/comments/card.jinja2", self.get_context_data()
        )

    @user_can_post_anonymously
    def post(self, request, *args, **kwargs):
        conversation = self.get_object()
        request.user = User.get_or_create_from_session(conversation, request)
        self.ctx = handle_detail_vote(request)
        return render(
            request, "ej_conversations/comments/card.jinja2", self.get_context_data()
        )


@method_decorator([login_required, can_acess_list_view], name="dispatch")
class ConversationCreateView(CreateView):
    template_name = "ej_conversations/conversation-create.jinja2"
    form_class = ConversationForm

    def post(self, request, board_slug, *args, **kwargs):
        form = self.form_class(request.POST, request.FILES)
        kwargs["board"] = self.get_board()

        if form.is_valid():
            with transaction.atomic():
                conversation = form.save_comments(
                    self.request.user, request.FILES, **kwargs
                )

            return redirect(
                reverse(
                    "boards:conversation-detail", kwargs=conversation.get_url_kwargs()
                )
            )

        return render(
            request,
            "ej_conversations/conversation-create.jinja2",
            self.get_context_data(form),
        )

    def get_context_data(self, form=None, **kwargs):
        user = self.request.user
        user_boards = Board.objects.filter(owner=user)
        return {
            "form": form or self.form_class(),
            "board": self.get_board(),
            "user_boards": user_boards,
        }

    def get_board(self) -> Board:
        board_slug = self.kwargs["board_slug"]
        return Board.objects.get(slug=board_slug)


@method_decorator([login_required, can_edit_conversation], name="dispatch")
class ConversationEditView(UpdateView):
    model = Conversation
    template_name = "ej_conversations/conversation-edit.jinja2"
    form_class = ConversationForm

    def post(self, request, conversation_id, slug, board_slug, *args, **kwargs):
        conversation = self.get_object()
        board = Board.objects.get(slug=board_slug)
        form = self.form_class(request.POST, request.FILES, instance=conversation)

        if form.is_valid():
            form.save(board=board, **kwargs)
            page = request.POST.get("next")
            url = self.get_redirect_url(conversation, page)
            return redirect(url)

        return render(request, self.template_name, self.get_context_data(form))

    def get_redirect_url(self, conversation, page):
        if page == "stereotypes":
            args = conversation.get_url_kwargs()
            return reverse("boards:stereotype-votes-list", kwargs=args)
        elif page == "moderate":
            return conversation.patch_url("conversation:moderate")
        elif conversation.is_promoted:
            return conversation.get_absolute_url()
        else:
            return reverse(
                "boards:dataviz-dashboard", kwargs=conversation.get_url_kwargs()
            )

    def get_context_data(self, form=None, **kwargs: Any):
        conversation = self.get_object()
        user = self.request.user
        return {
            "conversation": conversation,
            "form": form or self.form_class(instance=conversation),
            "can_publish": user.has_perm("ej_conversations.can_publish_promoted"),
            "board": conversation.board,
        }


@method_decorator([login_required, can_edit_conversation], name="dispatch")
class ConversationDeleteView(DeleteView):
    model = Conversation

    def get_object(self, queryset=None):
        conversation_id = self.kwargs["conversation_id"]
        return self.get_queryset().filter(pk=conversation_id).get()

    def get_success_url(self):
        conversation = self.object
        return reverse_lazy(
            "boards:conversation-list", kwargs={"board_slug": conversation.board.slug}
        )


@method_decorator(
    [login_required, can_edit_conversation, can_moderate_conversation], name="dispatch"
)
class ConversationModerateView(UpdateView):
    model = Conversation
    template_name = "ej_conversations/conversation-moderate.jinja2"
    status = Comment.STATUS

    def post(self, request, conversation_id, slug, board_slug, *args, **kwargs):
        payload = request.POST
        for status in [self.status.approved, self.status.pending, self.status.rejected]:
            if status in payload:
                comments_ids = payload.getlist(status)
                Comment.objects.filter(id__in=comments_ids).update(
                    status=Comment.STATUS_MAP[status]
                )

        return render(request, self.template_name, self.get_context_data())

    def get_context_data(self, **kwargs):
        conversation = self.get_object()

        comments = conversation.comments.annotate(
            annotation_author_name=F("author__name")
        )
        approved, pending, rejected = [
            comments.filter(status=_status).order_by("-created")
            for _status in [
                self.status.approved,
                self.status.pending,
                self.status.rejected,
            ]
        ]

        created_comments = comments.filter(author=conversation.author).order_by(
            "-created"
        )

        return {
            "conversation": conversation,
            "approved": approved,
            "pending": pending,
            "rejected": rejected,
            "created": created_comments,
            "comment_saved": False,
            "current_page": "moderate",
        }


@method_decorator(
    [login_required, can_edit_conversation, can_moderate_conversation], name="dispatch"
)
class CommentModerationView(UpdateView):
    model = Conversation
    template_name = "ej_conversations/conversation-moderate.jinja2"

    def post(self, request, conversation_id, slug, board_slug, *args, **kwargs):
        comments = request.POST.getlist("comment")
        with transaction.atomic():
            for comment in comments:
                if len(comment) > 2:
                    comment = Comment.objects.create(
                        content=comment,
                        conversation=self.get_object(),
                        author=request.user,
                        status=Comment.STATUS.approved,
                    )
        return render(request, self.template_name, self.get_context_data())

    def get_context_data(self, **kwargs):
        conversation = self.get_object()

        status = Comment.STATUS
        comments = conversation.comments.annotate(
            annotation_author_name=F("author__name")
        )
        approved, pending, rejected = [
            comments.filter(status=_status)
            for _status in [status.approved, status.pending, status.rejected]
        ]
        created_comments = comments.filter(author=conversation.author).order_by(
            "-created"
        )

        return {
            "conversation": conversation,
            "approved": approved,
            "pending": pending,
            "rejected": rejected,
            "created": created_comments,
            "comment_saved": True,
        }


@login_required
@can_edit_conversation
@can_moderate_conversation
def delete_comment(request, conversation_id, slug, board_slug):
    comment_id = request.POST.get("comment_id")
    comment = Comment.objects.get(id=int(comment_id))

    if comment.author == request.user:
        comment.delete()

    return HttpResponse(status=200)


@login_required
@can_edit_conversation
@can_moderate_conversation
def check_comment(request, conversation_id, slug, board_slug):
    comment_content = request.POST.get("comment_content")
    try:
        Comment.objects.get(content=comment_content, conversation_id=conversation_id)
        return HttpResponse(status=200)
    except Comment.DoesNotExist:
        return HttpResponse(status=204)


@login_required
@is_superuser
def update_favorite_boards(request, board_slug):
    user = request.user
    board = Board.objects.get(slug=board_slug)

    try:
        update_option = request.GET.get("updateOption", None)
        if update_option == "add":
            user.favorite_boards.add(board)
        elif update_option == "remove":
            user.favorite_boards.remove(board)
        else:
            return HttpResponse(status=404)
    except Exception:
        return HttpResponse(status=404)

    return HttpResponse(status=200)


@login_required
@is_superuser
def is_favorite_board(request, board_slug):
    user = request.user
    board = Board.objects.get(slug=board_slug)

    try:
        user.favorite_boards.get(id=board.id)
        return JsonResponse({"is_favorite_board": True})
    except Board.DoesNotExist:
        return JsonResponse({"is_favorite_board": False})
