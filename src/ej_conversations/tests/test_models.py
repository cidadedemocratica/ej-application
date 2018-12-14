import pytest
from django.core.exceptions import ValidationError

from ej_conversations import create_conversation
from ej_conversations.models import Vote, Choice
from ej_conversations.mommy_recipes import ConversationRecipes
from ej_users.models import User
from ej_boards.models import Board, BoardSubscription

ConversationRecipes.update_globals(globals())


class TestConversation(ConversationRecipes):
    def test_random_comment_invariants(self, db, mk_conversation, mk_user):
        conversation = mk_conversation()
        user = mk_user(email='user@domain.com')
        other = mk_user(email='other@domain.com')
        mk_comment = conversation.create_comment
        comments = [
            mk_comment(other, 'aa', status='approved', check_limits=False),
            mk_comment(user, 'bb', status='approved', check_limits=False),
            mk_comment(other, 'cc', status='pending', check_limits=False),
            mk_comment(other, 'dd', status='rejected', check_limits=False),
        ]

        cmt = conversation.next_comment(user)
        assert cmt == comments[1]
        assert cmt.status == cmt.STATUS.approved
        assert not Vote.objects.filter(author=user, comment=cmt)
        cmt.vote(user, Choice.AGREE)
        other_cmt = conversation.next_comment(user)
        assert other_cmt.author != user

    def test_create_conversation_saves_model_in_db(self, user_db):
        conversation = create_conversation('what?', 'test', user_db)
        assert conversation.id is not None
        assert conversation.author == user_db

    def test_can_get_conversations_by_board_url(self, api, db):
        user = User.objects.create_user('name@server.com', '123')
        user.board_name = 'name'
        user.save()
        board_url = '/' + user.board_name + '/'
        api.get(board_url, raw=True).status_code == 200

    def test_mark_conversation_favorite(self, mk_conversation, mk_user):
        user = mk_user()
        conversation = mk_conversation()
        conversation.make_favorite(user)
        assert conversation.is_favorite(user)

        conversation.toggle_favorite(user)
        assert not conversation.is_favorite(user)

        conversation.toggle_favorite(user)
        assert conversation.is_favorite(user)

    def test_get_board_palette_from_conversation(self, mk_conversation, mk_user):
        user = mk_user(email='someuser@mail.com')
        conversation = create_conversation("foo", "conv1", user)
        Board(slug="board1",
              owner=user,
              palette='Orange',
              description="board").save()
        board_subscription = BoardSubscription(conversation=conversation,
                                               board=Board.objects.last()).save()
        assert conversation.css_palette == 'orangePalette'
        assert conversation.css_light_palette == 'orangePalette-light'
        assert conversation.css_text_palette == 'orangePalette-text'

    def test_get_board_default_palette_from_conversation(self, mk_conversation, mk_user):
        user = mk_user(email='someuser@mail.com')
        conversation = create_conversation("foo", "conv1", user)
        Board(slug="board1",
              owner=user,
              description="board").save()
        board_subscription = BoardSubscription(conversation=conversation,
                                               board=Board.objects.last()).save()
        assert conversation.css_palette == 'bluePalette'



class TestVote:
    def test_unique_vote_per_comment(self, mk_user, comment_db):
        user = mk_user()
        comment_db.vote(user, 'agree')
        with pytest.raises(ValidationError):
            comment_db.vote(user, 'disagree')

    def test_cannot_vote_in_non_moderated_comment(self, comment_db, user_db):
        comment_db.status = comment_db.STATUS.pending

        with pytest.raises(ValidationError):
            comment_db.vote(user_db, 'agree')

    def test_create_agree_vote_happy_paths(self, comment_db, mk_user):
        vote1 = comment_db.vote(mk_user(email='user1@domain.com'), 'agree')
        assert comment_db.agree_count == 1
        assert comment_db.total_votes == 1
        vote2 = comment_db.vote(mk_user(email='user2@domain.com'), Choice.AGREE)
        assert comment_db.agree_count == 2
        assert comment_db.total_votes == 2
        assert vote1.choice == vote2.choice

    def test_create_vote_unhappy_paths(self, comment_db, user_db):
        with pytest.raises(ValueError):
            comment_db.vote(user_db, 42)

    def test_create_disagree_vote_happy_paths(self, comment_db, mk_user):
        vote1 = comment_db.vote(mk_user(email='user1@domain.com'), 'disagree')
        assert comment_db.disagree_count == 1
        assert comment_db.total_votes == 1
        vote2 = comment_db.vote(mk_user(email='user2@domain.com'), Choice.DISAGREE)
        assert comment_db.disagree_count == 2
        assert comment_db.total_votes == 2
        assert vote1.choice == vote2.choice

    def test_create_skip_vote_happy_paths(self, comment_db, mk_user):
        vote1 = comment_db.vote(mk_user(email='user1@domain.com'), 'skip')
        assert comment_db.skip_count == 1
        assert comment_db.total_votes == 1
        vote2 = comment_db.vote(mk_user(email='user2@domain.com'), Choice.SKIP)
        assert comment_db.skip_count == 2
        assert comment_db.total_votes == 2
        assert vote1.choice == vote2.choice
