from django.core.management.base import BaseCommand

from ej_profiles import enums, models

GENDER_CHOICES = [int(x) for x in enums.Gender]
RACE_CHOICES = [int(x) for x in enums.Race]


class Command(BaseCommand):
    help = "Update profile entries and make sure that invalid profile items are reset to default values"

    def log(self, *args, **kwargs):
        print(*args, **kwargs)

    def handle(self, *args, **options):
        for profile in models.Profile.objects.values(
            "id", "gender", "race", "state", "user__email"
        ):
            fix_profile(profile, self.log)


def fix_profile(profile, log=lambda *args, **kwargs: None, fix=True):
    profile_id = profile["id"]
    email = profile["user__email"]
    state = profile["state"]
    gender = profile["gender"]
    race = profile["race"]

    # Check state
    if state != "" and state not in enums.STATE_CHOICES_MAP:
        log(f"Invalid state for user {email}: {state}")
        log("The state field will be set to blank")
        if fix:
            models.Profile.objects.filter(id=profile_id).update(state="")

    # Check race
    if race and race not in RACE_CHOICES:
        log(f"Invalid race for user {email}: {race}")
        log("The race field will be set to blank")
        if fix:
            models.Profile.objects.filter(id=profile_id).update(race=0)

    # Check gender
    if gender and gender not in GENDER_CHOICES:
        log(f"Invalid gender for user {email}: {gender}")
        log("The gender field will be set to blank")
        if fix:
            models.Profile.objects.filter(id=profile_id).update(gender=0)
