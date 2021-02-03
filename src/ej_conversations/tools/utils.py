from requests import get
from .constants import BASE_URL_NPM

def get_npm_tag(url=BASE_URL_NPM):
    version = get(url)
    return version

def npm_version(get=get_npm_tag()):
    if get.status_code == 200:
        return get.json()
    else:
        return {"latest": "request failed"}