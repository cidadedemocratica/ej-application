from django.conf import settings
from django.utils.translation import gettext_lazy as _
from environ import ImproperlyConfigured
from django.db import models

_ethnicity_enums = getattr(settings, "EJ_PROFILE_ETHNICITY_CHOICES", None)
_race_enums = getattr(settings, "EJ_PROFILE_RACE_CHOICES", None)
_gender_enums = getattr(settings, "EJ_PROFILE_GENDER_CHOICES", None)
_not_filed = getattr(settings, "EJ_NOT_FILLED_MARK", "---------")
_refused_to_answer = getattr(
    settings, "EJ_REFUSED_TO_ANSWER_MARK", _("refused to answer")
)
_region_enums = getattr(settings, "EJ_PROFILE_REGION_CHOICES", None)
_age_enums = getattr(settings, "EJ_PROFILE_AGE_CHOICES", None)

# Here we fool the IntEnum metaclass into believing that items of a list are
# methods
_to_thunks = lambda lst: ((lambda: k, lambda: v) for k, v in lst)


class Ethnicity(models.IntegerChoices):
    NOT_FILLED = 0, _not_filed
    REFUSED = 7, _refused_to_answer

    if _ethnicity_enums is None:
        INDIGENOUS = 1, _("Indigenous")
        BLACK = 2, _("Black")
        BROWN = 3, _("Brown")
        WHITE = 4, _("White")
        YELLOW = 5, _("Yellow")
        OTHER = 6, _("Other")
    else:
        for _k, _v in _to_thunks(_ethnicity_enums.items()):
            locals()[_k()] = _v()


class Race(models.IntegerChoices):
    NOT_FILLED = 0, _not_filed
    REFUSED = 7, _refused_to_answer

    def __str__(self):
        return "Race"

    if _race_enums is None:
        BLACK = 1, _("Black")
        BROWN = 2, _("Brown")
        WHITE = 3, _("White")
        YELLOW = 4, _("Yellow")
        INDIGENOUS = 5, _("Indigenous")
        OTHER = 6, _("Other")
    else:
        for _k, _v in _to_thunks(_race_enums.items()):
            locals()[_k()] = _v()


class Region(models.IntegerChoices):
    NOT_FILLED = 0, _not_filed
    REFUSED = 6, _refused_to_answer

    if _region_enums is None:
        NORTH = 1, _("North")
        NORTHEAST = 2, _("Northeast")
        MIDWEST = 3, _("Midwest")
        SOUTHEAST = 4, _("Southeast")
        SOUTH = 5, _("South")
    else:
        for _k, _v in _to_thunks(_region_enums.items()):
            locals()[_k()] = _v()


class Gender(models.IntegerChoices):
    NOT_FILLED = 0, _not_filed
    REFUSED = 5, _refused_to_answer

    if _gender_enums is None:
        FEMALE = 1, _("Female")
        MALE = 2, _("Male")
        NO_BINARY = 3, _("Non-binary")
        OTHER = 4, _("Other")
    else:
        for _k, _v in _to_thunks(_gender_enums.items()):
            locals()[_k()] = _v()


class AgeRange(models.IntegerChoices):
    NOT_FILLED = 0, _not_filed
    REFUSED = 7, _refused_to_answer

    if _age_enums is None:
        RANGE_1 = 1, _("Less than 17 years")
        RANGE_2 = 2, _("Between 17-20 years")
        RANGE_3 = 3, _("Between 21-29 years")
        RANGE_4 = 4, _("Between 30-45 years")
        RANGE_5 = 5, _("Between 45-60 years")
        RANGE_6 = 6, _("Over 60 years")
    else:
        for _k, _v in _to_thunks(_age_enums.items()):
            locals()[_k()] = _v()


STATE_CHOICES = getattr(settings, "EJ_PROFILE_STATE_CHOICES", {})
STATE_CHOICES_MAP = dict(STATE_CHOICES)
if not STATE_CHOICES:
    raise ImproperlyConfigured(
        "You must define the environment variable EJ_PROFILE_STATE_CHOICES in "
        "your Django settings."
    )

# Those are profile field name translations that should be captured by gettext.
FIELD_TRANSLATIONS = [
    _("user"),
    _("race"),
    _("ethnicity"),
    _("education"),
    _("gender"),
    _("gender_other"),
    _("gender other"),
    _("birth_date"),
    _("birth date"),
    _("country"),
    _("state"),
    _("city"),
    _("biography"),
    _("occupation"),
    _("political_activity"),
    _("political activity"),
    _("profile_photo"),
    _("profile photo"),
    _("name"),
    _("email"),
    _("is_active"),
    _("is active"),
    _("is_staff"),
    _("is staff"),
    _("is_superuser"),
    _("is superuser"),
    _("limit_board_conversations"),
    _("limit board conversations"),
]
