from django.core.exceptions import ValidationError
from ej_conversations import create_conversation
from ej_conversations.enums import Choice, RejectionReason
from ej_conversations.models import Vote
from ej_conversations.mommy_recipes import ConversationRecipes
import pytest
from constance import config

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
