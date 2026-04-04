# -*- coding: utf-8 -*-
from __future__ import print_function

import os
from random import random, choice

from django.apps import apps
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from faker import Factory

User = get_user_model()
Profile = None
if apps.is_installed("ej_profiles"):
    from ej_profiles.models import Profile
    from ej_profiles.enums import Gender, Race


class Command(BaseCommand):
    help = "Export users data in a csv file"

    def add_arguments(self, parser):
        parser.add_argument(
            "--admin",
            action="store_true",
            dest="admin",
            help="Create an admin@admin.com user",
        )
        parser.add_argument(
            "--admin-password",
            action="store_true",
            dest="admin_password",
            help="Sets the admin password",
        )
        parser.add_argument(
            "--user",
            action="store_true",
            dest="user",
            help="Create an user@user.com user",
        )
        parser.add_argument(
            "--user-password",
            action="store_true",
            dest="user_password",
            help="Sets the user password",
        )
        parser.add_argument(
            "--staff", type=int, default=2, help="Number of staff members"
        )
        parser.add_argument(
            "--users", type=int, default=50, help="Number of regular users"
        )

    def handle(
        self,
        *files,
        admin=False,
        admin_password=None,
        user=True,
        user_password=None,
        staff=2,
        users=50,
        **options,
    ):
        users_created = 0
        fake = Factory.create("en-US")
        blocked_usernames = {
            "admin",
            *User.objects.values_list("email", flat=True),
        }
        usernames = set()
        while len(usernames) < staff + users:
            username = fake.user_name()
            if username not in blocked_usernames:
                usernames.add(username)

        # Create special users with known passwords
        if admin:
            users_created += create_admin(admin_password)
        if user:
            users_created += create_default_user(user_password)

        # Create staff users
        for _ in range(staff):
            username = usernames.pop()
            user = User.objects.create(
                name=fake.name(),
                email=username + "@" + fake.domain_name(),
                is_active=True,
                is_staff=True,
                is_superuser=False,
            )
            set_profile(user)
            users_created += 1

        # Create regular users
        for _ in range(users):
            username = usernames.pop()
            user = User.objects.create(
                name=fake.name(),
                email=username + "@" + fake.domain_name(),
                is_active=True,
                is_staff=False,
                is_superuser=False,
            )
            users_created += 1
            set_profile(user)

        # Feedback
        print(f"Created {users_created} fake users")


def create_admin(admin_password):
    if not User.objects.filter(email="admin@admin.com"):
        user = User.objects.create(
            name="Maurice Moss",
            email="admin@admin.com",
            is_active=True,
            is_staff=True,
            is_superuser=True,
        )
        user.set_password(
            admin_password or os.environ.get("ADMIN_PASSWORD", "admin")
        )
        user.save()
        set_profile(user)
        return 1
    else:
        print("Admin user was already created!")
        return 0


def create_default_user(user_password):
    if not User.objects.filter(email="user@user.com"):
        user = User.objects.create(
            name="Joe User",
            email="user@user.com",
            is_active=True,
            is_staff=False,
            is_superuser=False,
        )
        user.set_password(
            user_password or os.environ.get("USER_PASSWORD", "user")
        )
        user.save()
        set_profile(user)
        return 1
    else:
        print("Default user was already created!")
        return 0


def set_profile(user):
    if Profile is not None:
        kwargs = {}
        if random() < 0.5:
            kwargs["gender"] = choice(list(Gender))
        if random() < 0.5:
            kwargs["race"] = choice(list(Race))
        user.get_profile()
        Profile.objects.filter(user=user).update(**kwargs)
