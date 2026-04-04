from django.http import HttpRequest, HttpResponse, HttpResponseForbidden
from django.shortcuts import render
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required
from django.views.generic.edit import UpdateView
from django.views.generic import ListView, CreateView, DeleteView
from django.urls import reverse_lazy

from ej_clusters.forms import StereotypeForm
from ej_clusters.models.clusterization import Clusterization
from ej_conversations.models.conversation import Conversation
from ..models import Stereotype


@method_decorator([login_required], name="dispatch")
class StereotypeListView(ListView):
    template_name = "ej_clusters/stereotypes/list.jinja2"

    def get_queryset(self):
        return self.request.user.stereotypes.prefetch_related(
            "clusters__clusterization__conversation"
        )

    def get_context_data(self, **kwargs):
        qs = self.get_queryset()
        stereotypes = []
        for stereotype in qs:
            stereotype.conversations = conversations = []
            for cluster in stereotype.clusters.all():
                conversations.append(cluster.clusterization.conversation)
            stereotypes.append(stereotype)
        return {"stereotypes": stereotypes}


@method_decorator([login_required], name="dispatch")
class StereotypeCreateView(CreateView):
    template_name = "ej_clusters/stereotypes/create.jinja2"

    def post(self, request: HttpRequest, *args, **kwargs) -> HttpResponse:
        id = self.kwargs["clusterization_id"]
        context = self.get_context_data()
        clusterization = Clusterization.objects.filter(pk=id).get()
        form = StereotypeForm(
            owner=self.request.user,
            request=request,
            clusterization=clusterization,
        )
        if form.is_valid_post():
            stereotype = form.save()
            response = HttpResponse("")
            response["HX-Trigger"] = (
                '{"integrateData": ' + str(stereotype.id) + "}"
            )
            return response
        context["create_form"] = form
        return render(request, self.template_name, context)

    def get_context_data(self, **kwargs):
        form = StereotypeForm(request=self.request, owner=self.request.user)
        return {
            "create_form": form,
            "clusterization_id": self.kwargs["clusterization_id"],
        }


@method_decorator([login_required], name="dispatch")
class StereotypeEditView(UpdateView):
    model = Stereotype
    template_name = "ej_clusters/stereotypes/edit.jinja2"
    form_class = StereotypeForm

    def post(self, request: HttpRequest, *args, **kwargs) -> HttpResponse:
        stereotype = self.get_object()
        form = self.form_class(request=self.request, instance=stereotype)

        if form.is_valid_post():
            form.save()
        return render(request, self.template_name, self.get_context_data())

    def get_object(self) -> Stereotype:
        stereotype = super().get_object()
        user = self.request.user
        is_superuser = user.is_staff or user.is_superuser

        if stereotype.owner == user or is_superuser:
            return stereotype
        raise HttpResponseForbidden

    def get_context_data(self, **kwargs):
        stereotype = self.get_object()
        form = self.kwargs.get(
            "form", self.form_class(request=self.request, instance=stereotype)
        )
        return {"form": form, "stereotype": stereotype}


@method_decorator([login_required], name="dispatch")
class StereotypeDeleteView(DeleteView):
    model = Stereotype

    def get_object(self, queryset=None):
        id = self.kwargs["pk"]
        return self.get_queryset().filter(pk=id).get()

    def get_success_url(self):
        data = self.request.POST
        conversation = Conversation.objects.get(id=data["conversation_id"])
        return reverse_lazy(
            "boards:stereotype-votes-list",
            kwargs=conversation.get_url_kwargs(),
        )

    def form_valid(self, request, *args, **kwargs):
        clusters = self.get_object().clusters
        clusters.all().delete()

        return super().delete(self, request, *args, **kwargs)
