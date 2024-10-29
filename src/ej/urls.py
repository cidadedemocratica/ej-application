import logging

from boogie.rest import rest_api
from django.apps import apps
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.auth import get_user_model
from django.core.exceptions import ImproperlyConfigured
from django.urls import include, path, re_path
from django.views import defaults as default_views
from django.views.static import serve
from ej import services
from ej import views
from ej.fixes import unregister_admin
from ej_boards.api import BoardViewSet
from ej_clusters.api import ClusterizationViewSet
from ej_conversations.api import CommentViewSet, ConversationViewSet, VoteViewSet
from ej_profiles.api import ProfileViewSet
from ej_integrations.api import OpinionComponentViewSet, RasaConversationViewSet
from ej_users.api import TokenViewSet, UsersViewSet
from rest_framework.routers import DefaultRouter
from drf_spectacular.views import SpectacularSwaggerView, SpectacularAPIView

unregister_admin.unregister_apps()

api_router = DefaultRouter()
api_router.register(
    r"rasa-conversations", RasaConversationViewSet, basename="v1-rasa-conversations"
)
api_router.register(
    r"opinion-component", OpinionComponentViewSet, basename="v1-opinion-component"
)
api_router.register(r"conversations", ConversationViewSet, basename="v1-conversations")
api_router.register(r"comments", CommentViewSet, basename="v1-comments")
api_router.register(r"votes", VoteViewSet, basename="v1-votes")
api_router.register(
    r"clusterizations", ClusterizationViewSet, basename="v1-clusterizations"
)
api_router.register(r"profiles", ProfileViewSet, basename="v1-profiles")
api_router.register(r"boards", BoardViewSet, basename="v1-boards")
api_router.register(r"users", UsersViewSet, basename="v1-users")
api_router.register(r"", TokenViewSet, basename="v1-auth")

log = logging.getLogger("ej")


def get_apps_dynamic_urls():
    """
    Allows apps to include new urls without editing ej/urls.py directly.
    In order to include new urls, the app must implements the get_app_urls method,
    inside the apps.py file. The method must return a namespaced path, for example:

    def get_app_urls(self):
        from my_app.views import View
        from django.urls import path

        urlpatterns = [path("path/", View.as_view(), name="path")]
        return path("customapp/", include(urlpatterns, namespace="customapp"))

    Checks ej_activation app, for example.
    """
    apps_urls = []
    for app_config in apps.app_configs:
        try:
            get_app_urls = getattr(apps.app_configs[app_config], "get_app_urls")
            apps_urls += [get_app_urls()]
            log.info(f"Including {app_config} URLs using get_apps_dynamic_urls()")
        except Exception:
            pass
    return apps_urls


def get_urlpatterns():
    fixes()

    patterns = [
        #
        # Basic authentication and authorization
        path(
            "",
            views.IndexView.as_view(),
            name="index",
        ),
        path(
            "info/styles/",
            views.InfoStylesView.as_view(),
            name="info-styles",
        ),
        path(
            "info/django-settings/",
            views.InfoDjangoSettingsView.as_view(),
            name="info-django-settings",
        ),
        path(
            "info/environment/",
            views.InfoEnvironView.as_view(),
            name="info-environ",
        ),
        path(
            "sw.js",
            views.ServiceWorkerView.as_view(),
            name="service-worker",
        ),
        path("", include("ej_users.urls.user", namespace="auth")),
        path("", include("ej_users.urls.account", namespace="account")),
        #
        #  Conversations and other EJ-specific routes
        path(
            "conversations/",
            include(
                "ej_conversations.urls.public_conversations", namespace="conversation"
            ),
        ),
        path(
            "comments/", include("ej_conversations.urls.comments", namespace="comments")
        ),
        #
        #  Profile URLS
        path("profile/", include("ej_profiles.urls", namespace="profile")),
        #
        #  Data visualization
        path("conversations/", include("ej_dataviz.urls", namespace="dataviz")),
        #
        # Administration Routes
        path("administration/", include("ej_admin.urls", namespace="administration")),
        #
        #  Global stereotype and cluster management
        path("conversations/", include("ej_clusters.urls.clusters", namespace="cluster")),
        path(
            "conversations/",
            include("ej_clusters.urls.stereotype_votes", namespace="stereotype-votes"),
        ),
        path(
            "stereotypes/",
            include("ej_clusters.urls.stereotypes", namespace="stereotypes"),
        ),
        #
        #  Documentation in development mode
        re_path(r"^docs/$", serve, {"document_root": "build/docs", "path": "index.html"}),
        re_path(r"^docs/(?P<path>.*)$", serve, {"document_root": "build/docs/"}),
        #
        #  Admin
        *(
            [path(fix_url(settings.ADMIN_URL.lstrip("/")), admin.site.urls)]
            if apps.is_installed("django.contrib.admin")
            else ()
        ),
        #
        # Boards URLs
        path("", include("ej_boards.urls", namespace="boards")),
        #
        #  Allauth
        path("accounts/", include("allauth.urls")),
        #
        #  REST API
        path("api/v1/", include(api_router.urls)),
        path("api/", include(rest_api.urls)),
        path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
        path(
            "api/v1/swagger/",
            SpectacularSwaggerView.as_view(url_name="schema"),
            name="swagger",
        ),
        # Static files for the dev server
        *static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT),
        *static(settings.STATIC_URL, document_root=settings.STATIC_ROOT),
        *get_apps_dynamic_urls(),
    ]

    if settings.DEBUG:
        # Pages for error codes
        patterns.extend(
            [
                path(
                    "error/400/",
                    default_views.bad_request,
                    kwargs={"exception": Exception("Bad Request!")},
                ),
                path(
                    "error/403/",
                    default_views.permission_denied,
                    kwargs={"exception": Exception("Permission Denied")},
                ),
                path(
                    "error/404/",
                    default_views.page_not_found,
                    kwargs={"exception": Exception("Page not Found")},
                ),
                path("error/500/", default_views.server_error),
                path("roles/", include("ej.roles.routes")),
            ]
        )

        if "debug_toolbar" in settings.INSTALLED_APPS:
            import debug_toolbar

            patterns.append(path("__debug__/", include(debug_toolbar.urls)))
    return patterns


def fix_url(url):
    return url.strip("/") + "/"


def fixes():
    if not apps.is_installed("ej_users"):
        user = get_user_model()
        try:
            rest_api.get_resource_info(user)
        except ImproperlyConfigured:
            rest_api(["username"])(user)


services.start_services(settings)
urlpatterns = get_urlpatterns()
