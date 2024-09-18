from typing import Sequence
from sidekick import import_later
from django.conf import settings
from django.utils.translation import gettext_lazy as _

from ej_profiles.enums import Gender, Race, STATE_CHOICES

np = import_later("numpy")
#
# Grouping constants
#
def field_descriptor(enum):
    def formatter(x):
        if isinstance(x, str):
            return x
        elif x is None or x == 0 or np.isnan(x):
            return None
        elif x == [1, 2, 3, 4, 5, 6, 20]:
            return enum(x).description

    return formatter


def get_state_colors(states: Sequence):
    keys = set(states)
    keys.discard("")

    # We try to infer better colors for special configurations
    # For now, only Brazil is supported. It colors according to geographic region.
    if is_brazil(keys):
        cmap = state_colors_brazil(*COLORS[:5])
        return [cmap[st] for st in states]

    # Generic procedure: 1 color per state
    colors = COLORS[:]
    while len(colors) < len(states):
        colors.extend(COLORS)
    return colors[: len(states)]


def is_brazil(states: set):
    return states == {
        "AC",
        "AL",
        "AP",
        "AM",
        "BA",
        "CE",
        "DF",
        "ES",
        "GO",
        "MA",
        "MT",
        "MS",
        "MG",
        "PA",
        "PB",
        "PR",
        "PE",
        "PI",
        "RJ",
        "RN",
        "RS",
        "RO",
        "RR",
        "SC",
        "SP",
        "SE",
        "TO",
    }


def state_colors_brazil(N, NE, CW, SE, S):
    return {
        "AC": N,
        "AL": NE,
        "AP": N,
        "AM": N,
        "BA": NE,
        "CE": NE,
        "DF": CW,
        "ES": SE,
        "GO": CW,
        "MA": NE,
        "MT": CW,
        "MS": CW,
        "MG": SE,
        "PA": N,
        "PB": NE,
        "PR": S,
        "PE": NE,
        "PI": NE,
        "RJ": SE,
        "RN": NE,
        "RS": S,
        "RO": N,
        "RR": N,
        "SC": S,
        "SP": SE,
        "SE": NE,
        "TO": CW,
    }


VALID_GROUP_BY = {"gender": "profile__gender", "race": "profile__race"}

GROUP_NAMES = {
    "gender": lambda x: None if x is None else Gender(x).name.lower(),
    "race": lambda x: None if x is None else Race(x).name.lower(),
}

GROUP_DESCRIPTIONS = {
    "gender": lambda x: None if x is None else Gender(x).description,
    "race": lambda x: None if x is None else Race(x).description,
}

EXPOSED_PROFILE_FIELDS = (
    "race",
    "gender",
    "age",
    "occupation",
    "education",
    "country",
    "state",
)

# Reference: https://en.wikipedia.org/wiki/List_of_ISO_639-1_codes
NORMALIZE_LANGUAGES = {
    "ar": "arabic",
    "bg": "bulgarian",
    "ca": "catalan",
    "cs": "czech",
    "da": "danish",
    "de": "german",
    "en": "english",
    "es": "spanish",
    "fi": "finnish",
    "fr": "french",
    "hi": "hindi",
    "hu": "hungarian",
    "id": "indonesian",
    "it": "italian",
    "nl": "dutch",
    "no": "norwegian",
    "pl": "polish",
    "pt": "portuguese",
    "ro": "romanian",
    "ru": "russian",
    "sk": "slovak",
    "sv": "swedish",
    "tr": "turkish",
    "uk": "ukrainian",
    "vi": "vietnamese",
}

COLORS = [
    "#042A46",
    "#FF3E72",
    "#30BFD3",
    "#36C273",
    "#7758B3",
    "#797979",
    "#F68128",
    "#C4F2F4",
    "#B4FDD4",
    "#FFE1CA",
    "#E7DBFF",
    "#FFE3EA",
    "#EEEEEE",
]
SYMBOLS = ["circle", "rect", "triangle", "diamond", "arrow", "roundRect", "pin"]
FIELD_NAMES = getattr(settings, "EJ_PROFILE_FIELD_NAMES", {})
PIECEWISE_OPTIONS = {
    "piecewise": True,
    "bottom": 0,
    "orient": "vertical",
    "left": 10,
    "top": 10,
    "outOfRange": {"opacity": 0.25, "colorSaturation": 0.0},
}
VALID_STATE_CHOICES = sorted((st for st, _ in STATE_CHOICES if st))
FIELD_DATA = {
    "gender": {
        "query": "profile__gender",
        "name": FIELD_NAMES.get("gender", _("Gender")),
        "visual_map": {
            **PIECEWISE_OPTIONS,
            "categories": [choice.label for choice in Gender if choice.value != 0],
            "inRange": {"color": COLORS[: len(list(Gender))]},
        },
        "transform": lambda col: col.apply(field_descriptor(Gender)),
    },
    "race": {
        "query": "profile__race",
        "name": FIELD_NAMES.get("race", _("Race")),
        "visual_map": {
            **PIECEWISE_OPTIONS,
            "categories": [choice.label for choice in Race if choice.value != 0],
            "inRange": {"color": COLORS[: len(list(Race))]},
        },
        "transform": lambda col: col.apply(field_descriptor(Race)),
    },
    "state": {
        "query": "profile__state",
        "name": FIELD_NAMES.get("state", _("State")),
        "visual_map": {
            "piecewise": True,
            "padding": [20, 5, 5, 10],
            "top": "center",
            "outOfRange": PIECEWISE_OPTIONS["outOfRange"],
            "categories": VALID_STATE_CHOICES,
            "inRange": {"color": get_state_colors(VALID_STATE_CHOICES)},
            "itemGap": 2,
            "textStyle": {"fontSize": 8},
            "legend": {"type": "scroll"},
        },
        "transform": lambda x: x,
    },
    "name": {"query": "name", "name": _("Name")},
}
