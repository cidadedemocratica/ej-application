from logging import getLogger

from django.contrib import messages
from django.core.exceptions import ValidationError
from django.http import Http404, HttpResponseServerError
from django.utils.html import escape
from django.utils.translation import ugettext_lazy as _
from hyperpython import a
from sidekick import import_later

log = getLogger("ej")
models = import_later(".models", package=__package__)
forms = import_later(".forms", package=__package__)


#
# Functions
#
def check_promoted(conversation, request):
    """
    Raise a Http404 if conversation is not promoted
    """
    if not conversation.is_promoted:
        raise Http404
    if conversation.is_hidden and not request.user.has_perm(
        "ej.can_edit_conversation", conversation
    ):
        raise Http404
    return conversation


def handle_detail_post(request, conversation, action):
    """
    Process a POST in a conversation:detail view..
    """

    if action == "vote":
        return handle_detail_vote(request)
    elif action == "comment":
        return handle_detail_comment(request, conversation)
    elif action == "favorite":
        return handle_detail_favorite(request, conversation)
    else:
        log.warning(
            f"user {request.user.id} se nt invalid POST request: {request.POST}"
        )
        return HttpResponseServerError("invalid action")


def conversation_admin_menu_links(conversation, user):
    """
    Return administrative links to the conversation menu.
    """

    menu_links = []
    if user.has_perm("ej.can_edit_conversation", conversation):
        url = conversation.url("conversation:edit")
        menu_links.append(a(_("Edit"), href=url))
    if user.has_perm("ej.can_moderate_conversation", conversation):
        url = conversation.url("conversation:moderate")
        menu_links.append(a(_("Moderate"), href=url))
    return menu_links


def votes_counter(comment, choice=None):
    """
    Count the number of votes in comment.
    """
    if choice is not None:
        return comment.votes.filter(choice=choice).count()
    else:
        return comment.votes.count()


def normalize_status(value):
    """
    Convert status string values to safe db representations.
    """
    from ej_conversations.models import Comment

    if value is None:
        return Comment.STATUS.pending
    try:
        return Comment.STATUS_MAP[value.lower()]
    except KeyError:
        raise ValueError(f"invalid status value: {value}")


#
# Auxiliary classes
#
def handle_detail_vote(request):
    """
    User is voting in the current comment. We still need to choose a random
    comment to display next.
    """
    data = request.POST
    user = request.user
    vote = data["vote"]
    comment_id = data["comment_id"]
    try:
        models.Comment.objects.get(id=comment_id).vote(user, vote)
        toast(request, _("Thanks for voting."))

        log.info(f"user {user.id} voted {vote} on comment {comment_id}")
    except ValidationError:
        # User voted twice and too quickly... We simply ignore the last vote
        log.info(f"duplicated vote for user {user.id} on comment {comment_id}")
    return {}


def handle_detail_comment(request, conversation):
    """
    User is posting a new comment. We need to validate the form and try to
    keep the same comment that was displayed before.
    """
    form = forms.CommentForm(conversation=conversation, request=request)
    if form.is_valid():
        new_comment = form.cleaned_data["content"]
        user = request.user
        new_comment = conversation.create_comment(user, new_comment)
        toast(request, _("Your comment has been saved."))
        log.info(f"user {user.id} posted comment {new_comment.id} on {conversation.id}")
    return {"form": form}


def handle_detail_favorite(request, conversation):
    """
    User toggled the favorite status of conversation.
    """
    user = request.user
    is_favorite = conversation.toggle_favorite(user)
    if is_favorite:
        toast(request, _("This conversation is now favorite."))
    else:
        toast(request, _("Conversation removed from favorites."))

    log.info(
        f"user {user.id} toggled favorite status of conversation {conversation.id}"
    )


def toast(request, msg, **kwargs):
    messages.info(request, escape(msg), **kwargs)
