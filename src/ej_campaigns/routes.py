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

app_name = 'ej_campaigns'

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

def generate_template_with_jinja(request, conversation):
    scheme = request.META['wsgi.url_scheme']
    host = request.META['HTTP_HOST']
    site_url = '{}://{}'.format(scheme,host)
    root = os.path.dirname(os.path.abspath(__file__))
    templates_dir = os.path.join(root, 'templates')
    env = Environment(loader = FileSystemLoader(templates_dir))
    template = env.get_template('mautic.html')
    board_slug = BoardSubscription.objects.get(
        conversation=conversation.id
    ).board.slug
    data = template.render(
        board_slug=board_slug,
        conversation_slug=conversation.slug,
        conversation_title=conversation.title,
        comment_id=conversation.comments.all()[0].id,
        site_url=site_url
    )
    return data

@urlpatterns.route('<model:board>/conversations/<model:conversation>/template/', template=None)
def campaign_template(request, board, conversation):
    template = generate_template_with_jinja(request, conversation)
    response = HttpResponse(template, content_type="text/html")
    response['Content-Disposition'] = 'attachment; filename=mautic.html'
    return response

@urlpatterns.route('conversations/<model:conversation>/template/', template=None)
def campaign_template(request, conversation):
    template = generate_template_with_jinja(request, conversation)
    response = HttpResponse(template, content_type="text/html")
    response['Content-Disposition'] = 'attachment; filename=mautic.html'
    return response
