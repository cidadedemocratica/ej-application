import json

from django.contrib.auth import get_user_model
from django.http import HttpResponse
from sklearn.decomposition import PCA

from boogie.router import Router
from ej_clusters.math import get_raw_votes, get_votes, get_raw_cluster_users
from ej_conversations.models import Conversation

urlpatterns = Router(
    template=['ej_reports/{name}.jinja2', 'generic.jinja2'],
    object='conversation',
    models={'conversation': Conversation},
    lookup_field='slug',
    lookup_type='slug',
    login=False,
)
app_name = 'ej_reports'
reports_url = '<model:conversation>/reports/'
User = get_user_model()


#
# Base report URLs
#
@urlpatterns.route(reports_url)
def index(request, conversation):
    # user = request.user
    # can_download_data = user.has_perm('ej.can_edit_conversation', conversation)
    can_download_data = True
    clusterization = conversation.get_clusterization()
    clusterization.update()
    return {
        'clusters': clusterization.clusters.all(),
        'conversation': conversation,
        'users': conversation.statistics()['participants'],
        'can_download_data': can_download_data,
        'can_see_participants': can_download_data,
    }


@urlpatterns.route(reports_url + 'participants/', staff=True)
def participants_table(conversation):
    return {'conversation': conversation}


@urlpatterns.route(reports_url + 'scatter/')
def scatter(conversation):
    # TODO: make it use the pca-data.json endpoint
    votes = get_votes(conversation).fillna(0).values
    if votes.shape[0] <= 1 or votes.shape[1] <= 1:
        return {'error': 'insufficient data'}

    pca = PCA(n_components=2)
    pca.fit(votes)
    votes_pca = pca.transform(votes)
    return {'plot_data': json.dumps(votes_pca.tolist())}


#
# Raw data
#
@urlpatterns.route(reports_url + 'data/scatter-plot.json', template=None)
def scatter_plot_data(conversation):
    votes = get_votes(conversation).fillna(0).values
    if votes.shape[0] <= 1 or votes.shape[1] <= 1:
        return {'error': 'insufficient data'}

    pca = PCA(n_components=2)
    data = pca.fit_transform(votes)
    return {'votes': data.tolist()}


@urlpatterns.route(reports_url + 'data/votes.<format>')
def votes_data(conversation, format):
    response = file_response(conversation, 'votes', format)
    votes = get_raw_votes(conversation)
    generate_data_file(votes, format, response)
    return response


@urlpatterns.route(reports_url + 'data/comments.<format>')
def comments_data(conversation, format):
    response = file_response(conversation, 'comments', format)
    comments = conversation.comments_dataframe()
    generate_data_file(comments, format, response)
    return response


@urlpatterns.route(reports_url + 'data/users.<format>')
def users_data(conversation, format):
    response = file_response(conversation, 'users', format)
    votes = get_raw_votes(conversation)
    participants = participants_table(conversation, votes)
    generate_data_file(participants, format, response)
    return response


@urlpatterns.route(reports_url + 'data/clusters/<cluster_slug>.<format>')
def cluster_data(conversation, cluster_slug, format):
    from ej_boards.models import BoardSubscription
    is_conversation_in_board = BoardSubscription.objects.filter(conversation=conversation).exists()
    data_cat = ''
    if not is_conversation_in_board:
        data_cat = f'_{cluster_slug}'
    else:
        board = BoardSubscription.objects.get(conversation=conversation).board
        data_cat = f'{board.slug}_{cluster_slug.lower()}'
    response = file_response(conversation, data_cat, format)
    cluster_name = cluster_slug.replace('-', ' ')
    cluster_users = get_raw_cluster_users(conversation, cluster_name)

    generate_data_file(cluster_users, format, response)
    return response


def file_response(conversation, data_cat, format):
    response = HttpResponse(content_type=f'text/{format}')
    filename = f'filename={conversation.title}_{data_cat}.{format}'
    response['Content-Disposition'] = f'attachment; {filename}'
    return response


def generate_data_file(data, format, response):
    if format == 'json':
        return data.to_json(path_or_buf=response, force_ascii=False)
    elif format == 'csv':
        return data.to_csv(path_or_buf=response, index=False, mode='a')
    elif format == 'msgpack':
        return data.to_msgpack(path_or_buf=response, encoding='utf-8')
    else:
        return
