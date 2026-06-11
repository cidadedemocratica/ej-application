"""
Path-based breadcrumb builder.

Follows a URL path-based approach: breadcrumbs are derived from the current
request path by matching accumulated path segments against known URL patterns.
"""

from dataclasses import dataclass, field
from typing import Any

from django.utils.translation import gettext_lazy as _


@dataclass
class BreadcrumbItem:
    title: str
    url: str | None
    params: dict[str, Any]


@dataclass
class BreadcrumbItems:
    items: list[BreadcrumbItem]
    apps_url: dict[str, tuple[str, Any]] = field(
        default_factory=lambda: _get_apps_url()
    )


ROUTE_LABELS = {
    "boards:conversation-list": _("Mural"),
    "boards:conversation-detail": _("Conversation"),
    "boards:conversation-create": _("New Conversation"),
    "boards:conversation-edit": _("Settings"),
}

SKIPPED_ROUTES = {
    "boards:board-base",
}

BREADCRUMB_CURRENT_ROUTES = {
    "boards:conversation-create",
    "boards:conversation-edit",
}


def _get_apps_url():
    from ej_boards.urls import urlpatterns as boards_urlpatterns

    return {
        "boards": ("boards", boards_urlpatterns),
    }


def _home_breadcrumb():
    return BreadcrumbItem(
        title="Home",
        url="/profile/home/",
        params={},
    )


def _route_label(view_name, fallback):
    return ROUTE_LABELS.get(view_name, fallback.replace("-", " ").title())


def _match_pattern(pattern, path):
    match = pattern.match(path)
    if not match:
        return None

    remaining_path, args, kwargs = match
    if remaining_path:
        return None
    return kwargs


def _path_candidates(parts):
    path = ""
    for part in parts:
        path = f"{path}{part}/"
        yield path, part


def _django_breadcrumb(app_slug, crumbs, breadcrumbs):
    app_config = breadcrumbs.apps_url.get(app_slug)
    if app_config is None:
        return []

    namespace, urlpatterns = app_config
    items = [_home_breadcrumb()]
    current_view_name = None

    for path, crumb in _path_candidates(crumbs):
        for urlpattern in urlpatterns:
            kwargs = _match_pattern(urlpattern.pattern, path)
            if kwargs is None:
                continue

            view_name = f"{namespace}:{urlpattern.name}"
            if view_name in SKIPPED_ROUTES:
                continue

            current_view_name = view_name
            items.append(
                BreadcrumbItem(
                    title=_route_label(view_name, crumb),
                    url=f"/{app_slug}/{path}",
                    params=kwargs,
                )
            )

    if current_view_name not in BREADCRUMB_CURRENT_ROUTES:
        return []

    if items:
        items[-1].url = None
    return items


def get_breadcrumbs(request):
    """
    Build a root-to-current breadcrumb chain for the current request path.

    Returns dicts compatible with the existing Jinja breadcrumb macro.
    """
    path = getattr(request, "path", "")
    crumbs = [crumb for crumb in path.split("/") if crumb]
    if not crumbs:
        return []

    app_slug = crumbs[0]
    breadcrumbs = BreadcrumbItems(items=[])
    items = _django_breadcrumb(app_slug, crumbs[1:], breadcrumbs)
    return [{"label": item.title, "url": item.url} for item in items]
