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

inline_palettes = {
    'green': ['#36C273', '#B4FDD4'],
    'grey': ['#666666', '#EEEEEE'],
    'blue': ['#30BFD3', '#C4F2F4'],
    'orange': ['#F5700A', '#FFE1CA'],
    'purple': ['#7758B3', '#E7DBFF'],
    'pink': ['#C6027B', '#FFE3EA'],
    'campaign': ['#1c9dd9', '#332f82']
}

def palette_mixin(palette):
    colors = inline_palettes[palette]
    palette_style = {}
    palette_style['light'] = 'color: {}; background-color: {};'.format(colors[0], colors[1])
    palette_style['dark'] = 'color: {} !important; background-color: {};'.format(colors[1], colors[0])
    palette_style['arrow'] = 'border-top: 28px solid {} !important'.format(colors[1])
    return palette_style


def template_conversation_palette(conversation):
    try:
        current_palette = BoardSubscription.objects.get(
            conversation=conversation.id
        ).board.palette.lower()
    except:
        current_palette = 'blue'
    palette_style = palette_mixin(current_palette)
    return palette_style

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
        url = '{}/{}/conversations/{}?comment_id={}&action=vote&origin=mail'
        return url.format(_site_url, board_slug, conversation_slug, comment_id)
    except:
        url = '{}/conversations/{}?comment_id={}&action=vote&origin=mail'
        return url.format(_site_url, conversation_slug, comment_id)

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
        palette_style=template_conversation_palette(conversation)
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
