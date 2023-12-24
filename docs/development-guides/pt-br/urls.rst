**********************
Estruturação das URLs
**********************


Este documento registra as URLs padrão usadas na plataforma e onde encontrar-las em seus
respectivos aplicativos.

Users/login (ej_users app)
==========================

Views públicas que controlam a autenticação e a criação de novos usuários.
As views de login e registro aceitam uma tag ?next=<url> que controla o
página de redirecionamento.


Ações que não precisam de autenticação
------------------------------------------

login/ (auth:login):
    Página de login.
    Implementação :func:`ej_users.routes.login`.
register/ (auth:register):
    Registra um novo usuário.
    Implementação :func:`ej_users.routes.register`.
recover-password/ (auth:recover-password):
    Recupera a senha de um usuário.
    Implementação :func:`ej_users.routes.recover_password`
recover-password/<token> (auth:recover-password-token):
    URL enviada por email após o usuário fazer a solicitação de troca de senha.
    Implementação :func:`ej_users.routes.recover_password_token`.
login/api-key/ (auth:api-key):
    Login baseado em API. Utilizado por integrações como o componente de conversa e o rasachatbot.
    Implementation :func:`ej_users.routes.login`.


Ações que necessitam autenticação
-----------------------------------

account/ (account:index):
    Manage basic account actions such as password reset, e-mail reset, etc.
    Implementation :func:`ej_users.routes_account.index`.
account/logout/ (account:logout):
    End user session.
    Implementation :func:`ej_users.routes_account.logout`.
account/remove/ (account:remove-account):
    Remove user account. This is an non-reversible operation that the user
    must confirm in order to actually remove the account.
    Implementation :func:`ej_users.routes_account.remove`.
account/manage-email/ (account:manage-email):
    Allow user to change its e-mail.
    Implementation :func:`ej_users.routes_account.manage_email`.
account/change-password/ (account:change-password):
    Allow user to change its password.
    Implementation :func:`ej_users.routes_account.change_password`.

All views are included in the ``ej_accounts`` app.



Views de perfil (ej_profiles)
==============================

Users cannot see each other's profiles since EJ is not meant to be a traditional
social network. There is no concept of "friends", "followers",
"private conversations" etc.

profile/ (profile:detail):
    Show user profile.
    Implementation :func:`ej_profiles.routes.detail`.
profile/edit/ (profile:edit):
    Edit profile.
    Implementation :func:`ej_profiles.routes.edit`.
profile/contributions/ (profile:comments):
    Show statistics and information about all contributions of the user to
    conversations in the platform.
    Implementation :func:`ej_profiles.routes.contributions`.



Conversations (ej_conversations)
================================

Public views for displaying information about conversations.

conversations/ (conversations:list):
    List all available conversations
    Implementation :func:`ej_conversations.routes.list_view`.
conversations/<id>/<slug>/ (conversations:conversation-detail):
    Detail page for an specific conversation.
    Implementation :func:`ej_conversations.routes.detail`.


CRUD (ej_conversations)
-----------------------

All those URLS are only available for users with permission to edit
conversations. This can be applied to staff members or to the owner of the
conversation.

conversations/create/ (conversations:create-conversation):
    Add a new conversation.
    Implementation :func:`ej_conversations.routes.create`.
conversations/<id>/<slug>/edit/ (conversations:edit-conversation):
    Edit conversation.
    Implementation :func:`ej_conversations.routes.edit`.
conversations/<id>/<slug>/moderate/ (conversations:moderate-comments):
    Can classify all non-moderated comments.
    Implementation :func:`ej_conversations.routes.moderate`.



Reports (ej_dataviz)
--------------------

Only staff members and the conversation owner have access to those pages.

conversations/<id>/<slug>/reports/ (reports:index):
    Aggregate reports for the given conversation.
conversations/<id>/<slug>/reports/users/ (reports:radar):
    Display comments in a 2D layout to show the distribution of opinions and
    comments.

Clusters (ej_clusters)
----------------------

Display the clusters associated with a conversation. All those urls require
authentication, but are visible to all users.

conversations/<id>/<slug>/clusters/ (clusters:index):
    See cluster information in conversation.
    Implementation :func:`ej_clusters.routes.index`.
conversations/<id>/<slug>/clusters/edit/ (clusters:edit):
    Edit clusterization configurations.
    Implementation :func:`ej_clusters.routes.edit`.
conversations/<id>/<slug>/stereotypes/ (clusters:stereotype-votes):
    Cast stereotype votes in conversation.
    Implementation :func:`ej_clusters.routes.stereotype_votes`.



Clusters and Stereotypes (ej_clusters)
--------------------------------------

Only staff members and the conversation owner have access to those pages.

conversations/<id>/<slug>/stereotypes/ (clusters:stereotype-list):
    List of all stereotypes showing information about the assigned cluster and
    statistics.
conversations/<id>/<slug>/stereotypes/<id>/ (clusters:stereotype-vote):
    Allow the given stereotype to vote in conversation.


Help
====

Urls with the intention of explaining how to use the platform. Most of those
urls are implemented as flat pages and are stored as HTML or markdown under
either local/pages or lib/pages/.

/start/ (home):
    Landing-page broadly explaining what is EJ and how to use the platform.
/faq/ (faq):
    Frequently asked questions.
/about-us/ (about):
    About EJ or the organization deploying an instance.
/usage/ (usage):
    Usage terms for the platform.
/contact/ (contact):
    Contact information

All URLs are implemented as flat pages in the Django Admin. The content
of those URLs can be editable at ``/admin/flatpages/flatpage/``.


Administrative URLs
===================

All views in this section require staff permissions.

admin/:
    Django admin page. Users must be staff members.
/info/ (info):
    Show basic debug information about the server
    Implementation :func:`ej.routes.info`.
/info/styles/ (info-styles):
    Exhibit the main design elements like colors and typography applied in the
    current theme.
    Implementation :func:`ej.routes.info_styles`.
/info/ (info-django-settings):
    Display current Django settings. Only the admin user can see this page.
    Implementation :func:`ej.routes.info_django_settings`.
