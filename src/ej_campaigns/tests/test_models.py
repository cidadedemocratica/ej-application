from pytest import raises
from ej_campaigns.routes import campaign_template, board_campaign_template
from ej_campaigns.models import Campaign
from ej_boards.models import Board
from ej_conversations import create_conversation

class TestModels:

    def test_generate_vote_url(self, rf, conversation, comment, user):
        comment_1 = conversation.create_comment(user, 'comment 1', 'approved')
        comment_2 = conversation.create_comment(user, 'comment 2', 'approved')
        host_url = 'http://ejplatform.local'
        campaign = Campaign(conversation, host_url, 'mautic')
        vote_url = campaign.url_to_compute_vote()
        campaign_comment = conversation.comments.all()[0]
        expected_url = 'http://ejplatform.local/conversations/{}?'\
                       'comment_id={}&action=vote&origin=mail'\
                       .format(conversation.slug, campaign_comment.id)
        assert vote_url == expected_url

    def test_generate_vote_url_with_board(self, board, conversation, user, rf):
        board.add_conversation(conversation)
        comment_1 = conversation.create_comment(user, 'comment 1', 'approved')
        comment_2 = conversation.create_comment(user, 'comment 2', 'approved')
        host_url = 'http://ejplatform.local'
        campaign = Campaign(conversation, host_url, 'mautic')
        vote_url = campaign.url_to_compute_vote()
        campaign_comment = conversation.comments.all()[0]
        expected_url = 'http://ejplatform.local/{}/conversations/{}?'\
            'comment_id={}&action=vote&origin=mail'.format(board.slug,
                                                           conversation.slug,
                                                           campaign_comment.id)
        assert vote_url == expected_url

    def test_apply_board_pallete_on_mail_template(self, board, conversation):
        board.add_conversation(conversation)
        arrow = 'border-top: 28px solid {} !important;'.format('#FFE1CA')
        dark = 'color: {} !important; background-color: {};'.format('#FFE1CA', '#F5700A')
        light = 'color: {}; background-color: {};'.format('#F5700A', '#FFE1CA')
        expected_palette = {
            'arrow': arrow,
            'dark': dark,
            'light': light,
            'light-h1':'',
            'dark-h1': ''
        }
        host_url = 'http://ejplatform.local'
        campaign = Campaign(conversation, host_url, 'mautic')
        palette = campaign.palette_css('orange')
        assert palette == expected_palette

    def test_apply_campaign_pallete_on_mail_template(self, board, conversation):
        board.add_conversation(conversation)
        arrow = 'border-top: 28px solid {} !important;'.format('#332f82')
        dark = 'color: {} !important; background-color: {}; border-radius: unset;'.format('#332f82', '#1c9dd9')
        light = 'color: {}; background-color: {}; border-radius: unset;'.format('#1c9dd9', '#332f82')
        expected_palette = {
            'arrow': arrow,
            'dark': dark,
            'light': light,
            'light-h1':'color: #ffffff !important;',
            'dark-h1': 'color: #1c9dd9 !important;'
        }
        host_url = 'http://ejplatform.local'
        campaign = Campaign(conversation, host_url, 'mautic')
        palette = campaign.palette_css('campaign')
        assert palette == expected_palette


    def test_apply_default_pallete_on_mail_template(self, board, conversation):
        arrow = 'border-top: 28px solid {} !important;'.format('#C4F2F4')
        dark = 'color: {} !important; background-color: {};'.format('#C4F2F4', '#30BFD3')
        light = 'color: {}; background-color: {};'.format('#30BFD3', '#C4F2F4')
        expected_palette = {
            'arrow': arrow,
            'dark': dark,
            'light': light,
            'light-h1':'',
            'dark-h1': ''
        }
        host_url = 'http://ejplatform.local'
        campaign = Campaign(conversation, host_url, 'mautic')
        palette = campaign.palette_css()
        assert palette == expected_palette
