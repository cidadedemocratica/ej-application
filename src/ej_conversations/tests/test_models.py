from constance import config
from django.core.exceptions import ValidationError
import pytest

from ej_conversations import create_conversation
from ej_conversations.enums import Choice, RejectionReason
from ej_conversations.models import Vote
from ej_conversations.models.util import statistics, vote_count
from ej_conversations.models.vote import VoteChannels
from ej_conversations.mommy_recipes import ConversationRecipes

ConversationRecipes.update_globals(globals())


class TestConversation(ConversationRecipes):
    def test_random_comment_without_skiped(self, db, mk_conversation, mk_user):
        conversation = mk_conversation()
        user = mk_user(email="user@domain.com")
        other = mk_user(email="other@domain.com")
        mk_comment = conversation.create_comment
        comments = [
            mk_comment(user, "aa", status="approved", check_limits=False),
            mk_comment(user, "bb", status="approved", check_limits=False),
        ]
        comments[0].vote(other, "skip")
        comments[1].vote(other, "agree")

        config.RETURN_USER_SKIPED_COMMENTS = False
        cmt = conversation.next_comment(other)

        assert not other.is_anonymous
        assert cmt is None

    def test_random_comment_with_skiped(self, db, mk_conversation, mk_user):
        conversation = mk_conversation()
        user = mk_user(email="user@domain.com")
        other = mk_user(email="other@domain.com")
        mk_comment = conversation.create_comment
        comments = [
            mk_comment(user, "aa", status="approved", check_limits=False),
            mk_comment(user, "bb", status="approved", check_limits=False),
        ]
        comments[0].vote(other, "skip")
        comments[1].vote(other, "agree")
        cmt = conversation.next_comment(other)
        assert not other.is_anonymous
        assert cmt == comments[0]

    def test_random_comment_invariants(self, db, mk_conversation, mk_user):
        conversation = mk_conversation()
        user = mk_user(email="user@domain.com")
        other = mk_user(email="other@domain.com")
        mk_comment = conversation.create_comment
        comments = [
            mk_comment(other, "aa", status="approved", check_limits=False),
            mk_comment(user, "bb", status="approved", check_limits=False),
            mk_comment(other, "cc", status="pending", check_limits=False),
            mk_comment(
                other,
                "dd",
                status="rejected",
                check_limits=False,
                rejection_reason=RejectionReason.OFFENSIVE_LANGUAGE,
            ),
        ]

        cmt = conversation.next_comment(user)
        assert cmt == comments[1]
        assert cmt.status == cmt.STATUS.approved
        assert not Vote.objects.filter(author=user, comment=cmt)
        cmt.vote(user, Choice.AGREE)
        other_cmt = conversation.next_comment(user)
        assert other_cmt.author != user

    def test_create_conversation_saves_model_in_db(self, user_db):
        conversation = create_conversation("what?", "test", user_db)
        assert conversation.id is not None
        assert conversation.author == user_db

    def test_mark_conversation_favorite(self, mk_conversation, mk_user):
        user = mk_user()
        conversation = mk_conversation()
        conversation.make_favorite(user)
        assert conversation.is_favorite(user)

        conversation.toggle_favorite(user)
        assert not conversation.is_favorite(user)

        conversation.toggle_favorite(user)
        assert conversation.is_favorite(user)


class TestVote:
    def test_unique_vote_per_comment(self, mk_user, comment_db):
        user = mk_user()
        comment_db.vote(user, "agree")
        with pytest.raises(ValidationError):
            comment_db.vote(user, "disagree")

    def test_cannot_vote_in_non_moderated_comment(self, comment_db, user_db):
        comment_db.status = comment_db.STATUS.pending

        with pytest.raises(ValidationError):
            comment_db.vote(user_db, "agree")

    def test_create_agree_vote_happy_paths(self, comment_db, mk_user):
        vote1 = comment_db.vote(mk_user(email="user1@domain.com"), Choice.AGREE)
        assert comment_db.agree_count == 1
        assert comment_db.n_votes == 1
        vote2 = comment_db.vote(mk_user(email="user2@domain.com"), Choice.AGREE)
        assert comment_db.agree_count == 2
        assert comment_db.n_votes == 2
        assert vote1.choice == vote2.choice

    def test_create_vote_unhappy_paths(self, comment_db, user_db):
        with pytest.raises(ValueError):
            comment_db.vote(user_db, 42)

    def test_create_disagree_vote_happy_paths(self, comment_db, mk_user):
        vote1 = comment_db.vote(mk_user(email="user1@domain.com"), "disagree")
        assert comment_db.disagree_count == 1
        assert comment_db.n_votes == 1
        vote2 = comment_db.vote(mk_user(email="user2@domain.com"), Choice.DISAGREE)
        assert comment_db.disagree_count == 2
        assert comment_db.n_votes == 2
        assert vote1.choice == vote2.choice

    def test_create_skip_vote_happy_paths(self, comment_db, mk_user):
        vote1 = comment_db.vote(mk_user(email="user1@domain.com"), "skip")
        assert comment_db.skip_count == 1
        assert comment_db.n_votes == 1
        vote2 = comment_db.vote(mk_user(email="user2@domain.com"), Choice.SKIP)
        assert comment_db.skip_count == 2
        assert comment_db.n_votes == 2
        assert vote1.choice == vote2.choice

    def test_user_can_add_comment(self, mk_conversation, mk_user):
        conversation = mk_conversation()
        mk_comment = conversation.create_comment
        participant = mk_user(email="user1@domain.com")
        mk_comment(participant, "foo", status="approved", check_limits=False)
        n_comments = participant.comments.filter(conversation=conversation).count()
        assert conversation.user_can_add_comment(participant, n_comments)

        mk_comment(participant, "bla", status="approved", check_limits=False)
        n_comments = participant.comments.filter(conversation=conversation).count()
        assert not conversation.user_can_add_comment(participant, n_comments)

    def test_normalize_vote_using_labels(self):
        choice_agree = Choice.normalize("agree")
        choice_skip = Choice.normalize("skip")
        choice_disagree = Choice.normalize("disagree")
        assert choice_agree == Choice.AGREE
        assert choice_skip == Choice.SKIP
        assert choice_disagree == Choice.DISAGREE

        with pytest.raises(KeyError):
            Choice.normalize("xpto")

    def test_normalize_vote_using_numbers(self):
        choice_agree = Choice.normalize("1")
        choice_skip = Choice.normalize("0")
        choice_disagree = Choice.normalize("-1")
        assert choice_agree == Choice.AGREE
        assert choice_skip == Choice.SKIP
        assert choice_disagree == Choice.DISAGREE

        with pytest.raises(ValueError):
            Choice.normalize(42)

    def test_normalize_vote_using_choices(self):
        choice_agree = Choice.normalize(Choice.AGREE)
        choice_skip = Choice.normalize(Choice.SKIP)
        choice_disagree = Choice.normalize(Choice.DISAGREE)
        assert choice_agree == Choice.AGREE
        assert choice_skip == Choice.SKIP
        assert choice_disagree == Choice.DISAGREE


class TestComment(ConversationRecipes):
    def test_no_neighbours_comment(self, db, mk_conversation, mk_user):
        conversation = mk_conversation()
        user = mk_user(email="user@domain.com")
        mk_comment = conversation.create_comment
        comment = mk_comment(user, "aa", status="approved", check_limits=False)
        index = 0
        assert not comment.next(index, [{"comment": comment.id}])
        assert not comment.previous(index, [])

    def test_next_neighbour_comment(self, db, mk_conversation, mk_user):
        conversation = mk_conversation()
        user = mk_user(email="user@domain.com")
        mk_comment = conversation.create_comment
        comment = mk_comment(user, "aa", status="approved", check_limits=False)
        next_comment = mk_comment(
            user, "another content", status="approved", check_limits=False
        )
        comments = [{"comment": comment.id}, {"comment": next_comment.id}]
        index = 0
        assert comment.next(index, comments) == next_comment.id
        assert not comment.previous(index, comments)

    def test_previous_next_neighbour_comment(self, db, mk_conversation, mk_user):
        conversation = mk_conversation()
        user = mk_user(email="user@domain.com")
        mk_comment = conversation.create_comment
        comments = [
            mk_comment(user, "aa", status="approved", check_limits=False),
            mk_comment(user, "bb", status="approved", check_limits=False),
            mk_comment(user, "cc", status="approved", check_limits=False),
        ]
        comments_id = [{"comment": comment.id} for comment in comments]
        index = 1
        assert comments[index].next(index, comments_id) == comments[2].id
        assert comments[index].previous(index, comments_id) == comments[0].id

    def test_only_previous_neighbour_comment(self, db, mk_conversation, mk_user):
        conversation = mk_conversation()
        user = mk_user(email="user@domain.com")
        mk_comment = conversation.create_comment
        comments = [
            mk_comment(user, "aa", status="approved", check_limits=False),
            mk_comment(user, "bb", status="approved", check_limits=False),
            mk_comment(user, "cc", status="approved", check_limits=False),
        ]
        comments_id = [{"comment": comment.id} for comment in comments]
        index = 2
        assert not comments[index].next(index, comments_id)
        assert comments[index].previous(index, comments_id) == comments[1].id


class TestConversartionStatistics(ConversationRecipes):
    def test_vote_count_of_a_conversation(self, db, mk_conversation, mk_user):
        conversation = mk_conversation()
        vote_count_result = vote_count(conversation)
        assert vote_count_result == 0

        user = mk_user(email="user@domain.com")
        comment = conversation.create_comment(
            user, "aa", status="approved", check_limits=False
        )
        comment.vote(user, "agree")
        vote_count_result = vote_count(conversation)
        assert vote_count_result == 1

    def test_vote_count_agree(self, db, mk_conversation, mk_user):
        conversation = mk_conversation()
        user = mk_user(email="user@domain.com")
        vote_count_result = vote_count(conversation, Choice.AGREE)
        assert vote_count_result == 0

        comment = conversation.create_comment(
            user, "aa", status="approved", check_limits=False
        )
        comment.vote(user, "agree")
        vote_count_result = vote_count(conversation, Choice.AGREE)
        assert vote_count_result == 1

        other = mk_user(email="other@domain.com")
        comment = conversation.create_comment(
            user, "ab", status="approved", check_limits=False
        )
        comment.vote(other, "disagree")
        vote_count_result = vote_count(conversation, Choice.AGREE)
        assert vote_count_result == 1

    def test_vote_count_disagree(self, db, mk_conversation, mk_user):
        conversation = mk_conversation()
        user = mk_user(email="user@domain.com")
        vote_count_result = vote_count(conversation, Choice.DISAGREE)
        assert vote_count_result == 0

        comment = conversation.create_comment(
            user, "ac", status="approved", check_limits=False
        )
        comment.vote(user, "disagree")
        vote_count_result = vote_count(conversation, Choice.DISAGREE)
        assert vote_count_result == 1

    def test_vote_count_skip(self, db, mk_conversation, mk_user):
        conversation = mk_conversation()
        user = mk_user(email="user@domain.com")
        vote_count_result = vote_count(conversation, Choice.SKIP)
        assert vote_count_result == 0

        comment = conversation.create_comment(
            user, "ad", status="approved", check_limits=False
        )
        comment.vote(user, "skip")
        vote_count_result = vote_count(conversation, Choice.SKIP)
        assert vote_count_result == 1

    def test_statistics_return(self, db, mk_conversation):
        conversation = mk_conversation()
        statistics_result = statistics(conversation)

        assert "votes" in statistics_result
        assert "agree" in statistics_result["votes"]
        assert "disagree" in statistics_result["votes"]
        assert "skip" in statistics_result["votes"]
        assert "total" in statistics_result["votes"]

        assert "comments" in statistics_result
        assert "approved" in statistics_result["comments"]
        assert "rejected" in statistics_result["comments"]
        assert "pending" in statistics_result["comments"]
        assert "total" in statistics_result["comments"]

        assert "participants" in statistics_result
        assert "voters" in statistics_result["participants"]
        assert "commenters" in statistics_result["participants"]

        assert "channel_votes" in statistics_result
        assert "webchat" in statistics_result["channel_votes"]
        assert "telegram" in statistics_result["channel_votes"]
        assert "whatsapp" in statistics_result["channel_votes"]
        assert "opinion_component" in statistics_result["channel_votes"]
        assert "unknown" in statistics_result["channel_votes"]
        assert "ej" in statistics_result["channel_votes"]

        assert "channel_participants" in statistics_result
        assert "webchat" in statistics_result["channel_participants"]
        assert "telegram" in statistics_result["channel_participants"]
        assert "whatsapp" in statistics_result["channel_participants"]
        assert "opinion_component" in statistics_result["channel_participants"]
        assert "unknown" in statistics_result["channel_participants"]
        assert "ej" in statistics_result["channel_participants"]

        assert conversation._cached_statistics == statistics_result

    def test_statistics_for_channel_votes(self, db, mk_conversation, mk_user):
        conversation = mk_conversation()
        user1 = mk_user(email="user1@domain.com")
        user2 = mk_user(email="user2@domain.com")
        user3 = mk_user(email="user3@domain.com")
        comment = conversation.create_comment(
            user1, "ad", status="approved", check_limits=False
        )
        comment2 = conversation.create_comment(
            user1, "ad2", status="approved", check_limits=False
        )
        comment3 = conversation.create_comment(
            user2, "ad3", status="approved", check_limits=False
        )

        vote = comment.vote(user1, Choice.AGREE)
        vote.channel = VoteChannels.TELEGRAM
        vote.save()

        vote = comment.vote(user2, Choice.AGREE)
        vote.channel = VoteChannels.WHATSAPP
        vote.save()

        vote = comment.vote(user3, Choice.AGREE)
        vote.channel = VoteChannels.WHATSAPP
        vote.save()

        vote = comment2.vote(user1, Choice.AGREE)
        vote.channel = VoteChannels.OPINION_COMPONENT
        vote.save()

        vote = comment2.vote(user2, Choice.AGREE)
        vote.channel = VoteChannels.RASA_WEBCHAT
        vote.save()

        vote = comment2.vote(user3, Choice.AGREE)
        vote.channel = VoteChannels.UNKNOWN
        vote.save()

        vote = comment3.vote(user3, Choice.AGREE)
        vote.channel = VoteChannels.EJ
        vote.save()

        statistics = conversation.statistics()
        assert statistics["channel_votes"]["telegram"] == 1
        assert statistics["channel_votes"]["whatsapp"] == 2
        assert statistics["channel_votes"]["opinion_component"] == 1
        assert statistics["channel_votes"]["webchat"] == 1
        assert statistics["channel_votes"]["unknown"] == 1
        assert statistics["channel_votes"]["ej"] == 1

    def test_statistics_for_channel_participants(self, db, mk_conversation, mk_user):
        conversation = mk_conversation()
        user1 = mk_user(email="user1@domain.com")
        user2 = mk_user(email="user2@domain.com")
        user3 = mk_user(email="user3@domain.com")

        comment = conversation.create_comment(
            user1, "ad", status="approved", check_limits=False
        )
        comment2 = conversation.create_comment(
            user1, "ad2", status="approved", check_limits=False
        )
        comment3 = conversation.create_comment(
            user2, "ad3", status="approved", check_limits=False
        )

        # 3 participantes pelo telegram
        vote = comment.vote(user1, Choice.AGREE)
        vote.channel = VoteChannels.TELEGRAM
        vote.save()

        vote = comment.vote(user2, Choice.AGREE)
        vote.channel = VoteChannels.TELEGRAM
        vote.save()

        vote = comment.vote(user3, Choice.AGREE)
        vote.channel = VoteChannels.TELEGRAM
        vote.save()

        vote = comment2.vote(user1, Choice.AGREE)
        vote.channel = VoteChannels.TELEGRAM
        vote.save()

        vote = comment2.vote(user2, Choice.AGREE)
        vote.channel = VoteChannels.OPINION_COMPONENT
        vote.save()

        vote = comment2.vote(user3, Choice.AGREE)
        vote.channel = VoteChannels.UNKNOWN
        vote.save()

        vote = comment3.vote(user1, Choice.AGREE)
        vote.channel = VoteChannels.RASA_WEBCHAT
        vote.save()

        vote = comment3.vote(user2, Choice.AGREE)
        vote.channel = VoteChannels.WHATSAPP
        vote.save()

        vote = comment3.vote(user3, Choice.AGREE)
        vote.channel = VoteChannels.OPINION_COMPONENT
        vote.save()

        statistics = conversation.statistics()
        assert statistics["channel_participants"]["telegram"] == 3
        assert statistics["channel_participants"]["whatsapp"] == 1
        assert statistics["channel_participants"]["opinion_component"] == 2
        assert statistics["channel_participants"]["webchat"] == 1
        assert statistics["channel_participants"]["unknown"] == 1
