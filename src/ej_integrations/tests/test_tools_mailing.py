import mock
from pytest import raises
from ej_conversations.mommy_recipes import ConversationRecipes
from ej_integrations.mailing import TemplateGenerator, MarketingTool
from ej_integrations.forms import MailingToolForm


class TestTemplateGenerator(ConversationRecipes):
    def setup_method(self, method):
        self.REQUEST_META = {
            "HTTP_X_FORWARDED_PROTO": "http",
            "HTTP_HOST": "ejplatform.local",
        }
        self.REQUEST_POST = {"custom-domain": "http://ejplatform.local"}

    def test_generate_vote_url_with_mautic(self, mk_user, conversation_db):
        request = mock.Mock()
        request.META = self.REQUEST_META
        request.POST = self.REQUEST_POST
        user = mk_user(email="test@domain.com")
        comment_1 = conversation_db.create_comment(
            user, "comment 1", status="approved", check_limits=False
        )
        form_data = {"template_type": "mautic"}
        email_tag = MarketingTool.generate_email_tag(form_data["template_type"])
        generator = TemplateGenerator(conversation_db, request, form_data)
        vote_url = generator._get_voting_url()
        expected_url = (
            "http://ejplatform.local/{}/conversations/{}/{}"
            "?comment_id={}&action=vote&origin=campaign{}".format(
                conversation_db.board.slug,
                conversation_db.id,
                conversation_db.slug,
                comment_1.id,
                email_tag,
            )
        )

        assert vote_url == expected_url

    def test_generate_vote_url_with_mailchimp(self, mk_user, conversation_db):
        request = mock.Mock()
        request.META = self.REQUEST_META
        request.POST = self.REQUEST_POST
        user = mk_user(email="test@domain.com")
        comment_1 = conversation_db.create_comment(
            user, "comment 1", status="approved", check_limits=False
        )
        form_data = {"template_type": "mailchimp"}
        email_tag = MarketingTool.generate_email_tag(form_data["template_type"])
        generator = TemplateGenerator(conversation_db, request, form_data)
        vote_url = generator._get_voting_url()
        expected_url = (
            "http://ejplatform.local/{}/conversations/{}/{}"
            "?comment_id={}&action=vote&origin=campaign{}".format(
                conversation_db.board.slug,
                conversation_db.id,
                conversation_db.slug,
                comment_1.id,
                email_tag,
            )
        )

        assert vote_url == expected_url

    def test_generate_vote_url_with_invalid_template(self):
        with raises(ValueError):
            MarketingTool.generate_email_tag("invalid")

    def test_generate_vote_url_with_board_using_mailchimp(
        self, mk_board, mk_conversation, mk_user
    ):
        request = mock.Mock()
        request.META = self.REQUEST_META
        request.POST = self.REQUEST_POST
        board = mk_board()
        user = mk_user(email="test@domain.com")
        conversation = mk_conversation(author=user)
        comment_1 = conversation.create_comment(user, "comment 1", "approved")
        board.add_conversation(conversation)
        form_data = {"template_type": "mautic"}
        email_tag = MarketingTool.generate_email_tag(form_data["template_type"])
        generator = TemplateGenerator(conversation, request, form_data)
        vote_url = generator._get_voting_url()

        expected_url = (
            "http://ejplatform.local/{}/conversations/{}/{}"
            "?comment_id={}&action=vote&origin=campaign{}".format(
                board.slug, conversation.id, conversation.slug, comment_1.id, email_tag
            )
        )

        assert vote_url == expected_url

    def test_apply_default_palette_on_mail_template(
        self, mk_conversation, mk_board, mk_user
    ):
        request = mock.Mock()
        request.META = self.REQUEST_META
        conversation = mk_conversation()
        user = mk_user(email="test2@domain.com")
        conversation.create_comment(user, "comment 1", "approved")
        form_data = {"template_type": "mautic"}
        generator = TemplateGenerator(conversation, request, form_data)

        arrow = "border-top: 28px solid {} !important;".format("#C4F2F4")
        dark = "color: {} !important; background-color: {};".format("#C4F2F4", "#30BFD3")
        light = "color: {}; background-color: {};".format("#30BFD3", "#C4F2F4")
        expected_palette = {
            "arrow": arrow,
            "dark": dark,
            "light": light,
            "light-h1": "",
            "dark-h1": "",
        }

        palette = generator._get_palette_css()
        assert palette == expected_palette

    def test_apply_mautic_in_case_template_type_is_not_specified(
        self, mk_conversation, mk_board, mk_user
    ):
        request = mock.Mock()
        request.META = self.REQUEST_META
        conversation = mk_conversation()
        form_data1 = {"template_type": ""}
        generator1 = TemplateGenerator(conversation, request, form_data1)

        form_data2 = {}
        generator2 = TemplateGenerator(conversation, request, form_data2)

        assert generator1.template_type == "mautic"
        assert generator2.template_type == "mautic"

    def test_apply_board_palette_on_campaign_template_with_empty_template_type(
        self, mk_board, mk_conversation, mk_user
    ):
        request = mock.Mock()
        request.META = self.REQUEST_META
        conversation = mk_conversation()
        form_data1 = {"template_type": ""}
        generator1 = TemplateGenerator(conversation, request, form_data1)

        form_data2 = {}
        generator2 = TemplateGenerator(conversation, request, form_data2)

        assert generator1.template_type == "mautic"
        assert generator2.template_type == "mautic"

    def test_apply_board_palette_on_campaign_template_with_palette(
        self, mk_board, mk_conversation, mk_user
    ):
        request = mock.Mock()
        request.META = self.REQUEST_META
        board = mk_board(palette="orange")
        user = mk_user(email="test@domain.com")
        conversation = mk_conversation(author=user)
        conversation.create_comment(user, "comment 1", "approved")
        form_data = {"template_type": "mautic", "theme": board.palette}
        generator = TemplateGenerator(conversation, request, form_data)

        arrow = "border-top: 28px solid {} !important;".format("#FFE1CA")
        dark = "color: {} !important; background-color: {};".format("#FFE1CA", "#F5700A")
        light = "color: {}; background-color: {};".format("#F5700A", "#FFE1CA")
        expected_palette = {
            "arrow": arrow,
            "dark": dark,
            "light": light,
            "light-h1": "",
            "dark-h1": "",
        }

        palette = generator._get_palette_css()
        assert palette == expected_palette

    def test_apply_campaign_palette_on_mail_template(
        self, mk_board, mk_conversation, mk_user
    ):
        request = mock.Mock()
        request.META = self.REQUEST_META
        board = mk_board(palette="campaign")
        user = mk_user(email="test@domain.com")
        conversation = mk_conversation(author=user)
        conversation.create_comment(user, "comment 1", "approved")
        board.add_conversation(conversation)
        form_data = {"template_type": "mautic", "theme": "campaign"}
        campaign = TemplateGenerator(conversation, request, form_data)

        arrow = "border-top: 28px solid {} !important;".format("#332f82")
        dark = "color: {} !important; background-color: {}; border-radius: unset;".format(
            "#332f82", "#1c9dd9"
        )
        light = "color: {}; background-color: {}; border-radius: unset;".format(
            "#1c9dd9", "#332f82"
        )
        expected_palette = {
            "arrow": arrow,
            "dark": dark,
            "light": light,
            "light-h1": "color: #ffffff !important;",
            "dark-h1": "color: #1c9dd9 !important;",
        }

        palette = campaign._get_palette_css()
        assert palette == expected_palette

    def test_set_custom_comment_template(self, mk_user, conversation_db):
        request = mock.Mock()
        request.META = self.REQUEST_META
        request.POST = self.REQUEST_POST
        user = mk_user(email="test@domain.com")
        comment_1 = conversation_db.create_comment(
            user, "comment 1", status="approved", check_limits=False
        )
        form_data = {"template_type": "mautic", "custom_comment": comment_1}
        generator = TemplateGenerator(conversation_db, request, form_data)
        assert generator.comment.content == comment_1.content
        assert generator.comment == comment_1
        assert generator.conversation.text == conversation_db.text

    def test_set_custom_title_template(self, mk_user, conversation_db):
        request = mock.Mock()
        request.META = self.REQUEST_META
        request.POST = self.REQUEST_POST
        new_title = "Text of the new title"
        user = mk_user(email="test@domain.com")
        conversation_db.create_comment(
            user, "comment 1", status="approved", check_limits=False
        )
        form_data = {"template_type": "mautic", "custom_title": new_title}
        generator = TemplateGenerator(conversation_db, request, form_data)
        assert (
            generator.comment.content == conversation_db.approved_comments.last().content
        )
        assert generator.comment == conversation_db.approved_comments.last()
        assert generator.conversation.text == new_title


class TestMailingToolForm(ConversationRecipes):
    def test_valid_mautic_form_for_conversation_component(self, conversation_db, mk_user):
        user = mk_user(email="test@domain.com")
        conversation_db.create_comment(
            user, "comment 1", status="approved", check_limits=False
        )
        form = MailingToolForm(
            {
                "template_type": "mautic",
                "theme": "icd",
                "custom_title": None,
                "custom_comment": None,
            },
            conversation_id=conversation_db.id,
        )
        assert form.is_valid()

    def test_valid_mailchimp_form_for_conversation_component(
        self, conversation_db, mk_user
    ):
        user = mk_user(email="test@domain.com")
        conversation_db.create_comment(
            user, "comment 1", status="approved", check_limits=False
        )
        form = MailingToolForm(
            {
                "template_type": "mailchimp",
                "theme": "icd",
                "custom_title": None,
                "custom_comment": None,
            },
            conversation_id=conversation_db.id,
        )
        assert form.is_valid()

    def test_conversation_component_valid_custom_attributes(
        self, conversation_db, mk_user
    ):
        user = mk_user(email="test@domain.com")
        comment_1 = conversation_db.create_comment(
            user, "comment 1", status="approved", check_limits=False
        )
        form = MailingToolForm(
            {
                "template_type": "mailchimp",
                "theme": "icd",
                "custom_title": "New title",
                "custom_comment": comment_1.id,
            },
            conversation_id=conversation_db.id,
        )
        assert form.is_valid()
