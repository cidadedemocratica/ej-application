from celery import shared_task
from .models import Clusterization

from ej.celery import app as celery_app

logger = celery_app.log.get_default_logger()


@shared_task
def update_clusterization(id: int):
    """
    Celery task that fetches a clusterization with the given id and executes
    its .update_clusterization() method asynchronously.

    This task is used to update opinion clusters without blocking the main
    application. It can be called from any part of the codebase using:
        from ej_clusters.tasks import update_clusterization
        update_clusterization.delay(clusterization_id)

    Or executed synchronously:
        update_clusterization(clusterization_id)
    """
    clusterization = Clusterization.objects.filter(id=id).first()
    if clusterization is not None:
        logger.info("Task: updating clusterization!")
        clusterization.update_clusterization()
