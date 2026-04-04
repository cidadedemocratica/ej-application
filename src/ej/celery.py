import os
from celery import Celery
import environ

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "ej.settings")
env = environ.Env()
app = Celery(
    "ej",
    broker=f"amqp://{env('RABBITMQ_DEFAULT_USER')}:{env('RABBITMQ_DEFAULT_PASS')}@rabbitmq",
)
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()
