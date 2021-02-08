import os
from jinja2 import Environment, FileSystemLoader

from ej_boards.models import Board
from ej_conversations.models import Conversation


"""
 A class to generate an html template from conversations-detail page.
 This template serves for example to create marketing campaigns using
 mailchimp or mautic.
"""


class TemplateGenerator():

    def __init__(self, conversation, request, template_type='mautic'):
        self.PALETTE_CSS_GENERATORS = {
            'green': BaseCssGenerator('green'),
            'grey': BaseCssGenerator('grey'),
            'brand': BaseCssGenerator('brand'),
            'orange': BaseCssGenerator('orange'),
            'purple': BaseCssGenerator('purple'),
            'accent': BaseCssGenerator('accent'),
            'campaign': CampaignCssGenerator()
        }
        self.template_type = template_type
        self.conversation = conversation
        self.comment = conversation.approved_comments.last()
        self.request = request
        self.vote_domain = self._get_vote_domain()
        self.statics_domain = self._get_statics_domain()

    def get_template(self):
        try:
            return self._render_jinja_template()
        except:
            raise

    def _get_palette_css(self):
        try:
            palette = self.conversation.boards.first().palette.lower()
            generator = self.PALETTE_CSS_GENERATORS[palette]
        except:
            generator = self.PALETTE_CSS_GENERATORS["brand"]
        return generator.css()

    def _render_jinja_template(self):
        root = os.path.dirname(os.path.abspath(__file__))
        templates_dir = os.path.join(root, '../integrations')
        env = Environment(loader=FileSystemLoader(templates_dir))
        template = env.get_template('{}_template.jinja2'.format(self.template_type))
        return template.render(
            conversation_title=self.conversation.text,
            comment_content=self.comment.content,
            comment_author=self.comment.author.name,
            vote_url=self._get_voting_url(),
            statics_domain=self.statics_domain,
            tags=self.conversation.tags.all(),
            palette_css=self._get_palette_css()
        )

    def _get_voting_url(self):
        conversation_slug = self.conversation.slug
        conversation_id = self.conversation.id
        comment_id = self.comment.id
        if self.vote_domain == self.statics_domain:
            try:
                board_slug = self.conversation.boards.first().slug
                url = '{}/{}/conversations/{}/{}?comment_id={}&action=vote&origin=campaign'
                return url.format(self.vote_domain, board_slug, conversation_id, conversation_slug, comment_id)
            except:
                url = '{}/conversations/{}/{}?comment_id={}&action=vote&origin=campaign'
                return url.format(self.vote_domain, conversation_id, conversation_slug, comment_id)
        else:
            url = '{}/?cid={}&comment_id={}'
            return url.format(self.vote_domain, conversation_id, comment_id)

    def _get_vote_domain(self):
        if self.request.POST.get('custom-domain'):
            return self.request.POST.get('custom-domain')
        return self._get_statics_domain()

    def _get_statics_domain(self):
        scheme = self.request.META['wsgi.url_scheme']
        host = self.request.META['HTTP_HOST']
        return '{}://{}'.format(scheme, host)


class BaseCssGenerator():

    def __init__(self, palette='brand'):
        self.INLINE_PALETTES = {
            'green': ['#36C273', '#B4FDD4'],
            'grey': ['#666666', '#EEEEEE'],
            'brand': ['#30BFD3', '#C4F2F4'],
            'orange': ['#F5700A', '#FFE1CA'],
            'purple': ['#7758B3', '#E7DBFF'],
            'accent': ['#C6027B', '#FFE3EA'],
        }
        self.palette = palette

    def css(self):
        colors = self.INLINE_PALETTES[self.palette]
        palette_style = {}
        palette_style['light'] = 'color: {}; background-color: {};'.format(colors[0], colors[1])
        palette_style['dark'] = 'color: {} !important; background-color: {};'.format(colors[1], colors[0])
        palette_style['arrow'] = 'border-top: 28px solid {} !important;'.format(colors[1])
        palette_style['light-h1'] = ''
        palette_style['dark-h1'] = ''
        return palette_style


class CampaignCssGenerator():

    def __init__(self, palette='campaign'):
        self.INLINE_PALETTES = {'campaign': ['#1c9dd9', '#332f82']}
        self.palette = palette

    def css(self):
        colors = self.INLINE_PALETTES[self.palette]
        palette_style = {}
        palette_style['light'] = 'color: {}; background-color: {};'.format(colors[0], colors[1])
        palette_style['dark'] = 'color: {} !important; background-color: {};'.format(colors[1], colors[0])
        palette_style['arrow'] = 'border-top: 28px solid {} !important;'.format(colors[1])
        border_style = ' border-radius: unset;'
        palette_style['light-h1'] = 'color: #ffffff !important;'
        palette_style['dark-h1'] = 'color: #1c9dd9 !important;'
        palette_style['dark'] += border_style
        palette_style['light'] += border_style
        return palette_style
