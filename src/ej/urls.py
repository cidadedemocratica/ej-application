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
from rest_framework.documentation import include_docs_urls

from ej import services
from ej.fixes import unregister_admin

unregister_admin.unregister_apps()


#
# Optional urls
#
def get_urlpatterns():
    fixes()

    patterns = [
        #
        # Basic authentication and authorization
        path("", include("ej.routes")),
        *with_app("ej_users", "", namespace="auth"),
        *with_app("ej_users", "account/", "routes_account", namespace="account"),
        #
        #  Conversations and other EJ-specific routes
        path("conversations/", include("ej_conversations.routes", namespace="conversation")),
        path("", include("ej_conversations.tools.routes", namespace="conversation_tools")),
        path("comments/", include("ej_conversations.routes_comments", namespace="comments")),
        #
        #  Profile URLS
        *with_app("ej_profiles", "profile/", namespace="profile"),
        *with_app("ej_notifications", "notifications/", namespace="notifications"),
        #
        #  Data visualization
        *with_app("ej_dataviz", "conversations/", namespace="dataviz"),
        *with_app("ej_dataviz", "conversations/", routes="routes_report", namespace="report"),
        #
        #  Global stereotype and cluster management
        *with_app("ej_clusters", "conversations/", namespace="cluster"),
        *with_app("ej_clusters", "stereotypes/", routes="routes_stereotypes", namespace="stereotypes"),
        #
        #  Gamification
        *with_app("ej_gamification", "profile/", namespace="gamification"),
        *with_app("ej_gamification", "leaderboard/", routes="routes_leaderboard", namespace="leaderboard"),
        *with_app(
            "ej_gamification",
            "conversations/",
            routes="routes_conversation",
            namespace="conversation-achievement",
        ),
        #
        #  Rocket.chat integration
        *with_app("ej_rocketchat", "talks/", namespace="rocket"),
        #
        #  Allauth
        path("accounts/", include("allauth.urls")),
        #
        #  Admin
        *(
            [path(fix_url(settings.ADMIN_URL.lstrip("/")), admin.site.urls)]
            if apps.is_installed("django.contrib.admin")
            else ()
        ),
        #
        # Debug routes
        *with_app("ej_experiments", "info/experiments/", namespace="experiments"),
        #
        #  REST API
        path("api/", include(rest_api.urls)),
        path("api/v1/docs/", include_docs_urls(title="ej API Docs", public=False)),
        #
        #  REST API for user management
        path('rest-auth/', include('rest_auth.urls')),
        path('rest-auth/registration/', include('rest_auth.registration.urls')),
        # Static files for the dev server
        *static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT),
        *static(settings.STATIC_URL, document_root=settings.STATIC_ROOT),
        #
        #  Documentation in development mode
        re_path(r"^static_docs/$", serve, {"document_root": "build/docs", "path": "index.html"}),
        re_path(r"^static_docs/(?P<path>.*)$", serve, {"document_root": "build/docs/"}),
        #
        #  Boards
        *with_app("ej_boards", "", namespace="boards"),
    ]

    if settings.DEBUG:
        # Pages for error codes
        patterns.extend(
            [
                path(
                    "error/400/", default_views.bad_request, kwargs={"exception": Exception("Bad Request!")}
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


def with_app(app, url, routes="routes", namespace=None):
    if apps.is_installed(app):
        return [path(url, include(f"{app}.{routes}", namespace=namespace))]
    else:
        return []


services.start_services(settings)
urlpatterns = get_urlpatterns()
