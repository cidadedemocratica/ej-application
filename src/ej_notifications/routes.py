from django.utils.translation import ugettext_lazy as _

from boogie.router import Router

app_name = 'ej_notifications'
urlpatterns = Router(
    login=True,
    template=['ej_notifications/{name}.jinja2', 'generic.jinja2']
)


@urlpatterns.route()
def index(request):
    user = request.user
    return {
        'content_title': _('List of notifications'),
        'user': user,
        'notifications': ['hello', 'world'],
        # 'notifications': user.notifications.unseen(),
    }


@urlpatterns.route('history/')
def clusters(request):
    user = request.user
    return {
        'user': user,
        # 'notifications': user.notifications.seen(),
    }
