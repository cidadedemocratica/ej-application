from logging import getLogger
from typing import Any, Dict

from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.views.generic import ListView, TemplateView
from django.views.generic.edit import UpdateView
from ej.decorators import can_edit_conversation
from ej_clusters.models.clusterization import Clusterization
from ej_conversations.models import Conversation
from ej_conversations.utils import check_promoted
from ej_dataviz.utils import get_conversation_biggest_cluster

from .. import forms

log = getLogger("ej")


@method_decorator([login_required, can_edit_conversation], name="dispatch")
class ClustersIndexView(ListView):
    template_name = "ej_clusters/index.jinja2"

    def get_queryset(self):
        conversation = Conversation.objects.get(id=self.kwargs["conversation_id"])
        return getattr(conversation, "clusterization", None)

    def get_context_data(self, **kwargs: Any) -> Dict[str, Any]:
        conversation = Conversation.objects.get(id=self.kwargs["conversation_id"])
        user = self.request.user
        clusterization = self.get_queryset()
        clusterization.update_clusterization(force=True)
        biggest_cluster_data = get_conversation_biggest_cluster(
            self.request, conversation
        )

        json_shape_user_group = Clusterization.get_shape_data_by_groups(
            clusterization, user
        )

        return {
            "conversation": conversation,
            "num_groups": clusterization.get_clusters_count(),
            "biggest_cluster_data": biggest_cluster_data,
            **json_shape_user_group,
        }


@method_decorator([login_required, can_edit_conversation], name="dispatch")
class ClustersEditView(UpdateView):
    template_name = "ej_clusters/edit.jinja2"

    def setup(self, request: HttpRequest, *args: Any, **kwargs: Any) -> None:
        super().setup(request, *args, **kwargs)
        conversation_id = kwargs["conversation_id"]
        self.conversation = get_object_or_404(Conversation, id=conversation_id)
        self.post_actions = {
            "delete": self.handle_delete_cluster,
            "edit": self.handle_edit_cluster,
        }

    def get(self, request: HttpRequest, *args: str, **kwargs: Any) -> HttpResponse:
        new_cluster_form = forms.ClusterFormNew(user=self.conversation.author)
        clusters = self.get_queryset()
        context_args = {"new_cluster_form": new_cluster_form}

        current_cluster_id = request.GET.get("cluster-select", None)
        if current_cluster_id:
            selected_cluster = get_object_or_404(clusters, id=current_cluster_id)
            context_args = {"selected_cluster": selected_cluster}

        elif "delete-success" in request.GET:
            context_args["show_modal"] = "deleted_group"

        return render(request, self.template_name, self.get_context_data(**context_args))

    def post(self, request: HttpRequest, *args: str, **kwargs: Any) -> HttpResponse:
        clusters = self.get_queryset()
        action = request.POST.get("action")
        cluster_id = request.POST.get("cluster_id", None)

        action_method = self.post_actions.get(action)
        if action_method:
            return action_method(clusters, cluster_id)

        return self.handle_new_cluster()

    def handle_new_cluster(self):
        new_cluster_form = forms.ClusterFormNew(
            request=self.request, user=self.conversation.author
        )
        context_args = {"new_cluster_form": new_cluster_form}

        if new_cluster_form.is_valid():
            clusterization = self.conversation.get_clusterization()
            new_cluster_form.save(clusterization=clusterization)
            context_args["show_modal"] = "created_group_modal"

        return render(
            self.request,
            self.template_name,
            self.get_context_data(**context_args),
        )

    def handle_delete_cluster(self, clusters, cluster_id):
        cluster = get_object_or_404(clusters, id=cluster_id)
        cluster.delete()
        kwargs = self.conversation.get_url_kwargs()
        return redirect(reverse("boards:cluster-edit", kwargs=kwargs) + "?delete-success")

    def handle_edit_cluster(self, clusters, cluster_id):
        cluster = get_object_or_404(clusters, id=cluster_id)

        if cluster.form.is_valid():
            cluster = cluster.form.save()
            cluster.form = forms.ClusterForm(
                instance=cluster, user=self.conversation.author
            )

        return render(
            self.request,
            self.template_name,
            self.get_context_data(selected_cluster=cluster),
        )

    def get_queryset(self):
        clusterization = getattr(self.conversation, "clusterization", None)

        if clusterization is None:
            return ()

        return clusterization.clusters.annotate_attr(
            form=lambda x: forms.ClusterForm(
                request=self.request, instance=x, user=self.conversation.author
            )
        )

    def get_context_data(
        self,
        new_cluster_form=None,
        selected_cluster=None,
        show_modal=False,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        return {
            "conversation": self.conversation,
            "clusters": self.get_queryset(),
            "new_cluster_form": new_cluster_form,
            "edit_cluster": selected_cluster,
            "show_modal": show_modal,
            "current_page": "edit-groups",
        }


@method_decorator([login_required, can_edit_conversation], name="dispatch")
class CtrlView(TemplateView):
    def get(
        self, request: HttpRequest, conversation_id, *args: Any, **kwargs: Any
    ) -> HttpResponse:
        return redirect(
            reverse(
                "boards:stereotype-votes-list", kwargs=self.get_kwargs(conversation_id)
            )
        )

    def post(
        self, request: HttpRequest, conversation_id, *args: Any, **kwargs: Any
    ) -> HttpResponse:
        conversation = Conversation.objects.get(id=conversation_id)
        check_promoted(conversation, request)
        if request.POST["action"] == "force-clusterization":
            conversation.clusterization.update_clusterization(force=True)
        return redirect(
            reverse(
                "boards:stereotype-votes-list", kwargs=self.get_kwargs(conversation_id)
            )
        )

    def get_kwargs(self, conversation_id):
        conversation = Conversation.objects.get(id=conversation_id)
        return conversation.get_url_kwargs()
