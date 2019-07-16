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

def palette_css(palette):
    colors = inline_palettes[palette]
    palette_style = {}
    palette_style['light'] = 'color: {}; background-color: {};'.format(colors[0], colors[1])
    palette_style['dark'] = 'color: {} !important; background-color: {};'.format(colors[1], colors[0])
    palette_style['arrow'] = 'border-top: 28px solid {} !important'.format(colors[1])
    palette_style['light-h1'] = ''
    palette_style['dark-h1'] = ''
    if palette == 'campaign':
        border_style = ' border-radius: unset;'
        light_h1_style = 'color: #ffffff !important;'
        dark_h1_style = 'color: #1c9dd9 !important;'
        palette_style['light-h1'] += light_h1_style
        palette_style['dark'] += border_style
        palette_style['light'] += border_style
        palette_style['dark-h1'] += dark_h1_style
    return palette_style

def palette_from_conversation(conversation):
    try:
        conversation_palette = BoardSubscription.objects.get(
            conversation=conversation.id
        ).board.palette.lower()
    except:
        conversation_palette = 'blue'
    return palette_css(conversation_palette)

def site_url(request):
    scheme = request.META['wsgi.url_scheme']
    host = request.META['HTTP_HOST']
    _site_url = '{}://{}'.format(scheme,host)
    return _site_url

def url_to_compute_vote(request, conversation):
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

def render_jinja_template(request, conversation, template_type):
    root = os.path.dirname(os.path.abspath(__file__))
    templates_dir = os.path.join(root, 'templates')
    env = Environment(loader = FileSystemLoader(templates_dir))
    template = env.get_template('{}.html'.format(template_type))
    data = template.render(
        conversation_title=conversation.text,
        comment_content=conversation.comments.all()[0].content,
        comment_author=conversation.comments.all()[0].author.name,
        vote_url=url_to_compute_vote(request,conversation),
        site_url=site_url(request),
        tags=conversation.tags.all(),
        palette_css=palette_from_conversation(conversation)
    )
    return data

def build_template(request, conversation):
    template_type = request.GET.get('type')
    if (use_default_template(template_type)):
        return render_jinja_template(request, conversation, 'mautic')
    return render_jinja_template(request, conversation, template_type)

def use_default_template(template_type):
    return not template_type and not (template_type in existent_templates)
