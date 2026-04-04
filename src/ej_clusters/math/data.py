import logging
from collections import defaultdict, Counter

from sidekick import import_later

log = logging.getLogger("ej")
np = import_later("numpy")
models = import_later("..models", package=__name__)


#
# Cluster belonging fractions
#
def compute_cluster_affinities(
    votes, distance=lambda x, y: np.sum(np.abs(x - y))
):
    """
    Returns a dictionary mapping clusters to a list of affinities.

    Each affinity is another dictionary mapping clusters to the degree of
    affinity for the user in each other cluster.

    Args:
        votes (dataframe):
            A votes dataframe with users as rows and comments as columns. It
            must contain an extra column named 'cluster' indicating in which
            cluster each user is classified.

            Usually this data will come from a call to ``clusterization.clusters.votes_table()``
        distance (callable):
            Distance function.
    """
    votes = votes.copy()
    labels = votes["cluster"].copy()
    votes = (votes - votes.mean()) / (votes.std() + 1e-6)
    votes["cluster"] = labels

    centroids = votes.groupby("cluster").mean()
    clusters = votes.pop("cluster")

    tol = 1e-12
    shapes = defaultdict(
        lambda: {"intersections": defaultdict(float), "size": 0}
    )

    for k, x in zip(clusters.values, votes.values):
        centroid_k = centroids.loc[k].values
        coords = x - centroid_k
        distance_k = distance(x, centroid_k)
        shape = shapes[int(k)]

        for k_, centroid_k_ in enumerate((centroids - centroid_k).values):
            k_ = int(centroids.index[k_])

            # Check if vectors point to the same direction
            if k == k_:
                shape["size"] += 1
            elif np.sum(coords * centroid_k_) > 0:
                distance_k_ = distance(coords, centroid_k_)
                shape["intersections"][k_] += (
                    distance_k / (distance_k_ + tol) / 2
                )

    return dict(shapes)


def summarize_affinities(affinities):
    """
    Process the result of :func:`compute_cluster_affinities`
    and returns a list of summaries for each cluster/intersection. This data
    is exposed in the /api/v1/clusterizations/<id>/affinities/ as:

    >>> summarize_affinities(affinities)  # doctest: +SKIP
    [{'sets': [1, 2], 'size': 3.14},
     {'sets': [1],    'size': 42},
     {'sets': [2],    'size': 10}]

    """
    intersections = Counter()
    counts = Counter()

    for k, users in affinities.items():
        for user in users:
            for k_, frac in user.items():
                counts[k] += 1
                if k != k_:
                    intersections[k, k_] += frac

    for (k, k_), v in list(intersections.items()):
        if (k_, k) in intersections:
            if intersections[k_, k] > v:
                del intersections[k_, k]

    json = [{"sets": [k], "size": n} for k, n in counts.items()]
    json.extend({"sets": list(k), "size": n} for k, n in intersections.items())
    return json
