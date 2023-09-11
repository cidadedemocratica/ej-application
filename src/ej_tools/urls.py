from django.urls import path
from . import views

app_name = "ej_tools"

base_path = "<int:conversation_id>/<slug:slug>/tools"
chatbot_base_path = base_path + "/chatbot"

urlpatterns = [
    path(
        base_path,
        views.index,
        name="index",
    ),
    path(
        f"{base_path}/mailing",
        views.mailing,
        name="mailing",
    ),
    path(
        f"{base_path}/opinion-component",
        views.OpinionComponentView.as_view(),
        name="opinion-component",
    ),
    path(
        f"{base_path}/opinion-component/preview",
        views.opinion_component_preview,
        name="opinion-component-preview",
    ),
    path(
        f"{base_path}/chatbot",
        views.chatbot,
        name="chatbot",
    ),
    path(
        f"{base_path}/telegram",
        views.telegram,
        name="telegram",
    ),
    path(
        f"{base_path}/mautic",
        views.mautic,
        name="mautic",
    ),
    path(
        f"{base_path}/mautic/delete/<int:mautic_connection_id>",
        views.delete_mautic_connection,
        name="delete-mautic-connection",
    ),
    path(
        f"{chatbot_base_path}/whatsapp",
        views.whatsapp,
        name="whatsapp",
    ),
    path(
        f"{chatbot_base_path}/webchat",
        views.webchat,
        name="webchat",
    ),
    path(
        f"{chatbot_base_path}/webchat-preview",
        views.webchat_preview,
        name="webchat-preview",
    ),
    path(
        f"{chatbot_base_path}/webchat/delete/<int:connection_id>",
        views.delete_connection,
        name="delete-connection",
    ),
]
