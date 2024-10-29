from requests import get
from .constants import BASE_URL_NPM


def get_npm_tag(url=BASE_URL_NPM):
    version = get(url)
    return version


def npm_version():
    response = get_npm_tag()
    if response.status_code == 200:
        return response.json()
    else:
        return {"latest": "request failed"}


def user_can_add_new_domain(user, conversation):
    return user.is_staff or user.is_superuser or conversation.author.id == user.id


def get_host_with_schema(request):
    scheme = request.META.get("HTTP_X_FORWARDED_PROTO") or "http"
    host = request.META.get("HTTP_HOST") or "localhost:8000"
    return "{}://{}".format(scheme, host)
