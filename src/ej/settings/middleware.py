from boogie.configurations import MiddlewareConf as Base


class MiddlewareConf(Base):
    def get_middleware(self):
        middleware = super().get_middleware()
        middleware = [
            # 'corsheaders.middleware.CorsMiddleware',
            'django.contrib.flatpages.middleware.FlatpageFallbackMiddleware',
            'ej_boards.middleware.BoardFallbackMiddleware',
            'ej_conversations.middleware.ConversationFallbackMiddleware',
            *middleware
        ]
        if self.DEBUG:
            middleware = [
                'debug_toolbar.middleware.DebugToolbarMiddleware',
                *middleware
            ]
        if self.ENVIRONMENT == 'testing':
            middleware.remove('django.middleware.locale.LocaleMiddleware')
        if self.EJ_ROCKETCHAT_INTEGRATION:
            middleware.append('ej_rocketchat.middleware.ContentSecurityPolicyMiddleware')
        middleware.append('ej_campaigns.middleware.redirect_to_login_page')
        return middleware
