import random
import string

import hyperpython.jinja2
from django.apps import apps
from django.conf import settings
from django.contrib.messages import get_messages
from django.contrib.staticfiles.storage import staticfiles_storage
from django.utils import translation
from django.utils.formats import date_format
from django.utils.translation import get_language
from hyperpython import html, Blob
from jinja2 import Environment, StrictUndefined, contextfunction
from sidekick import record

from . import components
from . import roles
from .breadcrumbs import get_breadcrumbs as _get_breadcrumbs
from .roles import tags
from .utils.url import SafeUrl


def environment(autoescape=True, **options):
    options.pop("debug", None)
    options.setdefault("trim_blocks", True)
    options.setdefault("lstrip_blocks", True)
    options["undefined"] = StrictUndefined
    env = Environment(autoescape=True, **options)

    env.globals.update(
        static=staticfiles_storage.url,
        url=SafeUrl,
        settings=record(
            **{k: getattr(settings, k) for k in dir(settings)},
            has_boards=apps.is_installed("ej_boards"),
            has_clusters=apps.is_installed("ej_clusters"),
            has_dataviz=apps.is_installed("ej_dataviz"),
            has_profiles=apps.is_installed("ej_profiles"),
            has_users=apps.is_installed("ej_users"),
            service_worker=getattr(settings, "SERVICE_WORKER", False),
            all=settings,
        ),
        # Localization
        get_language=get_language,
        date_format=date_format,
        # Security
        salt_attr=salt_attr,
        salt_tag=salt_tag,
        salt=salt,
        # Platform functions
        generic_context=generic_context,
        get_messages=messages,
        get_breadcrumbs=breadcrumbs,
        # Available tags and components
        render=html,
        tag=roles,
        blob=Blob,
        **FUNCTIONS,
    )
    env.filters.update(
        pc=format_percent,
        salt=salt,
        **hyperpython.jinja2.filters,
    )
    env.install_gettext_translations(translation, newstyle=True)
    return env


#
# String formatting
#
def format_percent(x):
    return f"{int(x * 100)}%"


#
# Security
#
def salted(value):
    """
    Protects a value using a random salt. This completely prevents the BREACH
    attack against a salted secret, but stores values in a codified form that
    cannot be directly used.

    The BREACH authors suggest a transform that takes a string P and returns
    (P + (S^P)), where S^P is a XOR operation of each byte. Templates do not
    have a byte-level control of the message, hence salting must be done in
    unicode data. This brings some problems:

    * How to (efficiently) implement XOR for a large alphabet such as unicode?
    * Xor-ing two valid unicode points will not necessarily yield a valid
      unicode value.
    * Client code needs to recover the encoded data, hence the solution must
      be portable to Python and Javascript
    """
    # TODO: how to do it with unicode?
    raise NotImplementedError


def salt(size=None):
    """
    Create a random string of characters of a random size.

    The goal of the random salt is to make it more difficult to execute a
    BREACH attack (https://docs.djangoproject.com/en/2.0/ref/middleware/#module-django.middleware.gzip).
    A random salt makes the attack more difficult by requiring more requests to
    correctly guess each byte in the target secret sub-string.
    """
    size = random.randint(4, 10) if size is None else size
    func = random.choice
    chars = SALT_CHARS
    return "".join(func(chars) for _ in range(size))


def salt_attr():
    """
    A salt added as an HTML attribute.
    """
    return f'data-salt="{salt()}"'


def salt_tag():
    """
    A salt added as an invisible HTML tag.
    """
    return f'<div style="display: none" {salt_attr()}></div>'


#
# Messaging and services
#
@contextfunction
def messages(ctx):
    try:
        request = ctx["request"]
    except KeyError:
        return []
    else:
        return get_messages(request)


@contextfunction
def breadcrumbs(ctx):
    """
    Builds the breadcrumb chain for the current request by matching the
    URL path against known patterns (see :mod:`ej.breadcrumbs`). Templates
    can override the auto-generated value by setting ``breadcrumb_items``
    themselves.
    """
    request = ctx.get("request")
    if request is None:
        return []
    return _get_breadcrumbs(request)


@contextfunction
def generic_context(ctx):
    """
    Renders the current context as a description list.
    """
    from django.http import Http404
    from django.utils.translation import gettext as _

    blacklist = {
        # Jinja2
        "range",
        "dict",
        "lipsum",
        "cycler",
        "joiner",
        "namespace",
        "_",
        "gettext",
        "ngettext",
        "request",
        "csrf_input",
        "csrf_token",
        # Globals
        "static",
        "url",
        "salt_attr",
        "salt_tag",
        "salt",
        "social_icons",
        "service_worker",
        "generic_context",
        "render",
        "tag",
        "settings",
        *FUNCTIONS,
        # Variables injected by the base template
        "target",
        "target_context",
        "sidebar",
        "page_top_header",
        "page_header",
        "page_title",
        "title",
        "content_title",
        "enable_navbar",
        "hide_footer",
        "javascript_enabled",
    }
    ctx = {k: v for k, v in ctx.items() if k not in blacklist}
    if settings.DEBUG:
        if ctx:
            return tags.html_map(ctx)
        else:
            return tags.h("p", _("This template defines no extra variables"))
    else:
        raise Http404


#
# Constants
#
def try_function(func, *args, **kwargs):
    try:
        return func(*args, **kwargs)
    except Exception:
        return StrictUndefined()


FUNCTIONS = {}
for _names, _mod in [(tags.__all__, tags), (dir(components), components)]:
    for _name in _names:
        value = getattr(_mod, _name, None)
        if not _name.startswith("_") and callable(value):
            FUNCTIONS[_name] = value
SALT_CHARS = string.ascii_letters + string.digits + "-_"
FUNCTIONS["try"] = try_function
