from django import forms
from django.utils.translation import gettext_lazy as _
from django.template.loader import get_template

from ej.forms import EjModelForm
from ej_clusters.enums import FORM_CHOICE_MAP
from ej_clusters.models.stereotype_vote import StereotypeVote
from ej_conversations.enums import Choice
from ej_conversations.models import Comment
from .models import Stereotype, Cluster


class StereotypeForm(EjModelForm):
    """
    Create and edit new stereotypes
    """

    class Meta:
        # We have to add the owner attribute to enable the unique owner + name
        # validation constraint. This is not ideal since we have to fake the
        # existence of this field using default values
        model = Stereotype
        fields = ["name", "description", "owner"]

    def __init__(self, *args, owner=None, instance=None, clusterization=None, **kwargs):
        self.owner_instance = owner = owner or instance.owner
        self.clusterization = clusterization
        kwargs["instance"] = instance
        kwargs["initial"] = {"owner": owner, **kwargs.get("initial", {})}
        super(StereotypeForm, self).__init__(*args, **kwargs)
        self.fields["description"].widget.attrs["placeholder"] = _(
            "Brief description if necessary"
        )
        self.fields["name"].widget.attrs["placeholder"] = _(
            "What are we going to call this participant profile?"
        )

    def _save_m2m(self):
        super()._save_m2m()
        has_groups = self.instance.clusters.count() > 0
        if not has_groups:
            group = Cluster.objects.create(
                name=self.cleaned_data["name"],
                description=self.cleaned_data["description"],
                clusterization=self.clusterization,
            )
            group.stereotypes.add(self.instance)

    def full_clean(self):
        self.data = self.data.copy()
        self.data["owner"] = str(self.owner_instance.id)
        return super().full_clean()

    def save(self, commit=True, **kwargs):
        stereotype = super().save(commit, **kwargs)

        if stereotype.id and commit:
            cluster = stereotype.clusters.first()
            if cluster:
                cluster.name = stereotype.name
                cluster.description = stereotype.description
                cluster.save()
        return stereotype


class SelectWidget(forms.Select):
    template_name = "ej_clusters/stereotype-votes/vote-choice-input.jinja2"
    renderer = get_template(template_name)

    def __init__(
        self, stereotype_action, attrs=None, comment=None, initial_vote_value=None
    ):
        super().__init__(attrs)
        self.comment = comment
        self.initial_vote_value = initial_vote_value
        self.stereotype_action = stereotype_action

    def render(self, name, value, attrs=None, renderer=None):
        context = self.get_context(name, value, attrs)
        context["comment_id"] = self.comment.id
        context["comment_content"] = self.comment.content
        context["initial_vote_value"] = self.initial_vote_value
        context["stereotype_action"] = self.stereotype_action

        value = context["widget"]["value"][0]
        if value:
            context["widget"]["value"] = FORM_CHOICE_MAP.get(value, value)
        return self.renderer.render(context)


class StereotypeVoteForm(forms.ModelForm):
    class Meta:
        model = StereotypeVote
        fields = ["comment", "choice"]
        widgets = {
            "comment": forms.HiddenInput(),
        }

    def __init__(
        self,
        stereotype_action="create",
        comments_queryset=None,
        stereotype=0,
        *args,
        **kwargs,
    ):
        super(StereotypeVoteForm, self).__init__(*args, **kwargs)
        initial_vote_value = None
        comment = self.initial.get("comment")
        if not comment or isinstance(comment, int):
            comment = self.instance.comment
            initial_vote_value = self.instance.choice

        self.fields["choice"] = forms.ChoiceField(
            required=False,
            choices=Choice.choices,
            widget=SelectWidget(
                stereotype_action, comment=comment, initial_vote_value=initial_vote_value
            ),
            label="",
        )
        self.fields["comment"].queryset = comments_queryset
        self.stereotype = stereotype

    def prepare_instance(self, choice):
        instance = super(StereotypeVoteForm, self).save(commit=False)
        instance.author = self.stereotype
        instance.choice = Choice.normalize(choice)
        return instance

    def save(self, choice, comment_id=None, commit=True):
        has_voted = "choice" in self.initial
        instance = self.prepare_instance(choice)

        comment = Comment.objects.get(id=comment_id)
        if choice and commit:
            instance.comment = comment
            instance.save()
        elif has_voted and commit:
            instance = StereotypeVote.objects.get(
                comment_id=comment_id, author_id=self.stereotype.id
            )
            instance.delete()
        return instance


class StereotypeVoteFormsetFactory:
    def __init__(self, extra=0) -> None:
        self.formset = forms.modelformset_factory(
            StereotypeVote, form=StereotypeVoteForm, extra=extra
        )

    def _make(
        self,
        comments,
        post=None,
        stereotype=None,
        prefix="create",
        action="create",
        queryset=Stereotype.objects.none(),
    ):
        return self.formset(
            post,
            queryset=queryset,
            form_kwargs={
                "comments_queryset": comments,
                "stereotype": stereotype or Stereotype.objects.first(),
                "stereotype_action": action,
            },
            initial=[{"comment": comment, "author": stereotype} for comment in comments],
            prefix=prefix,
        )

    def make_create(self, comments, post=None, stereotype=None):
        return self._make(comments, post=post, stereotype=stereotype)

    def make_edit(
        self,
        comments,
        prefix,
        post=None,
        stereotype=None,
        queryset=StereotypeVote.objects.none(),
    ):
        return self._make(
            comments,
            post=post,
            stereotype=stereotype,
            prefix=prefix,
            action="edit",
            queryset=queryset,
        )


class ClusterForm(EjModelForm):
    """
    Edit clusters when configuring opinion groups
    """

    class Meta:
        model = Cluster
        fields = ["name", "description", "stereotypes"]
        help_texts = {
            "stereotypes": _(
                "You can select multiple personas for each group. Personas are "
                "users used as reference that you control and define the opinion "
                "profile of groups."
            )
        }
        labels = {"stereotypes": _("Personas"), "new_persona": ""}

    def __init__(self, user=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["stereotypes"].required = False
        if user:
            self.owner = user
            self.fields["stereotypes"].queryset = Stereotype.objects.filter(
                owner=self.owner
            )


class ClusterFormNew(ClusterForm):
    new_persona = forms.BooleanField(
        required=False,
        initial=True,
        help_text=_(
            "Create new persona with the name of the group if no other persona is selected."
        ),
    )

    def clean(self):
        if not self.cleaned_data["new_persona"] and not self.cleaned_data["stereotypes"]:
            self.add_error(
                "stereotypes", _("You must select a persona or create a new one.")
            )
        if self.cleaned_data["new_persona"]:
            stereotype = Stereotype.objects.filter(
                name=self.cleaned_data["name"], owner=self.owner
            )
            if stereotype.exists():
                self.add_error(
                    "name",
                    _("A group with that name already exists. Choose a different name."),
                )

    def _save_m2m(self):
        super()._save_m2m()
        has_stereotypes = len(self.cleaned_data["stereotypes"]) != 0
        if self.cleaned_data["new_persona"] and not has_stereotypes:
            owner = self.instance.clusterization.conversation.author
            stereotype, _ = Stereotype.objects.get_or_create(
                name=self.cleaned_data["name"],
                description=self.cleaned_data["description"],
                owner=owner,
            )
            self.instance.stereotypes.add(stereotype)
