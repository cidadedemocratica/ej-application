from django.utils.translation import gettext_lazy as _
from django.db import models


class RejectionReason(models.IntegerChoices):
    """
    Possible rejection reasons for a comment.
    """

    USER_PROVIDED = 0, _("User provided")
    INCOMPLETE_TEXT = (10, _("Incomplete or incomprehensible text"))
    OFF_TOPIC = (20, _("Off-topic"))
    OFFENSIVE_LANGUAGE = (30, _("Offensive content or language"))
    DUPLICATED_COMMENT = (40, _("Duplicated content"))
    VIOLATE_TERMS_OF_SERVICE = (50, _("Violates terms of service of the platform"))


class Choice(models.IntegerChoices):
    """
    Options for a user vote.
    """

    SKIP = 0, _("Skip")
    AGREE = 1, _("Agree")
    DISAGREE = -1, _("Disagree")

    @classmethod
    def normalize(cls, choice):
        """
        Converts 'agree', 'skip' and 'disagree' to 1, 0 and -1.
        It also converts '-1', '1' and '0' to -1, 1, and 0.
        """

        if choice is None or choice == "":
            return None

        if type(choice) == Choice:
            return choice.value

        if len(str(choice)) <= 2:
            if int(choice) in cls:
                return int(choice)
            else:
                raise ValueError

        try:
            return cls[choice.upper()].value
        except KeyError as e:
            raise e
