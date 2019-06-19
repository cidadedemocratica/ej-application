from pytest import raises
from ej_campaigns.routes import campaign_template, board_campaign_template
from ej_campaigns.helper import vote_url
from ej_boards.models import Board
from ej_conversations import create_conversation

class TestRoutes:

    def test_generate_mautic_template(self, rf, conversation, comment):
        request = rf.get('', {'type': 'mautic'})
        request.META['HTTP_HOST'] = 'ejplatform.local'
        response = campaign_template(request, conversation)
        assert response['Content-Disposition'] == 'attachment; filename=template.html'

    def test_generate_mautic_template_with_macros(self, rf, conversation, comment):
        request = rf.get('', {'type': 'mautic'})
        request.META['HTTP_HOST'] = 'ejplatform.local'
        response = campaign_template(request, conversation)
        assert str(response.content).find(conversation.title)
        assert str(response.content).find(comment.author.name)
