from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from . import models


def descr(msg):
    def decorator(f):
        setattr(f, "short_description", msg)
        return f

    return decorator


@admin.register(models.Profile)
class ProfileAdmin(admin.ModelAdmin):
    fieldsets = (
        (
            _("Basic information"),
            {
                "fields": [
                    "profile_photo",
                    "race",
                    "gender",
                    "birth_date",
                    "occupation",
                    "phone_number",
                ]
            },
        ),
        (_("Address"), {"fields": ["city", "state", "country"]}),
        (_("Advanced"), {"fields": ["political_activity", "biography"]}),
    )
    list_display = ("name", "email", "is_superuser")
    search_fields = ["user__name", "user__email"]
