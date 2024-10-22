from django.contrib.auth import get_user_model

from boogie.testing.pytest import CrawlerTester, UrlTester

from ej_clusters.mommy_recipes import ClusterRecipes
from ej_conversations.mommy_recipes import ConversationRecipes
from ej_profiles.mommy_recipes import ProfileRecipes
from ej_users.mommy_recipes import UserRecipes

User = get_user_model()

conversation_url = "/board-slug/conversations/1/conversation/"


class DataMixin(
    ClusterRecipes,
    ConversationRecipes,
    ProfileRecipes,
    UserRecipes,
):
    def make_user(self, username, **kwargs):
        return User.objects.create_user(name=username, **kwargs)


class Base(DataMixin, CrawlerTester):
    """
    Base crawler for a anonymous user.
    """

    start = "/"
    must_visit = start


class TestUserCrawl(Base):
    """
    Crawl on all urls accessible by a user without any privileges.
    """

    user = "user"
    must_visit = (*Base.must_visit, "/profile/")


class TestAuthorCrawl(TestUserCrawl):
    """
    Crawl on all urls accessible by the author of a resource.
    """

    user = "author"
    conversation_actions = []

    must_visit = (
        *TestUserCrawl.must_visit,
        *[conversation_url + x for x in conversation_actions],
    )


class TestAdminCrawl(TestAuthorCrawl):
    """
    Crawl on all urls accessible by the admin user resource.
    """

    user = "author"
    must_visit = (*TestAuthorCrawl.must_visit,)


class TestUrls(UrlTester, DataMixin):
    urls = {
        None: Base.must_visit,
        "user": TestUserCrawl.must_visit,
        "author": TestAuthorCrawl.must_visit,
        "admin": TestAdminCrawl.must_visit,
    }
