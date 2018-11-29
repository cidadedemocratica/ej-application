from django.db import transaction
from django.http import Http404
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.translation import ugettext_lazy as _

from boogie.router import Router
from ej_boards.models import Board
from ej_clusters.models import Stereotype
from ej_clusters.routes import create_stereotype_context, edit_stereotype_context
from ej_conversations import forms
from ej_conversations.models import Conversation
from ej_conversations.routes import (get_conversation_detail_context,
                                     get_conversation_moderate_context,
                                     get_conversation_edit_context)
from ej_reports import routes as report_routes
from .forms import BoardForm

app_name = 'ej_boards'

#
# Board management
#
urlpatterns = Router(
    template=['ej_boards/{name}.jinja2', 'generic.jinja2'],
    object='conversation',
    models={
        'board': Board,
        'conversation': Conversation,
        'stereotype': Stereotype,
    },
    lookup_field={'conversation': 'slug', 'board': 'slug'},
    lookup_type={'conversation': 'slug', 'board': 'slug'},
)


#
# Conversation URLs
#
@urlpatterns.route('<model:board>/conversations/')
def conversation_list(request, board):
    user = request.user
    conversations = board.conversations.filter(is_hidden=False)
    board_user = board.owner
    boards = []
    boards_count = 0
    if user == board_user:
        boards = board_user.boards.all()
        boards_count = boards.count()
        user_is_owner = True
    else:
        user_is_owner = False
    return {
        'can_add_conversation': user_is_owner,
        'can_edit_board': user_is_owner,
        'create_url': reverse('boards:conversation-create', kwargs={'board': board}),
        'edit_url': reverse('boards:board-edit', kwargs={'board': board}),
        'conversations': conversations,
        'boards_count': boards_count,
        'boards': boards,
        'current_board': board,
        'title': board.title,
        'description': board.description,
        'show_welcome_window': False,
        'board_palette': 'Palette' + board.palette,
    }


@urlpatterns.route('<model:board>/conversations/add/')
def conversation_create(request, board):
    user = request.user
    if not user == board.owner:
        raise Http404

    form = forms.ConversationForm(request.POST or None)

    if request.method == 'POST' and form.is_valid():
        with transaction.atomic():
            conversation = form.save_all(
                author=user,
                board=board,
            )
        return redirect(f'/{board.slug}/conversations/{conversation.slug}/stereotypes/')

    return {'form': form}


@urlpatterns.route('<model:board>/conversations/<model:conversation>/')
def conversation_detail(request, board, conversation):
    assure_correct_board(conversation, board)
    return get_conversation_detail_context(request, conversation)


@urlpatterns.route('<model:board>/conversations/<model:conversation>/edit/',
                   perms=['ej.can_edit_conversation'])
def conversation_edit(request, board, conversation):
    assure_correct_board(conversation, board)
    ctx = get_conversation_edit_context(request, conversation)
    ctx['board'] = board
    return ctx


@urlpatterns.route('<model:board>/conversations/<model:conversation>/moderate/',
                   perms=['ej.can_edit_conversation'])
def conversation_moderate(request, board, conversation):
    assure_correct_board(conversation, board)
    return get_conversation_moderate_context(request, conversation)


@urlpatterns.route('<model:board>/conversations/<model:conversation>/stereotypes/',
                   perms=['ej.can_manage_stereotypes'])
def conversation_stereotype_list(board, conversation):
    assure_correct_board(conversation, board)
    return {
        'content_title': _('Stereotypes'),
        'conversation_title': conversation.title,
        'stereotypes': conversation.stereotypes.all(),
        'stereotype_url': conversation.get_absolute_url() + 'stereotypes/',
        'conversation_url': conversation.get_absolute_url(),
    }


@urlpatterns.route('<model:board>/conversations/<model:conversation>/stereotypes/add/',
                   perms=['ej.can_manage_stereotypes'])
def conversation_stereotype_create(request, board, conversation):
    assure_correct_board(conversation, board)
    return create_stereotype_context(request, conversation)


@urlpatterns.route('<model:board>/conversations/<model:conversation>/stereotypes/<model:stereotype>/edit/',
                   perms=['ej.can_manage_stereotypes'])
def conversation_stereotype_edit(request, board, conversation, stereotype):
    assure_correct_board(conversation, board)
    return edit_stereotype_context(request, conversation, stereotype)


#
# Board URLs
#
@urlpatterns.route('profile/boards/', login=True)
def board_list(request):
    user = request.user
    boards = user.boards.all()
    can_add_board = user.has_perm('ej_boards.can_add_board')

    if not can_add_board and user.boards.count() == 1:
        return redirect(f'{boards[0].get_absolute_url()}conversations/')

    return {
        'boards': boards,
        'can_add_board': can_add_board,
    }


@urlpatterns.route('profile/boards/add/', login=True)
def board_create(request):
    user = request.user
    if not user.has_perm('ej_boards.can_add_board'):
        raise Http404

    form_class = BoardForm
    if request.method == 'POST':
        form = form_class(request.POST)
        if form.is_valid():
            board = form.save(commit=False)
            board.owner = user
            board.save()

            return redirect(board.get_absolute_url())
    else:
        form = form_class()

    return {
        'content_title': _('Create board'),
        'form': form,
    }


# Conversation and boards management
@urlpatterns.route('<model:board>/edit/')
def board_edit(request, board):
    if request.user != board.owner:
        raise PermissionError
    if request.method == 'POST':
        form = BoardForm(request.POST, instance=board)
        if form.is_valid():
            form.instance.save()
            return redirect(board.get_absolute_url())
    else:
        form = BoardForm(instance=board)
    return {
        'form': form,
    }


#
# Reports
#
reports_url = '<model:board>/conversations/<model:conversation>/reports/'
reports_kwargs = {'login': True}


@urlpatterns.route(reports_url, **reports_kwargs)
def report(request, board, conversation):
    assure_correct_board(conversation, board)
    return report_routes.index(request, conversation)


@urlpatterns.route(reports_url + 'participants/', staff=True, **reports_kwargs)
def report_participants(request, board, conversation):
    assure_correct_board(conversation, board)
    return report_routes.participants_table(conversation)


@urlpatterns.route(reports_url + 'scatter/', **reports_kwargs)
def report_scatter(board, conversation):
    assure_correct_board(conversation, board)
    return report_routes.scatter(conversation)


@urlpatterns.route(reports_url + 'votes.<format>', **reports_kwargs)
def report_votes_data(board, conversation, format):
    assure_correct_board(conversation, board)
    return report_routes.generate_votes(conversation, format)


@urlpatterns.route(reports_url + 'users.<format>', **reports_kwargs)
def report_users_data(board, conversation, format):
    assure_correct_board(conversation, board)
    return report_routes.generate_users(conversation, format)


@urlpatterns.route(reports_url + 'comments.<format>', **reports_kwargs)
def report_comments_data(board, conversation, format):
    assure_correct_board(conversation, board)
    return report_routes.generate_comments(conversation, format)


#
# Utility functions
#
def assure_correct_board(conversation, board):
    """
    Raise 404 if conversation does not belong to board.
    """
    if not board.has_conversation(conversation):
        raise Http404
