from typing import Any

from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render, get_object_or_404
from django.utils.decorators import method_decorator
from django.views.generic import ListView, CreateView

from ej.decorators import can_edit_conversation
from ej_clusters.stereotypes_utils import stereotype_vote_information
from ej_conversations.models import Conversation
from .. import forms
from ..models import Stereotype


@method_decorator([login_required, can_edit_conversation], name="dispatch")
class StereotypeVotesView(ListView):
    template_name = "ej_clusters/stereotype-votes.jinja2"

    def setup(self, request: HttpRequest, *args: Any, **kwargs: Any) -> None:
        super().setup(request, *args, **kwargs)
        conversation_id = kwargs["conversation_id"]
        self.conversation = get_object_or_404(Conversation, id=conversation_id)
        self.clusterization = self.conversation.get_clusterization()

    def dispatch(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        if self.clusterization is None:
            return render(
                request,
                self.template_name,
                {
                    "conversation": self.conversation,
                    "groups": None,
                    "current_page": "stereotypes",
                },
            )
        return super().dispatch(request, *args, **kwargs)

    def get(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        self.stereotype = self.clusterization.stereotypes.first()

        if "stereotype-select" in request.GET:
            self.stereotype = Stereotype.objects.get(id=request.GET["stereotype-select"])
        return render(request, self.template_name, self.get_context_data())

    def post(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        stereotype = Stereotype.objects.get(id=request.POST["stereotype_id"])
        self.stereotype = stereotype
        context = self.get_context_data()

        stereotype_votes_formset = forms.StereotypeVoteFormsetFactory()
        stereotype_votes_formset = stereotype_votes_formset.make_create(
            comments=self.comments, post=request.POST, stereotype=stereotype
        )

        for form in stereotype_votes_formset:
            if form.is_valid():
                form.save(form["choice"].value(), form["comment"].value())

        context["stereotype_votes_formset"] = stereotype_votes_formset
        return render(request, self.template_name, context)

    def get_context_data(self, **kwargs):
        conversation = Conversation.objects.get(id=self.kwargs["conversation_id"])
        groups = self.clusterization.get_stereotypes()
        self.comments = conversation.comments.approved()

        stereotype_votes_formset = forms.StereotypeVoteFormsetFactory(
            extra=self.comments.count()
        )
        stereotype_votes_formset = stereotype_votes_formset.make_create(
            comments=self.comments
        )

        return {
            "conversation": conversation,
            "stereotype": stereotype_vote_information(
                self.stereotype, self.clusterization, self.conversation
            ),
            "current_page": "stereotypes",
            "groups": groups,
            "tab_index": 0 if groups else 1,
            "stereotype_votes_formset": stereotype_votes_formset,
            "clusterization_id": self.clusterization.id,
        }


@method_decorator([login_required, can_edit_conversation], name="dispatch")
class StereotypeVotesManageView(CreateView):
    template_name = "ej_clusters/stereotype-votes/manage-stereotype-votes.jinja2"

    def post(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        context = self.get_context_data()

        non_voted = self.stereotype.non_voted_comments(context["conversation"])
        non_voted_formset = forms.StereotypeVoteFormsetFactory(extra=non_voted.count())
        non_voted_formset = non_voted_formset.make_edit(
            comments=non_voted,
            prefix="non-voted",
            post=request.POST,
            stereotype=self.stereotype,
        )

        for form in non_voted_formset:
            if form.is_valid():
                form.save(form["choice"].value(), form["comment"].value())

        voted_comments = self.stereotype.voted_comments(context["conversation"])
        voted_formset = forms.StereotypeVoteFormsetFactory()
        voted_formset = voted_formset.make_edit(
            comments=voted_comments,
            prefix="edit-voted",
            post=request.POST,
            stereotype=self.stereotype,
            queryset=self.stereotype.votes.all(),
        )
        for form in voted_formset:
            if form.is_valid():
                form.save(form["choice"].value(), form["comment"].value())

        return render(request, self.template_name, context)

    def get_context_data(self, **kwargs):
        conversation = Conversation.objects.get(id=self.kwargs["conversation_id"])
        self.comments = conversation.comments.approved()
        self.stereotype = Stereotype.objects.get(id=self.kwargs["pk"])

        non_voted = self.stereotype.non_voted_comments(conversation)
        non_voted_formset = forms.StereotypeVoteFormsetFactory(extra=non_voted.count())
        non_voted_formset = non_voted_formset.make_edit(
            comments=non_voted, prefix="non-voted", stereotype=self.stereotype
        )

        voted_comments = self.stereotype.voted_comments(conversation)
        voted_formset = forms.StereotypeVoteFormsetFactory()
        voted_formset = voted_formset.make_edit(
            comments=voted_comments,
            prefix="edit-voted",
            stereotype=self.stereotype,
            queryset=self.stereotype.votes.all(),
        )

        return {
            "conversation": conversation,
            "stereotype": self.stereotype,
            "non_voted_formset": non_voted_formset,
            "voted_formset": voted_formset,
        }
