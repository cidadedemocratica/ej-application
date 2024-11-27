from logging import getLogger

from django.core.exceptions import ValidationError
from django.http import Http404, HttpResponse
from django.utils.translation import gettext_lazy as _
from sidekick import import_later

from ej.components.builtins import toast

log = getLogger("ej")
models = import_later(".models", package=__package__)
forms = import_later(".forms", package=__package__)


#
# Functions
#


def request_comes_from_ej_bot(request):
    return request_promoted_conversations(request) and (
        request.GET.get("participation_source") == "bot"
    )


def request_promoted_conversations(request):
    return request.GET.get("is_promoted") == "true"


def check_promoted(conversation, request):
    """
    Raise a Http404 if conversation is not promoted
    """
    user = request.user
    if user.is_staff or user.is_superuser or user.id == conversation.author_id:
        return conversation
    if not conversation.is_promoted or conversation.is_hidden:
        raise Http404
    return conversation


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
        content = form.cleaned_data.get("content")
        user = request.user
        new_comment = conversation.create_comment(user, content)
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

    log.info(f"user {user.id} toggled favorite status of conversation {conversation.id}")
    return {}


def get_htmx_redirect_response(url, response=None):
    """
    Participation page uses HTMX library to make backend AJAX requests.
    In order to make a redirect with HTMX,
    we need to include HX-Redirect header to the response.
    For more information, access https://htmx.org/reference/.
    """

    _response = response or HttpResponse()
    _response["HX-Redirect"] = url
    _response.status_code = 302
    return _response
