from unittest.mock import Mock

from ej.settings.email import EmailConf


def test_get_email_backend_uses_mailgun_when_configured():
    config = Mock(
        ANYMAIL={
            "MAILGUN_API_KEY": "mailgun-api-key",
            "MAILGUN_SENDER_DOMAIN": "example.org",
        },
        EMAIL_HOST="smtp.example.org",
        EMAIL_PORT=587,
    )

    assert (
        EmailConf.get_email_backend(config)
        == "anymail.backends.mailgun.EmailBackend"
    )


def test_get_email_backend_uses_smtp_when_mailgun_is_not_configured():
    config = Mock(
        ANYMAIL={
            "MAILGUN_API_KEY": "",
            "MAILGUN_SENDER_DOMAIN": "",
        },
        EMAIL_HOST="smtp.example.org",
        EMAIL_PORT=587,
    )

    assert (
        EmailConf.get_email_backend(config)
        == "django.core.mail.backends.smtp.EmailBackend"
    )


def test_get_email_backend_uses_console_when_no_provider_is_configured():
    config = Mock(
        ANYMAIL={
            "MAILGUN_API_KEY": "",
            "MAILGUN_SENDER_DOMAIN": "",
        },
        EMAIL_HOST="",
        EMAIL_PORT="",
    )

    assert (
        EmailConf.get_email_backend(config)
        == "django.core.mail.backends.console.EmailBackend"
    )
