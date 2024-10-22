from boogie.configurations import Conf, env


def get_instance(x):
    return x


class EjOptions(Conf):
    """
    Options for EJ installation.
    """

    # Conversations and boards limits
    EJ_MAX_COMMENTS_PER_CONVERSATION = env(2, name="{attr}")
    EJ_MAX_CONVERSATIONS_PER_BOARD = env(None, type=int, name="{attr}")
    EJ_ENABLE_BOARDS = env(True, name="{attr}")

    # Disable parts of the system
    EJ_ENABLE_PROFILES = env(True, name="{attr}")
    EJ_ENABLE_CLUSTERS = env(True, name="{attr}")
    EJ_ENABLE_DATAVIZ = env(True, name="{attr}")

    # TODO: remove those in the future? Maybe all personalization strings
    # should be options in Django constance with a cache fallback
    # Personalization
    EJ_ANONYMOUS_HOME_PATH = env("/start/", name="{attr}")
    EJ_USER_HOME_PATH = env("/conversations/", name="{attr}")

    # Allow instances to exclude some profile fields from visualization
    EJ_PROFILE_EXCLUDE_FIELDS = env([], name="{attr}")

    # Messages
    EJ_PAGE_TITLE = env(get_instance("EJ Platform"), name="{attr}")
    EJ_REGISTER_TEXT = get_instance("Not part of EJ yet?")
    EJ_LOGIN_TITLE_TEXT = get_instance("Welcome!")
