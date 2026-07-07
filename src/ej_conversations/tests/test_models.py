from constance import config
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.urls import reverse
import pytest

from ej_conversations import create_conversation
from ej_conversations.enums import Choice, RejectionReason
from ej_conversations.models import (
    ConversationManager,
    ConversationManagerInvitation,
    Vote,
)
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


class TestConversationManagerInvitation(ConversationRecipes):
    def accept_invitation(self, invitation):
        return invitation.accept()

    def test_normalizes_email_before_save(self, db, mk_conversation, mk_user):
        conversation = mk_conversation()
        invited_by = mk_user(email="inviter@domain.com")

        invitation = ConversationManagerInvitation.objects.create(
            conversation=conversation,
            email=" Manager@Example.COM ",
            invited_by=invited_by,
        )

        assert invitation.email == "manager@example.com"

    def test_prevents_duplicate_active_invitation_for_same_email(
        self, db, mk_conversation, mk_user
    ):
        conversation = mk_conversation()
        invited_by = mk_user(email="inviter@domain.com")
        ConversationManagerInvitation.objects.create(
            conversation=conversation,
            email="manager@example.com",
            invited_by=invited_by,
        )

        with pytest.raises(IntegrityError):
            ConversationManagerInvitation.objects.create(
                conversation=conversation,
                email="MANAGER@example.com",
                invited_by=invited_by,
            )

    def test_allows_inactive_duplicate_invitation(
        self, db, mk_conversation, mk_user
    ):
        conversation = mk_conversation()
        invited_by = mk_user(email="inviter@domain.com")
        ConversationManagerInvitation.objects.create(
            conversation=conversation,
            email="manager@example.com",
            invited_by=invited_by,
        )

        invitation = ConversationManagerInvitation.objects.create(
            conversation=conversation,
            email="manager@example.com",
            invited_by=invited_by,
            is_active=False,
        )

        assert invitation.id is not None

    def test_get_dashboard_url(self, db, mk_conversation, mk_user):
        conversation = mk_conversation()
        invited_by = mk_user(email="inviter@domain.com")
        invitation = ConversationManagerInvitation.objects.create(
            conversation=conversation,
            email="manager@example.com",
            invited_by=invited_by,
        )

        assert invitation.get_dashboard_url() == reverse(
            "boards:dataviz-dashboard",
            kwargs=conversation.get_url_kwargs(),
        )

    def test_accepted_invitation_grants_manager_edit_access(
        self, db, mk_conversation, mk_user
    ):
        conversation = mk_conversation()
        manager = mk_user(email="manager@example.com")
        invited_by = mk_user(email="inviter@domain.com")
        invitation = ConversationManagerInvitation.objects.create(
            conversation=conversation,
            email=manager.email,
            invited_by=invited_by,
        )
        self.accept_invitation(invitation)

        assert ConversationManager.objects.is_manager(conversation, manager)
        assert manager.has_perm("ej.is_conversation_manager", conversation)
        assert manager.has_perm("ej.can_edit_conversation", conversation)

    def test_accepted_invitation_grants_access_after_user_registers(
        self, db, mk_conversation, mk_user
    ):
        conversation = mk_conversation()
        invited_by = mk_user(email="inviter@domain.com")
        invitation = ConversationManagerInvitation.objects.create(
            conversation=conversation,
            email="manager@example.com",
            invited_by=invited_by,
        )
        manager = mk_user(email="manager@example.com")
        invitation.refresh_from_db()
        self.accept_invitation(invitation)

        assert manager.has_perm("ej.is_conversation_manager", conversation)
        assert manager.has_perm("ej.can_edit_conversation", conversation)

    def test_pending_invitation_does_not_create_manager_or_grant_access(
        self, db, mk_conversation, mk_user
    ):
        conversation = mk_conversation()
        manager = mk_user(email="manager@example.com")
        invited_by = mk_user(email="inviter@domain.com")
        ConversationManagerInvitation.objects.create(
            conversation=conversation,
            email=manager.email,
            invited_by=invited_by,
        )

        assert not ConversationManager.objects.is_manager(conversation, manager)
        assert not manager.has_perm("ej.is_conversation_manager", conversation)
        assert not manager.has_perm("ej.can_edit_conversation", conversation)

    def test_inactive_invitation_does_not_grant_manager_access(
        self, db, mk_conversation, mk_user
    ):
        conversation = mk_conversation()
        manager = mk_user(email="manager@example.com")
        invited_by = mk_user(email="inviter@domain.com")
        ConversationManagerInvitation.objects.create(
            conversation=conversation,
            email=manager.email,
            invited_by=invited_by,
            is_active=False,
        )

        assert not manager.has_perm("ej.is_conversation_manager", conversation)
        assert not manager.has_perm("ej.can_edit_conversation", conversation)

    def test_inactive_invitation_cannot_be_accepted(
        self, db, mk_conversation, mk_user
    ):
        conversation = mk_conversation()
        manager = mk_user(email="manager@example.com")
        invited_by = mk_user(email="inviter@domain.com")
        invitation = ConversationManagerInvitation.objects.create(
            conversation=conversation,
            email=manager.email,
            invited_by=invited_by,
            is_active=False,
        )

        with pytest.raises(ValidationError):
            invitation.accept(manager)

        invitation.refresh_from_db()
        assert not invitation.is_active
        assert invitation.status == ConversationManagerInvitation.Status.PENDING
        assert not ConversationManager.objects.is_manager(conversation, manager)

    def test_resaving_accepted_invitation_does_not_duplicate_managers(
        self, db, mk_conversation, mk_user
    ):
        conversation = mk_conversation()
        manager = mk_user(email="manager@example.com")
        invited_by = mk_user(email="inviter@domain.com")
        invitation = ConversationManagerInvitation.objects.create(
            conversation=conversation,
            email=manager.email,
            invited_by=invited_by,
        )

        self.accept_invitation(invitation)
        invitation.save()

        assert (
            ConversationManager.objects.filter(
                conversation=conversation,
                user=manager,
            ).count()
            == 1
        )

    def test_accepting_new_invitation_invalidates_previous_manager_invitation(
        self, db, mk_conversation, mk_user
    ):
        conversation = mk_conversation()
        manager = mk_user(email="manager@example.com")
        invited_by = mk_user(email="inviter@domain.com")
        previous_invitation = ConversationManagerInvitation.objects.create(
            conversation=conversation,
            email=manager.email,
            invited_by=invited_by,
        )
        self.accept_invitation(previous_invitation)
        new_invitation = ConversationManagerInvitation.objects.create(
            conversation=conversation,
            email="manager-alias@example.com",
            user=manager,
            invited_by=invited_by,
        )

        self.accept_invitation(new_invitation)
        previous_invitation.refresh_from_db()

        manager_membership = ConversationManager.objects.get(
            conversation=conversation,
            user=manager,
        )
        assert manager_membership.invitation == new_invitation
        assert not previous_invitation.is_active
        assert new_invitation.is_active

    def test_delete_manager_removes_manager_access(
        self, db, mk_conversation, mk_user
    ):
        conversation = mk_conversation()
        manager = mk_user(email="manager@example.com")
        invited_by = mk_user(email="inviter@domain.com")
        invitation = ConversationManagerInvitation.objects.create(
            conversation=conversation,
            email=manager.email,
            invited_by=invited_by,
        )
        self.accept_invitation(invitation)

        invitation.delete_manager()
        invitation.refresh_from_db()

        assert not invitation.is_active
        assert not ConversationManager.objects.is_manager(conversation, manager)
        assert not manager.has_perm("ej.is_conversation_manager", conversation)
        assert not manager.has_perm("ej.can_edit_conversation", conversation)

    def test_manager_invitation_does_not_grant_moderation_or_delete_access(
        self, db, mk_conversation, mk_user
    ):
        conversation = mk_conversation()
        manager = mk_user(email="manager@example.com")
        invited_by = mk_user(email="inviter@domain.com")
        invitation = ConversationManagerInvitation.objects.create(
            conversation=conversation,
            email=manager.email,
            invited_by=invited_by,
        )
        self.accept_invitation(invitation)

        assert manager.has_perm("ej.can_edit_conversation", conversation)
        assert manager.has_perm("ej.can_access_tools_page", conversation)
        assert not manager.has_perm(
            "ej.can_moderate_conversation", conversation
        )
        assert not manager.has_perm(
            "ej.can_manage_conversation_members", conversation
        )
        assert not manager.has_perm("ej.can_delete_conversation", conversation)


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
        vote2 = comment_db.vote(
            mk_user(email="user2@domain.com"), Choice.DISAGREE
        )
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
        n_comments = participant.comments.filter(
            conversation=conversation
        ).count()
        assert conversation.user_can_add_comment(participant, n_comments)

        mk_comment(participant, "bla", status="approved", check_limits=False)
        n_comments = participant.comments.filter(
            conversation=conversation
        ).count()
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

    def test_previous_next_neighbour_comment(
        self, db, mk_conversation, mk_user
    ):
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

    def test_only_previous_neighbour_comment(
        self, db, mk_conversation, mk_user
    ):
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

    def test_statistics_for_channel_participants(
        self, db, mk_conversation, mk_user
    ):
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
