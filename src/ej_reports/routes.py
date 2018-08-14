import numpy as np
import pandas as pd
from django.contrib.auth import get_user_model
from django.http import HttpResponse
from django.utils.translation import ugettext_lazy as _, ugettext as __

from boogie.router import Router
from boogie.rules import proxy_seq
from ej_clusters.math import get_raw_votes
from ej_conversations.models import Conversation
from ej_dataviz import render_dataframe
from ej_math import VoteStats
from hyperpython.components import html_table, hyperlink


app_name = 'ej_reports'
urlpatterns = Router(
    template=['ej_reports/{name}.jinja2', 'generic.jinja2'],
    perms=['ej_reports.can_view_report'],
    object='conversation',
    models={
        'conversation': Conversation,
    },
    lookup_field='slug',
    lookup_type='slug',
    login=True,
)
conversation_url = '<model:conversation>/reports/'
User = get_user_model()


@urlpatterns.route(conversation_url)
def index(request, conversation):
    statistics = conversation.statistics()
    votes = get_raw_votes(conversation)
    comments = comments_table(conversation, votes)
    participants = participants_table(conversation, votes)
    clusters = proxy_seq(
        conversation.clusters.all(),
        all_votes=votes,
        comment_table=cluster_comments_table,
        size=lambda x: x.users.count(),
    )
    # Change agree and disagree comments to add up to 100% with skipped
    remaining = 100 - comments["skipped"]
    comments["agree"] = 0.01 * comments["agree"] * remaining
    comments["disagree"] = 0.01 * comments["disagree"] * remaining

    # Change agree and disagree participants to add up to 100% with skipped
    remaining = 100 - participants["skipped"]
    participants["agree"] = 0.01 * participants["agree"] * remaining
    participants["disagree"] = 0.01 * participants["disagree"] * remaining

    if request.GET.get('action') == 'generate_csv':
        response = generate_csv(conversation, statistics, votes, comments,
                                participants, clusters)
    elif request.GET.get('action') == 'generate_json':
        response = generate_json(conversation, statistics, votes, comments,
                                 participants, clusters)
    elif request.GET.get('action') == 'generate_msgpack':
        response = generate_msgpack(conversation, statistics, votes, comments,
                                    participants, clusters)
    else:
        response = {
            'page_title': _('Report'),
            'content_title': hyperlink(conversation),
            'conversation': conversation,
            'statistics': statistics,
            'vote_data': map_to_html_table(statistics['votes']),
            'comment_data': map_to_html_table(statistics['comments']),
            'comments_table': df_to_table(comments),
            'participants_table': df_to_table(participants),
            'clusters': clusters,
        }
    return response


@urlpatterns.route(conversation_url + 'clusters/')
def clusters(conversation):
    return {
        'conversation': conversation,
    }


@urlpatterns.route(conversation_url + 'radar/')
def radar(conversation):
    return {
        'conversation': conversation,
    }


@urlpatterns.route(conversation_url + 'divergence/')
def divergence(conversation):
    return {
        'conversation': conversation,
    }


#
# Auxiliary functions and data
#
COLUMN_NAMES = {
    'author': _('Author'),
    'text': _('Text'),
    'votes': _('Votes'),
    'missing': _('Missing'),
    'skipped': _('Skipped'),
    'agree': _('Agree'),
    'disagree': _('Disagree'),
    'average': _('Average'),
    'divergence': _('Divergence'),
    'entropy': _('Entropy'),
    'comment': _('Comment'),
    'user': _('User'),
    'participation': _('Participation ratio'),
    'name': _('Name'),
}
PC_COLUMNS = [
    'missing', 'skipped', 'agree', 'disagree', 'average',
    'divergence', 'entropy', 'participation',
]


def map_to_table(data):
    return np.array(list(data.items())).T


def map_to_html_table(cols):
    array = map_to_table(cols)
    cols, body = array
    cols = [__(col) for col in cols]
    return html_table([body], columns=cols, class_='ReportTable table')


def df_to_table(df, pc=True):
    if pc:
        for col in PC_COLUMNS:
            if col in df:
                df[col] = to_pc(df[col])
    return render_dataframe(df, col_display=COLUMN_NAMES, class_='table long')


def to_pc(data):
    """
    Map floats to percentages.
    """

    def transform(x):
        if isinstance(x, int):
            return str(x)
        elif np.isnan(x):
            return '-'
        else:
            return '%d%%' % x

    return list(map(transform, data))


def cluster_comments_table(cluster):
    usernames = list(cluster.users.all().values_list('email', flat=True))

    # Filter votes by users present in cluster
    df = cluster.all_votes
    votes = df[df['user'].isin(usernames)]

    data = comments_table(cluster.conversation, votes)
    data = data.sort_values('agree', ascending=False)
    return df_to_table(data)


def comments_table(conversation, votes):
    """
    Data frame with information about each comment in conversation.
    """

    stats = VoteStats(votes)
    df = stats.comments(pc=True)
    comments = conversation.comments.approved().display_dataframe()
    comments = comments[['author', 'text']]
    for col in ['agree', 'disagree', 'skipped', 'divergence']:
        comments[col] = df[col]
    comments['participation'] = 100 - df['missing']
    comments.dropna(inplace=True)
    return comments


def participants_table(conversation, votes):
    """
    Data frame with information about each participant in conversation.
    """

    stats = VoteStats(votes)
    df = stats.users(pc=True)

    data = list(User.objects.values_list('email', 'name'))
    participants = pd.DataFrame(list(data), columns=['email', 'name'])
    participants.index = participants.pop('email')

    for col in ['agree', 'disagree', 'skipped', 'divergence']:
        participants[col] = df[col]

    return participants


def generate_csv(conversation, statistics, votes, comments, participants, clusters):
    response = HttpResponse(content_type='text/csv')
    filename = 'filename={}.csv'.format(conversation.title)
    response['Content-Disposition'] = 'attachment; {}'.format(filename)

    # Change participants property for ease of use
    statistics["participants"] = {"total": statistics["participants"]}

    for item in statistics:
        title = [item]
        title = pd.DataFrame(title)
        title.to_csv(path_or_buf=response, header=False, index=False, mode='a')
        statistics_df = pd.DataFrame.from_records([statistics[item]])
        statistics_df.to_csv(path_or_buf=response, index=False, mode='a')

    comments.to_csv(path_or_buf=response, index=False, mode='a')
    participants.to_csv(path_or_buf=response, index=False, mode='a')

    # writer = csv.writer(response)
    # for cluster in clusters:
    #     writer.writerow({cluster.name + ' size: ' + str(cluster.size)})
    #     writer.writerow({''})
    #     table = pd.read_html(str(cluster.comment_table))[0]
    #     writer.writerow(list(participants))
    #     writer.writerows(table.values)

    return response


def generate_json(conversation, statistics, votes, comments, participants, clusters):
    response = HttpResponse(content_type='text/json')
    filename = 'filename={}.json'.format(conversation.title)
    response['Content-Disposition'] = 'attachment; {}'.format(filename)

    # Change participants property for ease of use
    statistics["participants"] = {"total": statistics["participants"]}

    for item in statistics:
        statistics_df = pd.DataFrame.from_records([statistics[item]])
        statistics_df.to_json(path_or_buf=response, force_ascii=False)
    comments.to_json(path_or_buf=response, force_ascii=False)
    participants.to_json(path_or_buf=response, force_ascii=False)
    return response


def generate_msgpack(conversation, statistics, votes, comments, participants, clusters):
    response = HttpResponse(content_type='text/msgpack')
    filename = 'filename={}.msgpack'.format(conversation.title)
    response['Content-Disposition'] = 'attachment; {}'.format(filename)

    for item in statistics:
        statistics_df = pd.DataFrame.from_records([statistics[item]])
        statistics_df.to_msgpack(path_or_buf=response, encoding='utf-8')
    comments.to_msgpack(path_or_buf=response, encoding='utf-8')
    participants.to_msgpack(path_or_buf=response)
    return response
