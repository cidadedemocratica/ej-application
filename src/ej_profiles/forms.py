from django import forms
from django.conf import settings

from ej.forms import EjModelForm
from . import models
from .enums import STATE_CHOICES


FULL_EDITABLE_FIELDS = [
    "occupation",
    "education",
    "gender",
    "race",
    "ethnicity",
    "birth_date",
    "city",
    "state",
    "country",
    "phone_number",
    "political_activity",
    "biography",
    "profile_photo",
]
EXCLUDE_EDITABLE_FIELDS = settings.EJ_PROFILE_EXCLUDE_FIELDS
EDITABLE_FIELDS = [
    f for f in FULL_EDITABLE_FIELDS if f not in EXCLUDE_EDITABLE_FIELDS
]


class UsernameForm(EjModelForm):
    class Meta:
        model = models.User
        fields = ["name"]
        help_texts = {"name": ""}


class ProfileFormProfilePhoto(forms.ModelForm):
    class Meta:
        model = models.Profile
        fields = [
            "profile_photo",
        ]


class ProfileForm(EjModelForm):
    """
    User profile form
    """

    class Meta:
        model = models.Profile
        fields = [
            field
            for field in EDITABLE_FIELDS
            if field not in EXCLUDE_EDITABLE_FIELDS
        ]
        widgets = {
            # DateInput seems to not convert data in the database to a proper
            # value. Dates already saved on the database are removed because
            # they show as blanks
            # "birth_date": DateInput(attrs={"type": "date"}, format="D d M Y"),
            # "profile_photo": ej.forms.FileInput(attrs={"accept": "image/*"})
            "state": forms.Select(choices=STATE_CHOICES),
            "birth_date": forms.DateInput(
                attrs={
                    "placeholder": "DD/MM/YYYY",
                    "pattern": "\d{2}/\d{2}/\d{4}",
                }
            ),
        }

    def __init__(self, *args, instance, **kwargs):
        super().__init__(*args, instance=instance, **kwargs)
        self.user_form = UsernameForm(*args, instance=instance.user, **kwargs)
        self.fields = {**self.user_form.fields, **self.fields}
        self.initial.update(self.user_form.initial)

        # Override field names
        name_overrides = getattr(settings, "EJ_PROFILE_FIELD_NAMES", {})
        for name, value in name_overrides.items():
            self[name].label = value

    def save(self, commit=True, **kwargs):
        result = super().save(commit=commit, **kwargs)
        self.user_form.instance = result.user
        self.user_form.save(commit=commit)
        return result
