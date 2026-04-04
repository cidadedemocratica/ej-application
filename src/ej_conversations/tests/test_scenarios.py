"""
Those scenarios are difficult to test using unit tests.

We describe simple scenarios with lots of asserts in the middle. This documents
user stories and can protect us from bad refactorings.
"""

import datetime
from contextlib import contextmanager
from types import SimpleNamespace

import mock
import pytest
from django.utils import timezone

from ej_conversations import rules
from ej_conversations.mommy_recipes import ConversationRecipes


class TestCommentLimitsAreEnforced(ConversationRecipes):
    """
    Application prevents user from posting too many comments in too little
    time.
    """

    @contextmanager
    def time_control(self):
        self.delay_secs = 0
        self.real_time = timezone.now

        def sleep(time):
            self.delay_secs += time

        with mock.patch.object(rules, "now", self.now):
            yield SimpleNamespace(sleep=sleep)

    def now(self):
        delta = datetime.timedelta(seconds=self.delay_secs)
        real = self.real_time()
        print("now", real, delta)
        return real + delta

    def test_comment_limits_are_enforced(self, mk_conversation, mk_user):
        with self.time_control():
            # We create a basic conversation and a user.
            conversation = mk_conversation()
            user = mk_user(email="test@domain.com")

            # User can post the first comment without problems.
            conversation.create_comment(user, "cmt1")

            # Ditto
            conversation.create_comment(user, "cmt2")
            assert user.comments.count() == 2

            # Now user cannot post because it has reached the global limit.
            with pytest.raises(PermissionError):
                conversation.create_comment(user, "cmt3-bad")

            # Never again...
            with pytest.raises(PermissionError):
                conversation.create_comment(user, "cmt3-bad-again")


class TestStatistics(ConversationRecipes):
    """
    We create a small, but plausible scenario of comments in a conversation
    and check if statistics are correct.
    """

    @pytest.mark.skip(reason="FIX THIS LATER")
    def test_conversation_statistics(self, mk_conversation, mk_user):
        conversation = mk_conversation()
        user = mk_user()

        # Three groups of people with different preferences
        g1 = [mk_user(email=f"user_a{i}@domain.com") for i in range(3)]
        g2 = [mk_user(email=f"user_b{i}@domain.com") for i in range(3)]
        g3 = [mk_user(email=f"user_c{i}@domain.com") for i in range(2)]

        # User makes some comments
        comments = [
            conversation.create_comment(
                user, f"comment {i}", status="approved", check_limits=False
            )
            for i in range(5)
        ]

        # Now we vote...
        votes = []
        for i, comment in enumerate(comments):
            for user in g1:
                votes.append(comment.vote(user, "agree"))
            for user in g2:
                votes.append(comment.vote(user, "disagree"))

            # Alternate between a pair who skip and miss to a pair who miss
            # and then skip ==> 5 skips and 5 misses in total
            for j, user in enumerate(g3):
                if (i + j) % 2 == 0:
                    votes.append(comment.vote(user, "skip"))

        # Now we check global statistics.
        stats = conversation.statistics()
        assert stats == {
            "comments": {
                "approved": 5,
                "pending": 0,
                "rejected": 0,
                "total": 5,
            },
            "votes": {"agree": 15, "disagree": 15, "skip": 5, "total": 35},
            "participants": {"commenters": 1, "voters": 8},
        }

        # User can also check its own stats
        assert conversation.statistics_for_user(g1[0]) == {
            "missing_votes": 0,
            "participation_ratio": 1.0,
            "votes": 5,
        }
        assert conversation.statistics_for_user(g1[2]) == {
            "missing_votes": 0,
            "participation_ratio": 1.0,
            "votes": 5,
        }
        assert conversation.statistics_for_user(g3[0]) == {
            "missing_votes": 2,
            "participation_ratio": 3 / 5,
            "votes": 3,
        }
        assert conversation.statistics_for_user(g3[1]) == {
            "missing_votes": 3,
            "participation_ratio": 2 / 5,
            "votes": 2,
        }
