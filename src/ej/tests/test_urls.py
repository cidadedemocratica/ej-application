import logging


class TestBasicUrls:
    #
    # Generic URLs
    #

    # Urls visible to every one (even without login)
    public_urls = [
        # Basic login/profile related urls
        '/start/',
        '/login/',
        '/register/',
        '/profile/recover-password/',
        '/conversations/',
        '/rules/',
        '/about/',
        '/usage/',
        '/social/',
    ]

    # Urls that redirect to the login page for anonymous users
    login_redirect_urls = [
        # Profile
        '/profile/',
        '/profile/edit/',
        '/profile/comments/',
        '/profile/comments/approved/',
        '/profile/comments/pending/',
        '/profile/comments/rejected/',

        # Account management
        '/profile/reset-password/',
        '/profile/remove/',

        # Gamification
        '/profile/badges/',
        '/profile/leaderboard/',
        '/profile/quests/',
        '/profile/powers/',

        # Notifications
        '/profile/notifications/',
        '/profile/notifications/history/',
    ]

    #
    # Conversation based URLs
    #
    conversation_public_urls = [
        '/conversations/',
        '/conversations/{conversation}/',
        '/conversations/{conversation}/info/',
    ]

    conversation_private_urls = [
        '/conversations/{conversation}/comments/',
        '/conversations/{conversation}/my-comments/',
        '/conversations/{conversation}/comments/{comment}/',
        '/conversations/{conversation}/leaderboard/',
    ]

    #
    # Requires administrative access
    #
    admin_urls = [
        '/admin/',
        '/debug/styles/',
        '/debug/info/',
        '/debug/data/',
        '/debug/logs/',
    ]

    def test_visible_urls_for_anonymous_user(self, db, caplog, client):
        caplog.set_level(logging.CRITICAL, logger='django')
        check_urls(client, self.public_urls)

    def test_url_redirects(self, db, caplog, client):
        caplog.set_level(logging.CRITICAL, logger='django')
        check_urls(client, self.login_redirect_urls, 302)
        assert client.get('/').status_code == 302

    def test_login_required_urls(self, db, caplog, client, user_db):
        caplog.set_level(logging.CRITICAL, logger='django')
        client.force_login(user_db, backend=None)
        check_urls(client, [*self.public_urls, *self.login_redirect_urls])


def check_urls(client, urls, code=200):
    for url in urls:
        try:
            response = client.get(url)
        except Exception as ex:
            print('Error loading url: %s' % url)
            raise RuntimeError(f'{ex.__class__.__name__}: {ex}')
        assert response.status_code == code, f'url: {url}'
