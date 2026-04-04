from django.utils import timezone


def years_from(date, now=None):
    now = now or timezone.now()
    years = now.year - date.year
    if date.month > now.month or (
        date.month == now.month and date.day > now.day
    ):
        return years - 1
    return years
