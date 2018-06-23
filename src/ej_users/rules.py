from django.conf import settings
from django.urls import resolve, Resolver404

from boogie import rules
from sidekick import import_later


USERNAMES_BLACKLIST = {
    # Common 'bad' usernames
    'me', '', 'user',

    # Additional usernames from settings
    *getattr(settings, 'FORBIDDEN_USERNAMES', ()),
}


@rules.register_rule('auth.valid_username')
def is_valid_username(username):
    if username in USERNAMES_BLACKLIST:
        return False
    try:
        resolve(f'/{username}/')
        return False
    except Resolver404:
        return True


@rules.register_value('auth.profile')
def profile(user):
    """
    Return a profile instance for user.
    """
    profile_class = rules.compute('auth.profile_class')
    try:
        return user.raw_profile
    except profile_class.DoesNotExist:
        return profile_class.objects.create(user=user)


@rules.register_value('auth.profile_class')
def profile_class():
    """
    Return a profile instance for user.
    """
    return import_later('ej_profiles.models:Profile')
