from pytest import raises
from ej_campaigns.routes import campaign_template, board_campaign_template
from ej_campaigns.helper import vote_url, template_conversation_palette, inline_palettes
from ej_boards.models import Board
from ej_conversations import create_conversation

class TestCampaignHelper:

    def test_generate_vote_url(self, rf, conversation, comment, user):
        comment_1 = conversation.create_comment(user, 'comment 1', 'approved')
        comment_2 = conversation.create_comment(user, 'comment 2', 'approved')
        request = rf.get('', {'type': 'mautic'})
        request.META['HTTP_HOST'] = 'ejplatform.local'
        _vote_url = vote_url(request, conversation)
        campaign_comment = conversation.comments.all()[0]
        expected_url = 'http://ejplatform.local/conversations/{}?'\
                       'comment_id={}&action=vote&origin=mail'\
                       .format(conversation.slug, campaign_comment.id)
        assert _vote_url == expected_url

    def test_generate_vote_url_with_board(self, board, conversation, user, rf):
        board.add_conversation(conversation)
        comment_1 = conversation.create_comment(user, 'comment 1', 'approved')
        comment_2 = conversation.create_comment(user, 'comment 2', 'approved')
        request = rf.get('', {'type': 'mautic'})
        request.META['HTTP_HOST'] = 'ejplatform.local'
        _vote_url = vote_url(request, conversation)
        campaign_comment = conversation.comments.all()[0]
        expected_url = 'http://ejplatform.local/{}/conversations/{}?'\
            'comment_id={}&action=vote&origin=mail'.format(board.slug,
                                                           conversation.slug,
                                                           campaign_comment.id)
        assert _vote_url == expected_url

    def test_apply_board_pallete_on_mail_template(self, board, conversation):
        board.add_conversation(conversation)
        orange = inline_palettes['orange']
        arrow = 'border-top: 28px solid {} !important'.format(orange[1])
        dark = 'color: {} !important; background-color: {};'.format(orange[1], orange[0])
        light = 'color: {}; background-color: {};'.format(orange[0], orange[1])
        expected_palette = {
            'arrow': arrow,
            'dark': dark,
            'light': light
        }
        palette = template_conversation_palette(conversation)
        assert palette == expected_palette

    def test_apply_default_pallete_on_mail_template(self, board, conversation):
        blue = inline_palettes['blue']
        arrow = 'border-top: 28px solid {} !important'.format(blue[1])
        dark = 'color: {} !important; background-color: {};'.format(blue[1], blue[0])
        light = 'color: {}; background-color: {};'.format(blue[0], blue[1])
        expected_palette = {
            'arrow': arrow,
            'dark': dark,
            'light': light
        }
        palette = template_conversation_palette(conversation)
        assert palette == expected_palette
