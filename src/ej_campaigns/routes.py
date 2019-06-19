from django.db import transaction
from django.http import HttpResponse, Http404
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.translation import ugettext_lazy as _
from jinja2 import Environment, FileSystemLoader
import os

from boogie.router import Router
from ej_boards.models import Board, BoardSubscription
from ej_conversations.models import Conversation
from .helper import *

app_name = 'ej_campaigns'
conversation_template_url = 'conversations/<model:conversation>/template/'
board_template_url = '<model:board>/{}'.format(conversation_template_url)

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

@urlpatterns.route(board_template_url, template=None)
def board_campaign_template(request, conversation, board):
    template = template_generator(request, conversation)
    response = HttpResponse(template, content_type="text/html")
    response['Content-Disposition'] = 'attachment; filename=template.html'
    return response

@urlpatterns.route(conversation_template_url, template=None)
def campaign_template(request, conversation):
    template = template_generator(request, conversation)
    response = HttpResponse(template, content_type="text/html")
    response['Content-Disposition'] = 'attachment; filename=template.html'
    return response
