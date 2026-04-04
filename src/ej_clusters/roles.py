from django.utils.translation import gettext_lazy as _
from hyperpython import html

from ej.roles import extra_content
from ej_conversations import models


@html.register(models.Conversation, role="opinion-groups-summary")
def opinion_groups_summary(conversation, request=None, **kwargs):
    """
    Render comment form for one conversation.
    """
    n_groups = 3
    group_id = 2
    msg = _(
        "This conversation has {n_groups} groups, "
        "and you are in group {group_id}."
    ).format(n_groups=n_groups, group_id=group_id)
    return extra_content(_("Opinion groups"), msg, icon="chart-pie")
