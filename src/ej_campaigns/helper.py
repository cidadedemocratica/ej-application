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

existent_templates = ['mautic', 'hotsite']

inlinePalettes = {
    'green': ['#36C273', '#B4FDD4'],
    'grey': ['#666666', '#EEEEEE'],
    'blue': ['#30BFD3', '#C4F2F4'],
    'orange': ['#F5700A', '#FFE1CA'],
    'purple': ['#7758B3', '#E7DBFF'],
    'pink': ['#C6027B', '#FFE3EA']
}

def paletteMixin(palette):
    colors = inlinePalettes[palette]
    templatePalette = {}
    templatePalette['light'] = 'color: {}; background-color: {};'.format(colors[0], colors[1])
    templatePalette['dark'] = 'color: {} !important; background-color: {};'.format(colors[1], colors[0])
    templatePalette['arrow'] = 'border-top: 28px solid {} !important'.format(colors[1])
    return templatePalette


def templatePalette(conversation):
    try:
        currentPalette = BoardSubscription.objects.get(
            conversation=conversation.id
        ).board.palette.lower()
    except:
        currentPalette = 'blue'
    paletteStyle = paletteMixin(currentPalette)
    return paletteStyle

def site_url(request):
    scheme = request.META['wsgi.url_scheme']
    host = request.META['HTTP_HOST']
    _site_url = '{}://{}'.format(scheme,host)
    return _site_url


def vote_url(request, conversation):
    board_slug = None
    _vote_url = None
    _site_url = site_url(request)
    conversation_slug=conversation.slug
    comment_id=conversation.comments.all()[0].id
    try:
        board_slug = BoardSubscription.objects.get(
            conversation=conversation.id
        ).board.slug
        _vote_url = '{}/{}/conversations/{}?comment_id={}&action=vote'.format(
            _site_url,
            board_slug,
            conversation_slug,
            comment_id
        )
    except:
        _vote_url = '{}/conversations/{}?comment_id={}&action=vote'.format(
            _site_url,
            conversation_slug,
            comment_id
        )
    return _vote_url

def generate_template_with_jinja(request, conversation, template_type):
    root = os.path.dirname(os.path.abspath(__file__))
    templates_dir = os.path.join(root, 'templates')
    env = Environment(loader = FileSystemLoader(templates_dir))
    template = env.get_template('{}.html'.format(template_type))
    data = template.render(
        conversation_title=conversation.text,
        comment_content=conversation.comments.all()[0].content,
        comment_author=conversation.comments.all()[0].author.name,
        vote_url=vote_url(request,conversation),
        site_url=site_url(request),
        tags=conversation.tags.all(),
        paletteStyle=templatePalette(conversation)
    )
    return data

def template_generator(request, conversation):
    template_type = request.GET.get('type')
    if (template_type and template_type in existent_templates):
        template = generate_template_with_jinja(
            request, conversation, template_type
        )
    else:
        template = generate_template_with_jinja(
            request, conversation, 'mautic'
        )
    return template
