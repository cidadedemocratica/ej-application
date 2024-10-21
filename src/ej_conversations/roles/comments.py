from django.utils.translation import gettext_lazy as _


from ej.roles import with_template
from .. import models
from ..enums import RejectionReason
from ..models import Comment


@with_template(Comment, role="moderate")
def comment_moderate(comment: Comment, request=None, **kwargs):
    """
    Render a comment inside a moderation card.
    """

    moderator = getattr(comment.moderator, "name", None)
    return {
        "created": comment.created,
        "author": comment.author_name,
        "text": comment.content,
        "moderator": moderator,
    }


@with_template(Comment, role="reject-reason")
def comment_reject_reason(comment: Comment, **kwargs):
    """
    Show reject reason for each comment.
    """

    rejection_reason = comment.rejection_reason_text
    if comment.status != comment.STATUS.rejected:
        rejection_reason = None
    elif comment.rejection_reason != RejectionReason.USER_PROVIDED:
        rejection_reason = comment.rejection_reason.description

    return {
        "comment": comment,
        "conversation_url": comment.conversation.get_absolute_url(),
        "status": comment.status,
        "status_name": dict(models.Comment.STATUS)[comment.status].capitalize(),
        "rejection_reason": rejection_reason,
    }


@with_template(Comment, role="summary")
def comment_summary(comment: Comment, **kwargs):
    """
    Show comment summary.
    """
    status_icon = {"approved": "thumbtack", "rejected": "ban", "pending": "clock"}

    return {
        "created": comment.created,
        "comment_url": comment.conversation.get_absolute_url(),
        "text": comment.content,
        "status": Comment.STATUS[comment.status],
        "status_icon": status_icon.get(comment.status),
        "conversation": comment.conversation,
    }


@with_template(Comment, role="stats", template="ej/role/voting-stats.jinja2")
def comment_stats(comment: Comment, request=None):
    return {
        "agree": comment.agree_count,
        "skip": comment.skip_count,
        "disagree": comment.disagree_count,
        "request": request,
    }
