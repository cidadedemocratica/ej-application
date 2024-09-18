from django.db.models import TextChoices
from django.utils.translation import gettext_lazy as _

from boogie.fields import IntEnum
from ej_conversations.enums import Choice


class StereotypeVoteChoices(TextChoices):

    agree = "agree"
    disagree = "disagree"
    skip = "skip"
    __empty__ = "--------"


FORM_CHOICE_MAP = {
    "1": "agree",
    "-1": "disagree",
    "0": "skip",
    "": "--------",
}

CHOICE_MAP = {"agree": Choice.AGREE, "disagree": Choice.DISAGREE, "skip": Choice.SKIP}


class ClusterStatus(IntEnum):
    PENDING_DATA = 0, _("Waiting for more data")
    ACTIVE = 1, _("Active")
    DISABLED = 2, _("Disabled")

    # FIXME: deprecated, a future boogie version will implement this!
    @classmethod
    def normalize(cls, obj):
        """
        Normalize enumeration that can be passed as value or a string argument.
        """
        if isinstance(obj, cls):
            return obj
        elif isinstance(obj, str):
            value = getattr(cls, obj.upper(), None)
            if value is None:
                raise ValueError(f"invalid {cls.__name__}: {obj}")
            elif isinstance(obj, int):
                return cls(obj)
            else:
                raise TypeError(type(obj))
