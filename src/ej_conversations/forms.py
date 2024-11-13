from datetime import date, datetime

from django import forms
from django.core.exceptions import ValidationError
from django.template.loader import get_template
from django.utils.translation import gettext_lazy as _

from ej.forms import EjModelForm
from .models import Comment, Conversation


class CommentForm(EjModelForm):
    class Meta:
        model = Comment
        fields = ["content"]
        help_texts = {"content": None}

    def __init__(self, *args, conversation, **kwargs):
        self.conversation = conversation
        super().__init__(*args, **kwargs)

        self.fields["content"].widget.attrs["placeholder"] = _("Give your opinion here")
        self.fields["content"].widget.attrs["title"] = _("Suggest a new comment")

    def clean_content(self):
        super().clean()
        content = (self.cleaned_data.get("content") or "").strip()
        if content:
            comment_exists = Comment.objects.filter(
                content=content, conversation=self.conversation
            ).exists()
            if comment_exists:
                msg = _("You already submitted this comment.")
                raise ValidationError(msg, code="duplicated")

        return content


class ConversationDateWidget(forms.DateInput):
    template_name = "ej_conversations/includes/form-date.jinja2"
    renderer = get_template(template_name)

    def render(self, name, value, attrs=None, renderer=None):
        if isinstance(value, date):
            value = value.strftime("%Y-%m-%d")

        if name == "start_date" and value is None:
            today = datetime.today()
            value = today.strftime("%Y-%m-%d")

        context = self.get_context(name, value, attrs)
        return self.renderer.render(context)


class CustomImageInputWidget(forms.ClearableFileInput):
    template_name = "ej_conversations/includes/image-input.jinja2"
    renderer = get_template(template_name)

    def render(self, name, value, attrs=None, renderer=None):
        context = self.get_context(name, value, attrs)
        context["widget"]["value"] = value
        if value:
            context["is_valid_image"] = hasattr(value, "url")
        return self.renderer.render(context)


class ConversationForm(forms.ModelForm):
    """
    Form used to create and edit conversations.
    """

    comments_count = forms.IntegerField(initial=3, required=False)
    tags = forms.CharField(
        label=_("Tags"), help_text=_("Tags, separated by commas."), required=False
    )
    background_image = forms.ImageField(
        widget=CustomImageInputWidget(
            attrs={"id": "background_input", "title": _("Background image")}
        ),
        required=False,
        label=_("Background image"),
    )
    logo_image = forms.ImageField(
        widget=CustomImageInputWidget(attrs={"id": "logo_input", "title": _("Logo")}),
        required=False,
        label=_("Logo"),
    )

    class Meta:
        model = Conversation
        fields = [
            "title",
            "text",
            "anonymous_votes_enabled",
            "anonymous_votes",
            "send_profile_question",
            "votes_to_send_profile_question",
            "start_date",
            "end_date",
            "welcome_message",
            "background_image",
            "logo_image",
            "ending_message",
            "participants_can_add_comments",
        ]
        widgets = {
            "start_date": ConversationDateWidget,
            "end_date": ConversationDateWidget,
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in ("tags", "text"):
            self.set_placeholder(field, self[field].help_text)
        if self.instance and self.instance.id is not None:
            self.fields["tags"].initial = ", ".join(
                self.instance.tags.values_list("name", flat=True)
            )

    def clean_title(self, *args, **kwargs):
        title = self.cleaned_data["title"]
        edited = title != self.instance.title
        if not edited:
            return title
        if Conversation.objects.filter(title=title).exists():
            raise ValidationError(_("This title already exists!"), code="duplicate")
        return title

    def set_placeholder(self, field, value):
        self.fields[field].widget.attrs["placeholder"] = value

    def save(self, commit=True, board=None, **kwargs):
        if not board:
            raise ValidationError("Board field should not be empty")
        conversation = super().save(commit=False)
        conversation.board = board

        for k, v in kwargs.items():
            setattr(conversation, k, v)

        if commit:
            conversation.save()
            conversation.set_overdue()

            # Save tags on the database
            tags = self.cleaned_data["tags"]
            if not (tags.isspace() or tags == ""):
                tags = tags.split(",")
                conversation.tags.set(tags, clear=True)

        return conversation

    def save_comments(
        self, author, check_limits=True, status=Comment.STATUS.approved, **kwargs
    ):
        """
        Save model, tags and comments.
        """
        conversation = self.save(author=author, **kwargs)

        # Create comments
        kwargs = {"status": status, "check_limits": check_limits}
        n = int(self.data["comments_count"])
        for i in range(n):
            name = f"comment-{i + 1}"
            value = self.data.get(name)
            if value:
                try:
                    conversation.create_comment(author, value, **kwargs)
                # Duplicate or empty comment...
                except ValidationError:
                    pass
        return conversation
