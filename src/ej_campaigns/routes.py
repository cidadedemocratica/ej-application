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

def vote_url(request, conversation):
    scheme = request.META['wsgi.url_scheme']
    host = request.META['HTTP_HOST']
    site_url = '{}://{}'.format(scheme,host)
    board_slug = None
    try:
        board_slug = BoardSubscription.objects.get(
            conversation=conversation.id
        ).board.slug
    except:
        pass
    conversation_slug=conversation.slug
    comment_id=conversation.comments.all()[0].id
    if board_slug:
        _vote_url = '{}/{}/conversations/{}?comment_id={}&action=vote'.format(
            site_url,
            board_slug,
            conversation_slug,
            comment_id
        )
    else:
        _vote_url = '{}/conversations/{}?comment_id={}&action=vote'.format(
            site_url,
            conversation_slug,
            comment_id
        )
    return _vote_url

def generate_template_with_jinja(request, conversation):
    root = os.path.dirname(os.path.abspath(__file__))
    templates_dir = os.path.join(root, 'templates')
    env = Environment(loader = FileSystemLoader(templates_dir))
    template = env.get_template('mautic.html')
    data = template.render(
        conversation_title=conversation.text,
        comment_content=conversation.comments.all()[0].content,
        comment_author=conversation.comments.all()[0].author,
        vote_url=vote_url(request,conversation)
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
