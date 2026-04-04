import os
from .fixes import apply_all
from .celery import app as celery_app

__all__ = ("celery_app",)

if os.environ.get("EXPERIMENTAL_ACCELERATE", "false").lower() == "true":
    from ej.fixes.startup_accelerator import accelerate

    accelerate()


# Apply fixes
apply_all()
