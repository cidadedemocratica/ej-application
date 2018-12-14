from boogie.router import Router
from django.http import Http404
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.translation import ugettext_lazy as _

from ej_conversations.models import Conversation, FavoriteConversation, Comment
from .forms import ProfileForm, UsernameForm

app_name = 'ej_profiles'
urlpatterns = Router(
    template=['ej_profiles/{name}.jinja2', 'generic.jinja2'],
    login=True,
)


@urlpatterns.route('')
def detail(request):
    user = request.user

    # Select conversations and comments in an optimized query
    favorites = (
        FavoriteConversation.objects
            .filter(user=user)
            .select_related('conversation')
            .prefetch_related('conversation__followers')
            .prefetch_related('conversation__tags')
    )
    conversations = [fav.conversation for fav in favorites]

    # Comments
    comments = (
        user.comments
            .all()
            .select_related('conversation')
            .select_related('author')
    )

    return {
        'which_tab': request.GET.get('info', 'profile'),
        'profile': user.profile,
        'conversations': conversations,
        'comments': comments,
    }


@urlpatterns.route('edit/')
def edit(request):
    profile = request.user.profile
    if request.method == 'POST':
        form = ProfileForm(request.POST, instance=profile, files=request.FILES)
        name_form = UsernameForm(request.POST, instance=request.user)
        if form.is_valid() and name_form.is_valid():
            form.save()
            name_form.save()
            return redirect('/profile/')
    else:
        form = ProfileForm(instance=profile)
        name_form = UsernameForm(instance=request.user)

    return {
        'form': form,
        'name_form': name_form,
        'profile': profile,
    }


@urlpatterns.route('conversations/', template='ej_conversations/list.jinja2')
def conversations_list(request):
    user = request.user
    boards = user.boards.all()
    conversations = []
    board = None
    board_palette = Conversation.get_default_css_palette()
    if len(boards) > 0:
        board = boards[0]
        conversations = board.conversations
        board_palette = board.css_palette
    return {
        'user': user,
        'conversations': conversations,
        'current_board': board,
        'boards': boards,
        'create_url': reverse('conversation:create'),
        # you can't add conversations because there can be more than one board being displayed
        'can_add_conversation': False,
        'title': _('My conversations'),
        'description': _('See all conversations created by you'),
        'board_palette': board_palette
    }


@urlpatterns.route('comments/')
def comments_list(request):
    user = request.user
    return {
        'user': user,
        'comments': user.comments.all(),
        'stats': user.comments.statistics(),
    }


@urlpatterns.route('favorites/')
def favorite_conversations(request):
    user = request.user
    favorites = FavoriteConversation.objects.filter(user=user)
    conversations = [fav.conversation for fav in favorites]
    return {
        'conversations': conversations,
    }


@urlpatterns.route('comments/<which>/')
def comments_tab(request, which):
    if which not in {'approved', 'pending', 'rejected'}:
        raise Http404

    st = Comment.STATUS
    status_map = {'approved': st.approved, 'pending': st.pending, 'rejected': st.rejected}
    user = request.user
    return {
        'user': user,
        'comments': user.comments.filter(status=status_map[which]),
        'stats': user.comments.statistics(),
    }
