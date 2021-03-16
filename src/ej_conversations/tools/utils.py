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
