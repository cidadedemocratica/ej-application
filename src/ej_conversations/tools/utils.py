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

def generate_props(form):
    if form.is_valid():
        result = ""
        if form.cleaned_data["theme"]:
            result = result + f"theme={form.cleaned_data['theme']} "
        if form.cleaned_data["authentication_type"]:
            result = result + f" authenticate-with={form.cleaned_data['authentication_type']}"
        return result
    return None