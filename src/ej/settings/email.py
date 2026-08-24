import environ

from boogie.configurations import Conf

env = environ.Env(
    DEFAULT_FROM_EMAIL=(str, "cd@cidadedemocratica.org.br"),
    DEFAULT_FROM_NAME=(str, "Empurrando Juntas"),
    MAILGUN_API_KEY=(str, ""),
    MAILGUN_SENDER_DOMAIN=(str, ""),
    EMAIL_HOST=(str, ""),
    EMAIL_PORT=(int, ""),
    EMAIL_HOST_USER=(str, ""),
    EMAIL_HOST_PASSWORD=(str, ""),
    EMAIL_USE_TLS=(bool, True),
)


class EmailConf(Conf):

    DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL")
    DEFAULT_FROM_NAME = env("DEFAULT_FROM_NAME")
    ANYMAIL = {
        "MAILGUN_API_KEY": env("MAILGUN_API_KEY"),
        "MAILGUN_SENDER_DOMAIN": env("MAILGUN_SENDER_DOMAIN"),
    }
    EMAIL_HOST = env("EMAIL_HOST")
    EMAIL_PORT = env("EMAIL_PORT")
    EMAIL_HOST_USER = env("EMAIL_HOST_USER")
    EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD")
    EMAIL_USE_TLS = env("EMAIL_USE_TLS")

    def get_email_backend(self):
        if (
            self.ANYMAIL["MAILGUN_API_KEY"]
            and self.ANYMAIL["MAILGUN_SENDER_DOMAIN"]
        ):
            return "anymail.backends.mailgun.EmailBackend"

        if self.EMAIL_HOST and self.EMAIL_PORT:
            return "django.core.mail.backends.smtp.EmailBackend"

        return "django.core.mail.backends.console.EmailBackend"
