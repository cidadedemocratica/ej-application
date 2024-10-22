"""
A few functions for creating plausible synthetic data.
"""

from functools import wraps
from random import choice, random

from django.contrib.auth import get_user_model
from django.db.models import Model
from faker import Factory

from ... import create_conversation
from ...models import Comment

fake = Factory.create()
User = get_user_model()


def bulk_create(func):
    @wraps(func)
    def method(self, *args, commit=True, **kwargs):
        result = func(self, *args, **kwargs)
        if commit and result:
            model = type(result[0])
            model.objects.bulk_create(result)
            ids = model.objects.order_by("-id").values_list("id", flat=True)[
                : len(result)
            ]
            for id_, item in zip(ids, reversed(result)):
                item.id = id_
        return result

    return method


class ExampleData:
    def __init__(self, users, verbose):
        self.users = list(users)
        self.staff_users = [x for x in self.users if x.is_staff]
        self.verbose = verbose
        if verbose:
            self.log = lambda x: "Created: %s" % x
        else:
            self.log = lambda x: None

    def __setattr__(self, key, value):
        if isinstance(value, Model):
            self.log(value)
        super().__setattr__(key, value)

    def _comment_factory(self, conversation, **kwargs):
        create = conversation.create_comment
        return lambda comment, status="approved": create(
            self.get_user(), comment, check_limits=False, status=status, **kwargs
        )

    def get_staff_user(self):
        return choice(self.staff_users)

    def new(self, question, title):
        return create_conversation(
            question, title, self.get_staff_user, is_promoted=True, commit=False
        )

    @bulk_create
    def make_conversations(self):
        return [
            self.new(
                "We want to create the best programming language. How should it be?",
                "A better programming language",
            ),
            self.new(
                "How can we improve the schools and education in our community?",
                "School system",
            ),
            self.new(
                "How can we make our democracy more participative?",
                "Participative democracy",
            ),
        ]

    @bulk_create
    def make_language_comments(self, conversation):
        new = self._comment_factory(conversation, commit=False)
        return [
            new("It must be functional to control side-effects."),
            new("I want a purely OO language."),
            new("We have Python! We don't need a new language!"),
            new("It has to run on the browser."),
            new("It must be really fast."),
            new("I want a statically typed language."),
            new("It must be dynamic, but accept type hints.", status="pending"),
        ]

    @bulk_create
    def make_school_comments(self, conversation):
        new = self._comment_factory(conversation, commit=False)
        return [
            new("Students should have a say on what they want to learn."),
            new("We need more arts and crafts lessons."),
            new("We have to encourage the use technology and teach programming."),
            new("Our curriculum should be open and focused on real problems."),
            new(
                "We don't need no education! We don't need no thought control!",
                status="pending",
            ),
        ]

    @bulk_create
    def make_democracy_comments(self, conversation, extra=50):
        new = self._comment_factory(conversation, commit=False)
        return [
            new("People should have direct power to decide community affairs."),
            new("We need to forbid corporations from financing elections."),
            new("We need better voting systems.", status="pending"),
            *map(new, (fake.paragraph() for _ in range(extra))),
        ]

    @bulk_create
    def make_votes(self):
        comments = list(Comment.approved.all())
        probs = [(x, (random(), random(), random() / 3)) for x in comments]
        votes = []
        for comment, probs in probs:
            for user in self.users:
                vote = self.random_vote(comment, user, probs)
                if vote:
                    votes.append(vote)
        return votes

    def random_vote(self, comment, user, probs):
        p_vote, p_skip, p_ok = probs
        if random() < p_vote:
            try:
                if random() < p_skip:
                    return comment.vote(user, "skip", commit=False)
                elif random() < p_ok:
                    return comment.vote(user, "agree", commit=False)
                else:
                    return comment.vote(user, "disagree", commit=False)
            except Exception:
                print(f"could not vote on comment {comment.content}")

    def make_all(self):
        language, school, democracy = self.make_conversations()
        self.make_language_comments(language)
        self.make_school_comments(school)
        self.make_democracy_comments(democracy)
        self.make_votes()

    def get_user(self):
        return choice(self.users)


def make_examples(users=None, verbose=False):
    """
    Takes a list of users and creates plausible synthetic data.
    """
    if users is None:
        users = User.objects.all()

    data = ExampleData(users, verbose)
    data.make_all()
