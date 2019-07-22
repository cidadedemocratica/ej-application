from logging import getLogger

from django.http import HttpResponseServerError, Http404
from django.urls import reverse
from django.utils.translation import ugettext_lazy as _
from hyperpython import a

from boogie import rules
from . import urlpatterns, conversation_url
from ..forms import CommentForm
from ..models import Conversation, Comment
from ej_conversations.rules import max_comments_per_conversation

log = getLogger('ej')


@urlpatterns.route('', name='list')
def conversation_list(request):
    return {
        'conversations': Conversation.objects.filter(is_promoted=True, is_hidden=False),
        'can_add_conversation': request.user.has_perm('ej.can_add_promoted_conversation'),
        'create_url': reverse('conversation:create'),
        'topic': _('A space for adolescents to discuss actions that promote, guarantee and defend their rights'),
        'title': _('Public conversations'),
        'subtitle': _('Participate of conversations and give your opinion with comments and votes!'),
        'description': _('Participate of conversations and give your opinion with comments and votes!'),
        'board_palette': Conversation.get_default_css_palette()
    }


@urlpatterns.route(conversation_url)
def detail(request, conversation):
    if not conversation.is_promoted:
        raise Http404
    return get_conversation_detail_context(request, conversation)


#
# Auxiliary and re-usable functions
#
def get_conversation_detail_context(request, conversation):
    """
    Common implementation used by both /conversations/<slug> and inside boards
    in /<board>/conversations/<slug>/
    """
    user = request.user
    is_favorite = user.is_authenticated and conversation.followers.filter(user=user).exists()
    comment = None
    comment_form = CommentForm(None, conversation=conversation)
    # User is voting in the current comment. We still need to choose a random
    # comment to display next.
    if request.POST.get('action') == 'vote':
        vote = request.POST['vote']
        comment_id = request.POST['comment_id']
        Comment.objects.get(id=comment_id).vote(user, vote)
        log.info(f'user {user.id} voted {vote} on comment {comment_id}')

    # User is posting a new comment. We need to validate the form and try to
    # keep the same comment that was displayed before.
    elif request.POST.get('action') == 'comment':
        comment_form = CommentForm(request.POST, conversation=conversation)
        if comment_form.is_valid():
            new_comment = comment_form.cleaned_data['content']
            new_comment = conversation.create_comment(user, new_comment)
            comment_form = CommentForm(conversation=conversation)
            log.info(f'user {user.id} posted comment {new_comment.id} on {conversation.id}')

    # User toggled the favorite status of conversation.
    elif request.POST.get('action') == 'favorite':
        conversation.toggle_favorite(user)
        log.info(f'user {user.id} toggled favorite status of conversation {conversation.id}')

    # User is probably trying to something nasty ;)
    elif request.method == 'POST':
        log.warning(f'user {user.id} se nt invalid POST request: {request.POST}')
        return HttpResponseServerError('invalid action')
    n_comments_under_moderation = rules.compute('ej_conversations.comments_under_moderation', conversation, user)
    if user.is_authenticated:
        comments_made = user.comments.filter(conversation=conversation).count()
    else:
        comments_made = 0

    if request.GET.get('vote') and request.GET.get('comment_id'):
        campaign_comment_id = request.GET.get('comment_id')
        comment = Comment.campaign_comment(comment,
                                           campaign_comment_id,
                                           user)
    return {
        # Objects
        'conversation': conversation,
        'comment': comment or conversation.next_comment(user, None),
        'login_link': login_link(_('login'), conversation),
        'comment_form': comment_form,

        # Permissions and predicates
        'is_favorite': is_favorite,
        'can_comment': user.is_authenticated,
        'can_edit': user.has_perm('ej.can_edit_conversation', conversation),
        'cannot_comment_reason': '',
        'comments_under_moderation': n_comments_under_moderation,
        'comments_made': comments_made,
        'max_comments': max_comments_per_conversation(),
        'board_palette': conversation.css_palette
    }


def login_link(content, obj):
    path = obj.get_absolute_url()
    return a(content, href=reverse('auth:login') + f'?next={path}')
