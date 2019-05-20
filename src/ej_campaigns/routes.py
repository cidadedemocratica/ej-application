from django.db import transaction
from django.http import HttpResponse, Http404
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.translation import ugettext_lazy as _
from jinja2 import Environment, FileSystemLoader
import os

from boogie.router import Router
from ej_boards.models import Board
from ej_conversations.models import Conversation

app_name = 'ej_campaigns'

#
# Board management
#
urlpatterns = Router(
    template=['generic.jinja2'],
    object='',
    models={
        'board': Board,
        'conversation': Conversation,
    },
    lookup_field={'conversation': 'slug', 'board': 'slug'},
    lookup_type={'conversation': 'slug', 'board': 'slug'},
)


#
# Campaign URLs
#
@urlpatterns.route('<model:board>/conversations/<model:conversation>/template/', template=None)
def campaign_template(request, board, conversation):
    root = os.path.dirname(os.path.abspath(__file__))
    templates_dir = os.path.join(root, 'templates')
    env = Environment(loader = FileSystemLoader(templates_dir))
    template = env.get_template('mautic.html')
    data = template.render(
        conversation_title=conversation.title)
    response = HttpResponse(data, content_type="text/html")
    response['Content-Disposition'] = 'attachment; filename=mautic.html'
    return response
