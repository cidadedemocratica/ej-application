from django.core.paginator import PageNotAnInteger, EmptyPage
from django.apps import apps
from django.http import HttpResponse, Http404, JsonResponse
from typing import Callable

from django.shortcuts import get_object_or_404
from django.utils.translation import gettext_lazy as _, gettext as __
from sidekick import import_later
from django.conf import settings
from django.utils.text import slugify


from ej_clusters.models import Cluster
from .constants import EXPOSED_PROFILE_FIELDS
from .constants import *

from ej_conversations.utils import check_promoted

pd = import_later("pandas")
stop_words = import_later("stop_words")


class OrderByOptions:
    AGREEMENT = "0"
    DISAGREEMENT = "1"
    CONVERGENCE = "2"
    PARTICIPATION = "3"


def get_page(paginator, page):
    """
    Gets the comments from a specific page.
    """
    if int(page) < 1:
        page = 1
    if int(page) > paginator.num_pages:
        page = paginator.num_pages

    try:
        comments = paginator.page(page)
    except PageNotAnInteger:
        comments = paginator.page(1)
    except EmptyPage:
        comments = paginator.page(paginator.num_pages)

    return comments


def get_cluster_names(clusters):
    cluster_names = [cluster.name for cluster in clusters]
    return cluster_names


def add_group_column(comments_df, group_name):
    comments_df["group"] = group_name


def add_id_column(comments_df):
    comments_df["id"] = range(len(comments_df.index))


def get_comments_dataframe(comments, cluster_name):
    """
    Gets the comments dataframe from statistics_summary_dataframe and sets the
    group column for each comment row
    """
    df = comments.statistics_summary_dataframe(normalization=100)
    add_group_column(df, cluster_name)
    return df


def get_cluster_comments_df(cluster, cluster_name):
    """
    Gets the cluster comments dataframe from comments_statistics_summary_dataframe
    and sets the group column for each comment row.
    """
    df = cluster.comments_statistics_summary_dataframe(normalization=100)
    add_group_column(df, cluster_name)
    return df


def filter_comments_by_group(comments_df, clusters, cluster_filters):
    """
    Gets the conversation comments (comments_df) and cluster comments
    filtered by the group specified in cluster_filters.
    """
    for cluster in clusters:
        if cluster.name in cluster_filters:
            cluster_comments_df = get_cluster_comments_df(cluster, cluster.name)
            comments_df = comments_df.append(cluster_comments_df)

    if "general" not in cluster_filters:
        comments_df = comments_df[comments_df.group != ""]

    return comments_df


def sort_comments_df(comments_df, sort_by=OrderByOptions.AGREEMENT, sort_order="desc"):
    """
    Sort the comments dataframe by a column option (disagree, convergence, participation or agree).
    """
    ascending = False if sort_order == "desc" else True

    if sort_by == OrderByOptions.DISAGREEMENT:
        return comments_df.sort_values("disagree", ascending=ascending)
    elif sort_by == OrderByOptions.CONVERGENCE:
        return comments_df.sort_values("convergence", ascending=ascending)
    elif sort_by == OrderByOptions.PARTICIPATION:
        return comments_df.sort_values("participation", ascending=ascending)
    else:
        return comments_df.sort_values("agree", ascending=ascending)


def search_comments_df(comments_df, substring):
    """
    Filter the comments dataframe by the content column. It will be checked if the
    content has the substring variable.
    """
    return comments_df[comments_df.content.str.contains(substring)]


def get_cluster_main_comments(cluster):
    """
    Gets the comments that have the lower convergence, the greater agree and the
    greater disagree.
    """
    df = cluster.comments_statistics_summary_dataframe(normalization=100)

    if df.empty:
        return {
            "id": cluster.id,
            "cluster_name": cluster.name,
        }

    lower_convergence_df = df[df["convergence"] == df["convergence"].min()].head(1)
    greater_agree_df = df[df["agree"] == df["agree"].max()].head(1)
    greater_disagree_df = df[df["disagree"] == df["disagree"].max()].head(1)

    return {
        "id": cluster.id,
        "cluster_name": cluster.name,
        "lower_convergence": {
            "author": lower_convergence_df.get("author").item(),
            "content": lower_convergence_df.get("content").item(),
            "convergence_level": lower_convergence_df.get("convergence").item(),
        },
        "greater_agree": {
            "author": greater_agree_df.get("author").item(),
            "content": greater_agree_df.get("content").item(),
            "agree_level": greater_agree_df.get("agree").item(),
            "disagree_level": greater_agree_df.get("disagree").item(),
        },
        "greater_disagree": {
            "author": greater_disagree_df.get("author").item(),
            "content": greater_disagree_df.get("content").item(),
            "agree_level": greater_disagree_df.get("agree").item(),
            "disagree_level": greater_disagree_df.get("disagree").item(),
        },
    }


def get_cluster_or_404(cluster_id, conversation=None):
    """
    Return cluster and checks if cluster belongs to conversation
    """
    cluster = get_object_or_404(Cluster, id=cluster_id)
    if conversation is not None and cluster.clusterization.conversation_id != conversation.id:
        raise Http404
    return cluster


def get_clusters(conversation):
    # Force clusterization, when possible
    clusterization = getattr(conversation, "clusterization", None)
    if clusterization:
        clusterization.update_clusterization()
        clusters = clusterization.clusters.all()
    else:
        clusters = ()
    return clusters


def export_data(data: pd.DataFrame, fmt: str, filename: str, translate=True):
    """
    Prepare data response for file from dataframe.
    """
    response = HttpResponse(content_type=f"text/{fmt}")
    if translate:
        data = data.copy()
        data.columns = [__(x) for x in data.columns]
    response["Content-Disposition"] = f"attachment; filename={filename}.{fmt}"
    if fmt == "json":
        data.to_json(response, orient="records", date_format="iso")
    elif fmt == "csv":
        data.to_csv(response, index=False, mode="a", float_format="%.3f")
    elif fmt == "msgpack":
        data.to_msgpack(response, encoding="utf-8")
    else:
        raise ValueError(f"invalid format: {fmt}")
    return response


def get_user_data(conversation):
    df = conversation.users.statistics_summary_dataframe(
        extend_fields=("id", *EXPOSED_PROFILE_FIELDS), conversation=conversation
    )
    df = df[
        [
            "email",
            "id",
            "name",
            *EXPOSED_PROFILE_FIELDS,
            "agree",
            "disagree",
            "skipped",
            "convergence",
            "participation",
        ]
    ]
    df.columns = ["email", "user_id", *df.columns[2:]]
    return df


def comments_data_common(comments, votes, filename, fmt, clusters=None):
    df = comments.statistics_summary_dataframe(votes=votes)
    df = comments.extend_dataframe(df, "id", "author__email", "author__id", "created")
    if clusters:
        for cluster in clusters:
            df = cluster.concat_statistics_to_dataframe(df)

    # Adjust column names
    columns = [
        "content",
        "id",
        "author__email",
        "agree",
        "disagree",
        "skipped",
        "convergence",
        "participation",
        "group",
        "created",
    ]
    df = df[columns]
    df.columns = ["comment", "comment_id", "author", *columns[3:]]
    if not fmt:
        return df
    return export_data(df, fmt, filename)


def vote_data_common(votes, filename, fmt):
    """
    Common implementation for votes_data and votes_data_cluster
    """
    df = votes_as_dataframe(votes)
    return export_data(df, fmt, filename)


def votes_as_dataframe(votes):
    columns = (
        "author__email",
        "author__name",
        "author__id",
        "author__metadata__analytics_id",
        "author__metadata__mautic_id",
        "comment__content",
        "comment__id",
        "comment__conversation",
        "choice",
    )
    df = votes.dataframe(*columns)
    df.columns = (
        "email",
        "author",
        "author_id",
        "author__metadata__analytics_id",
        "author__metadata__mautic_id",
        "comment",
        "comment_id",
        "conversation_id",
        "choice",
    )
    votes_timestamps = list(map(lambda x: x[0].timestamp(), list(votes.values_list("created"))))
    df["created"] = votes_timestamps
    df.choice = list(map({-1: "disagree", 1: "agree", 0: "skip"}.get, df["choice"]))
    return df


def get_stop_words():
    lang = getattr(settings, "LANGUAGE_CODE", "en")
    lang = NORMALIZE_LANGUAGES.get(lang, lang)
    if lang in stop_words.AVAILABLE_LANGUAGES:
        return stop_words.get_stop_words(lang)

    pre_lang = lang.split("-")[0]
    pre_lang = NORMALIZE_LANGUAGES.get(pre_lang, pre_lang)
    if pre_lang in stop_words.AVAILABLE_LANGUAGES:
        return stop_words.get_stop_words(lang.split("-")[0])

    log.error("Could not find stop words for language {lang!r}. Using English.")
    return stop_words.get_stop_words("en")


def get_biggest_cluster_data(cluster, cluster_as_dataframe):
    """
    returns the biggest cluster and the most positive comment from it.
    """
    import math

    try:
        positive_comment_content = cluster_as_dataframe.sort_values("agree", ascending=False).iloc[0][
            "comment"
        ]
        positive_comment_percent = math.trunc(
            cluster_as_dataframe.sort_values("agree", ascending=False).iloc[0]["agree"] * 100
        )
        return {
            "name": cluster.name,
            "content": positive_comment_content,
            "percentage": positive_comment_percent,
        }
    except Exception as e:
        print(e)
    return {}


def conversation_has_stereotypes(clusterization):
    if clusterization and clusterization.exists():
        return clusterization.stereotypes().count() > 0
    return False


def get_biggest_cluster(clusterization):
    from django.db.models import Count, F

    if conversation_has_stereotypes(clusterization):
        clusters = clusterization.clusters().annotate(size=Count(F("users")))
        return clusters.order_by("-size").first()
    return None


def create_stereotype_coords(conversation, table, comments: list, transformer: Callable, kwargs: dict):
    if apps.is_installed("ej_clusters") and getattr(conversation, "clusterization", None):
        from ej_clusters.models import Stereotype

        labels = conversation.clusterization.clusters.all().dataframe("name", index="users")
        if labels.shape != (0, 0):
            table["cluster"] = labels.loc[labels.index.values != None]
            table["cluster"].fillna(__("*Unknown*"), inplace=True)
            kwargs["labels"] = labels

            # Stereotype votes
            stereotypes = conversation.clusters.all().stereotypes()
            names = dict(Stereotype.objects.values_list("id", "name"))
            votes_ = stereotypes.votes_table()
            missing_cols = set(comments) - set(votes_.columns)
            for col in missing_cols:
                votes_[col] = float("nan")
            votes_ = votes_[comments]
            points = transformer(votes_)

            for pk, (x, y) in zip(votes_.index, points):
                yield {
                    "name": names[pk],
                    "symbol": "circle",
                    "coord": [x, y, names[pk], None, None],
                    "label": {"show": True, "formatter": names[pk], "color": "black"},
                    "itemStyle": {"opacity": 0.75, "color": "rgba(180, 180, 180, 0.33)"},
                    "tooltip": {"formatter": _("{} persona").format(names[pk])},
                }


def format_echarts_option(data, user_coords, stereotype_coords, extra_fields: list, labels=None):
    """
    Format option JSON for echarts.
    """
    visual_map = [
        {"dimension": n, **FIELD_DATA[f]["visual_map"]} for n, f in enumerate(extra_fields[1:], 3)
    ]
    if labels is not None:
        clusters = [*pd.unique(labels.values.flat), _("*Unknown*")]
        visual_map.append(
            {
                **PIECEWISE_OPTIONS,
                "dimension": len(visual_map) + 3,
                "categories": clusters,
                "inRange": {"color": COLORS[: len(clusters)]},
            }
        )

    axis_opts = {"axisTick": {"show": False}, "axisLabel": {"show": False}}
    return JsonResponse(
        {
            "option": {
                "tooltip": {
                    "showDelay": 0,
                    "axisPointer": {
                        "show": True,
                        "type": "cross",
                        "lineStyle": {"type": "dashed", "width": 1},
                    },
                },
                "xAxis": axis_opts,
                "yAxis": axis_opts,
                "series": [
                    {
                        "type": "scatter",
                        "name": _("PCA data"),
                        "symbolSize": 18,
                        "markPoint": {
                            "data": [
                                {
                                    "name": _("You!"),
                                    "coord": [*user_coords, _("You!"), None, None],
                                    "label": {"show": True, "formatter": _("You!")},
                                    "itemStyle": {"color": "black"},
                                    "tooltip": {"formatter": _("You!")},
                                },
                                *stereotype_coords,
                            ]
                        },
                        "data": data.values.tolist(),
                    }
                ],
                "grid": {"left": 10, "right": 10, "top": 10, "bottom": 30},
            },
            "visualMap": visual_map,
        }
    )


def clusters(request, conversation):
    """
    Returns the cluster data as json format to render groups on frontend.
    """

    clusterization = getattr(conversation, "clusterization", None)
    if clusterization:
        clusters_data = clusterization.get_shape_data(request.user)
        return clusters_data.get("json_data")
    return None


def get_dashboard_biggest_cluster(request, conversation, clusterization):
    biggest_cluster = get_biggest_cluster(clusterization)
    if biggest_cluster:
        biggest_cluster_df = comments_data_cluster(request, conversation, None, biggest_cluster.id)
        return get_biggest_cluster_data(biggest_cluster, biggest_cluster_df)
    return {}


def comments_data_cluster(request, conversation, fmt, cluster_id, **kwargs):
    check_promoted(conversation, request)
    cluster = get_cluster_or_404(cluster_id, conversation)
    filename = conversation.slug + f"-{slugify(cluster.name)}-comments"
    return comments_data_common(conversation.comments, cluster.votes, filename, fmt)
