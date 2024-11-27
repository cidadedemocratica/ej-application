import os
from jinja2 import Environment, FileSystemLoader

from .utils import get_host_with_schema


"""
 A class to generate an html template from conversations-detail page.
 This template serves for example to create marketing campaigns using
 mailchimp or mautic.
"""


class TemplateGenerator:
    def __init__(self, conversation, request, form_data):
        self.PALETTE_CSS_GENERATORS = {
            "green": BaseCssGenerator("green"),
            "grey": BaseCssGenerator("grey"),
            "brand": BaseCssGenerator("brand"),
            "orange": BaseCssGenerator("orange"),
            "purple": BaseCssGenerator("purple"),
            "accent": BaseCssGenerator("accent"),
            "osf": BaseCssGenerator("osf"),
            "votorantim": BaseCssGenerator("votorantim"),
            "icd": BaseCssGenerator("icd"),
            "bocadelobo": BaseCssGenerator("bocadelobo"),
            "campaign": CampaignCssGenerator(),
        }
        self.template_type = form_data.get("template_type") or "mautic"
        self.conversation = conversation
        self.comment = conversation.approved_comments.last()
        self.request = request
        self.vote_domain = self._get_vote_domain()
        self.theme = form_data.get("theme")
        self.form_data = form_data
        self.set_custom_values()

    def set_custom_values(self):
        self.conversation.text = (
            self.form_data.get("custom_title") or self.conversation.text
        )
        self.comment = self.form_data.get("custom_comment") or self.comment

    def get_template(self):
        try:
            return self._render_jinja_template()
        except Exception:
            raise

    def _get_palette_css(self):
        try:
            generator = self.PALETTE_CSS_GENERATORS[self.theme]
        except Exception:
            generator = self.PALETTE_CSS_GENERATORS["brand"]
        return generator.css()

    def _render_jinja_template(self):
        root = os.path.dirname(os.path.abspath(__file__))
        templates_dir = os.path.join(root, "./jinja2/ej_integrations")
        env = Environment(loader=FileSystemLoader(templates_dir))
        host = get_host_with_schema(self.request)
        template = env.get_template("mailing_template.jinja2".format(self.template_type))
        return template.render(
            conversation_title=self.conversation.text,
            comment_content=self.comment.content,
            comment_author=self.comment.author.name,
            vote_url=self._get_voting_url(),
            statics_domain=get_host_with_schema(self.request),
            tags=self.conversation.tags.all(),
            palette_css=self._get_palette_css(),
            conversation_n_comments=self.conversation.n_comments,
            votes_conversation=self.conversation.n_votes,
            host=host,
        )

    def _get_voting_url(self):
        conversation_slug = self.conversation.slug
        conversation_id = self.conversation.id
        comment_id = self.comment.id
        statics_domain = get_host_with_schema(self.request)
        email_tag = MarketingTool.generate_email_tag(self.template_type)

        if self.vote_domain == statics_domain:
            try:
                board_slug = self.conversation.board.slug
                url = "{}/{}/conversations/{}/{}?comment_id={}&action=vote&origin=campaign{}"
                return url.format(
                    self.vote_domain,
                    board_slug,
                    conversation_id,
                    conversation_slug,
                    comment_id,
                    email_tag,
                )
            except Exception:
                url = "{}/conversations/{}/{}?comment_id={}&action=vote&origin=campaign{}"
                return url.format(
                    self.vote_domain,
                    conversation_id,
                    conversation_slug,
                    comment_id,
                    email_tag,
                )
        else:
            url = "{}/?cid={}&comment_id={}&action=vote&origin=campaign{}"
            return url.format(self.vote_domain, conversation_id, comment_id, email_tag)

    def _get_vote_domain(self):
        if self.request.POST.get("custom-domain"):
            return self.request.POST.get("custom-domain")
        return get_host_with_schema(self.request)


class MarketingTool:
    # Manage email marketing tags
    def generate_email_tag(template_type):
        if template_type == "mailchimp":
            return "&email=*|EMAIL|*"
        elif template_type == "mautic":
            return "&email=|EMAIL|"
        raise ValueError("Template type invalid")


class BaseCssGenerator:
    def __init__(self, palette="brand"):
        self.INLINE_PALETTES = {
            "green": ["#36C273", "#B4FDD4"],
            "grey": ["#666666", "#EEEEEE"],
            "brand": ["#30BFD3", "#C4F2F4"],
            "orange": ["#F5700A", "#FFE1CA"],
            "purple": ["#7758B3", "#E7DBFF"],
            "accent": ["#C6027B", "#FFE3EA"],
            "osf": ["#1D1088", "#F8127E"],
            "votorantim": ["#04082D", "#F14236"],
            "icd": ["#005BAA", "#F5821F"],
            "bocadelobo": ["#83E760", "#161616"],
        }
        self.palette = palette

    def css(self):
        colors = self.INLINE_PALETTES[self.palette]
        palette_style = {}
        palette_style["light"] = "color: {}; background-color: {};".format(
            colors[0], colors[1]
        )
        palette_style["dark"] = "color: {} !important; background-color: {};".format(
            colors[1], colors[0]
        )
        palette_style["arrow"] = "border-top: 28px solid {} !important;".format(colors[1])
        palette_style["light-h1"] = ""
        palette_style["dark-h1"] = ""
        return palette_style


class CampaignCssGenerator:
    def __init__(self, palette="campaign"):
        self.INLINE_PALETTES = {"campaign": ["#1c9dd9", "#332f82"]}
        self.palette = palette

    def css(self):
        colors = self.INLINE_PALETTES[self.palette]
        palette_style = {}
        palette_style["light"] = "color: {}; background-color: {};".format(
            colors[0], colors[1]
        )
        palette_style["dark"] = "color: {} !important; background-color: {};".format(
            colors[1], colors[0]
        )
        palette_style["arrow"] = "border-top: 28px solid {} !important;".format(colors[1])
        border_style = " border-radius: unset;"
        palette_style["light-h1"] = "color: #ffffff !important;"
        palette_style["dark-h1"] = "color: #1c9dd9 !important;"
        palette_style["dark"] += border_style
        palette_style["light"] += border_style
        return palette_style
