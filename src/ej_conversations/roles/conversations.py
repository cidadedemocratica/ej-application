from boogie import rules
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from hyperpython import a, html, Blob, div
from hyperpython.django import csrf_input

from ej.roles import with_template, progress_bar
from .. import forms
from .. import models


@with_template(models.Conversation, role="balloon")
def conversation_balloon(
    conversation, request=None, actions=None, is_favorite=False, **kwargs
):
    """
    Render details of a conversation inside a conversation balloon.
    """

    user = getattr(request, "user", None)

    # Share and favorite actions bellow the balloon
    if actions is not False:
        is_authenticated = getattr(user, "is_authenticated", False)
        is_favorite = is_authenticated and conversation.is_favorite(user)
        if actions is None:
            actions = is_authenticated

    return {
        "text": conversation.text,
        "user": user,
        "tags": conversation.tag_names,
        "hidden": conversation.is_hidden,
        "is_favorite": is_favorite,
        "actions": actions,
    }


@with_template(models.Conversation, role="card")
def conversation_card(
    conversation, url=None, request=None, text=None, hidden=None, button_text=""
):
    """
    Render a round card representing a conversation in a list.
    """

    # Non-authenticated users do not have progress
    if request and request.user.is_authenticated:
        progress = conversation_user_progress(conversation, request=request)
    else:
        progress = None

    return {
        "author": conversation.author_name,
        "text": text or conversation.text,
        "progress": progress,
        "hidden": conversation.is_hidden if hidden is None else hidden,
        "url": url or conversation.get_absolute_url(),
        "tag": conversation.first_tag,
        "n_comments": conversation.n_approved_comments,
        "n_votes": conversation.n_final_votes,
        "n_favorites": conversation.n_favorites,
        "button_text": button_text,
    }


@with_template(models.Conversation, role="comment-form")
def conversation_comment_form(
    conversation, request=None, content=None, user=None, form=None, target=None
):
    """
    Render comment form for conversation.
    """
    # Check user credentials
    user = user or getattr(request, "user", None)
    if not user.is_authenticated:
        conversation_url = conversation.get_absolute_url()
        login = reverse("auth:login")
        return {
            "user": None,
            "login_anchor": a(
                _("login"), href=f"{login}?next={conversation_url}"
            ),
        }

    # Check if user still have comments left
    n_comments = rules.compute("ej.remaining_comments", conversation, user)
    if n_comments <= 0:
        return {"comments_exceeded": True, "user": user}

    # Everything is ok, proceed ;)
    return {
        "user": user,
        "csrf_input": csrf_input(request),
        "n_comments": n_comments,
        "content": content,
        "target": target or "main",
        "form": form
        or forms.CommentForm(request=request, conversation=conversation),
    }


@html.register(models.Conversation, role="create-comment")
def conversation_create_comment(conversation, request=None, **kwargs):
    """
    Render "create comment" button for one conversation.
    """
    conversation.set_request(request)
    if request and request.user.is_anonymous:
        n_comments, n_moderation = [0, 0]
    else:
        n_comments, n_moderation = [
            conversation.n_user_total_comments,
            conversation.n_pending_comments,
        ]

    fn = rules.get_value("ej.max_comments_per_conversation")
    max_comments = fn()

    moderation_msg = _("{n} awaiting moderation").format(n=n_moderation)
    comments_count = _("{n} of {m} comments").format(
        n=n_comments, m=max_comments
    )

    return div(
        Blob(
            f"{comments_count}"
            f'<div class="text-7 strong">{moderation_msg}</div>'
        ),
        id="create-comment",
        class_="extra-content",
    )


@html.register(models.Conversation, role="detail-page-extra")
def conversation_detail_page_extra(conversation, **kwargs):
    return ""


@with_template(models.Conversation, role="summary")
def conversation_summary(conversation, request=None):
    """
    Show only essential information about a conversation.
    """

    return {
        "text": conversation.text,
        "tag": conversation.first_tag or _("Conversation"),
        "created": conversation.created,
        "url": conversation.get_absolute_url(),
    }


@html.register(models.Conversation, role="user-progress")
def conversation_user_progress(conversation, request=None, user=None, **kwargs):
    """
    Render comment form for one conversation.
    """

    user = user or request.user
    total = conversation.n_approved_comments
    n = 0
    if not user.is_anonymous:
        conversation.for_user = user
        n = conversation.n_user_final_votes
    return progress_bar(min(n, total), total, **kwargs)


@html.register(models.Conversation, role="user-home-progress")
def conversation_user_home_progress(
    conversation, request=None, user=None, **kwargs
):
    """
    Render comment form for one conversation.
    """

    user = user or request.user
    total = conversation.n_approved_comments
    n = 0
    kwargs["text"] = str(_(" comments"))
    kwargs["class_name"] = "progress-bar--simple"
    kwargs["extended_text"] = _(" of ")
    if not user.is_anonymous:
        conversation.for_user = user
        n = conversation.n_user_final_votes
    return progress_bar(min(n, total), total, **kwargs)
