from celery import shared_task
from .models import Clusterization

from ej.celery import app as celery_app

logger = celery_app.log.get_default_logger()


@shared_task
def update_clusterization(id: int):
    """
    Task that fetches a clusterization with the given id and executes it's
    .update_clusterization() method.
    """
    clusterization = Clusterization.objects.filter(id=id).first()
    if clusterization is not None:
        logger.info("Task: updating clusterization!")
        clusterization.update_clusterization()
