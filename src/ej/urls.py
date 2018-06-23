from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from django.views import defaults as default_views
from rest_framework.documentation import include_docs_urls

from boogie.rest import rest_api
from ej.fixes import unregister_admin

unregister_admin.unregister_apps()

#
# Optional urls
#
if settings.EJ_ENABLE_ROCKETCHAT:
    rocket = [path('talks/', include('ej_rocketchat.routes', namespace='rocketchat'))]
else:
    rocket = []

urlpatterns = [
    # Basic authentication and authorization
    path('', include('ej.routes')),
    path('', include('ej_users.routes', namespace='auth')),
    path('', include('ej_help.routes', namespace='help')),

    # Profile URLS
    path('profile/', include(('ej_profiles.routes', 'ej_profiles'), namespace='profiles')),
    path('profile/', include('ej_gamification.routes', namespace='gamification')),
    path('profile/notifications/', include('ej_notifications.routes', namespace='notifications')),

    # Conversations and other EJ-specific routes
    path('conversations/', include('ej_conversations.routes', namespace='conversation')),
    path('conversations/', include('ej_clusters.routes', namespace='cluster')),
    path('conversations/', include('ej_reports.routes', namespace='report')),

    # User conversations
    path('', include('ej_conversations.routes.for_user', namespace='user-conversation')),

    # Configurations
    path('config/', include(('ej_configurations.routes', 'ej_configurations'), namespace='configurations')),

    # Rocket
    *rocket,

    # Admin
    path(settings.ADMIN_URL.rstrip('^'), admin.site.urls),

    # REST API
    path('api/', include(rest_api.urls)),
    path('api/v1/docs/', include_docs_urls(title='ej API Docs', public=False)),
    path('api/v1/missions', include('ej_missions.urls')),
    path('api/v1/rocketchat/', include('ej_rocketchat.routes')),

    # User management
    path('rest-auth/', include('rest_auth.urls')),
    path('rest-auth/registration/', include('rest_auth.registration.urls')),

    # Static files for the dev server
    *static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT),
    *static(settings.STATIC_URL, document_root=settings.STATIC_ROOT),
]

if settings.DEBUG:
    # Pages for error codes
    urlpatterns.extend([
        path('error/400/', default_views.bad_request, kwargs={'exception': Exception('Bad Request!')}),
        path('error/403/', default_views.permission_denied, kwargs={'exception': Exception('Permission Denied')}),
        path('error/404/', default_views.page_not_found, kwargs={'exception': Exception('Page not Found')}),
        path('error/500/', default_views.server_error),
    ])

    if 'debug_toolbar' in settings.INSTALLED_APPS:
        import debug_toolbar

        urlpatterns.append(
            path('__debug__/', include(debug_toolbar.urls))
        )
