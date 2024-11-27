"""
K-means clustering.

This module has no dependency on EJ and will stay here for a while.
Once the API stabilizes, it will be implemented in Cython and will move to an
external package.
"""
import random

from sidekick import import_later

np = import_later("numpy")


def kmeans(data, k, n_runs=10, **kwargs):
    """
    Run kmeans n_runs times and returns the (labels, centroids) for the best
    result.

    Args:
        data: 2D input data of (samples, features)
        k (int): number of returning clusters
        n_runs (int): number of parallel runs

    Return:
        labels: an 1D array of labels for each data point
        centroids: [k, features] array for each centroid

    See also:
        It accepts all keyword arguments of the :func:`kmeans_single` function.
    """
    distance = kwargs.get("distance")

    def get_objective(x):
        return vq(data, *x, distance=distance)

    return worker(n_runs, get_objective, kmeans_run, data, k, **kwargs)


def worker(nruns, objective, func, *args, **kwargs):
    """
    Worker function: runs func(*args, **kwargs) nruns times and return the
    result with the largest value for the objective function.
    """
    # Use threads in the future?
    results = [func(*args, **kwargs) for _ in range(nruns)]
    return max(results, key=objective)


def kmeans_stereotypes(data, stereotypes, max_iter=20, distance=None, aggregator=None):
    """
    Implements k-means clustering with defined stereotypes.

    Stereotypes have two roles:

    * They guide the clustering procedure by providing a direction for each
      cluster.
    * They serve as a initial guide that removes the requirement of having
      multiple parallel runs of the algorithm.

    Args:
        data: input data of (samples, features)
        stereotypes: average feature set for each stereotype (k, features)
        max_iter: maximum number of iterations
        distance: distance function (defaults to 'euclidean')
        aggregator: aggregator function used (defaults to 'mean')

    Returns:
        Two arrays of (labels, centroids)
    """
    k = len(stereotypes)
    data = np.asarray(data)
    data_ext = np.vstack([data, stereotypes])
    labels_extra = np.arange(k, dtype=int)
    stereotypes = np.asarray(stereotypes)
    centroids = stereotypes.copy()
    labels = np.random.randint(0, k, size=len(data))

    for i in range(max_iter):
        labels_ = compute_labels(data, centroids, distance)
        if (labels_ == labels).all():
            return labels_, centroids
        labels_ext = np.append(labels_, labels_extra)
        centroids = compute_centroids(data_ext, labels_ext, k, aggregator)
        labels = labels_
    return labels, centroids


def kmeans_run(
    data, k: int, max_iter=10, init_centroids=None, distance=None, aggregator=None
):
    """
    Compute a single k-means run with at most max_iter iterations.

    Args:
        data:
            2D input data of (samples, features)
        k:
            number of returning clusters
        init_centroids (callable):
            control centroid initialization (defaults to :func:`init_kmeanspp`)
        distance (callable):
            distance function (defaults to :func:`euclidean_distance`)
        aggregator:
            aggregator function that computes clusters from samples
            (defaults to :func:`mean_aggregator`)

    Returns:
        Two arrays of (labels, centroids)
    """
    init_centroids = init_centroids or init_kmeanspp
    distance = distance or euclidean_distance
    data = np.asarray(data)

    centroids = init_centroids(data, k)
    labels = np.random.randint(0, k, size=len(data))
    for i in range(max_iter):
        labels_ = compute_labels(data, centroids, distance)
        if (labels_ == labels).all():
            return labels_, centroids
        centroids = compute_centroids(data, labels_, k, aggregator)
        labels = labels_
    return labels, centroids


def init_kmeanspp(data, k):
    """
    Uses Kmeans++ strategy for initializing centroids: just pick k random
    different points.
    """
    n = len(data)

    # Pick indexes
    if k == n:
        selected = range(n)
    elif k > n:
        raise ValueError(f"we need at least {n} samples in the dataset")
    else:
        selected = set()
        while len(selected) < n:
            selected.add(random.randrange(0, n))

    return np.array([data[i] for i in selected])


def compute_labels(data, centroids, distance=None):
    """
    Label each data point to its closest centroid.

    Args:
        data:
            2D input data of (samples, features)
        centroids:
            2D array of centroids (k, features)
        distance:
            the distance function (defaults to Euclidean distance)
    """
    return compute_distance_matrix(data, centroids, distance).argmin(axis=1)


def compute_distance_matrix(data, centroids, distance=None):
    """
    Return matrix of distances of each data element from each centroid.

    Args:
        data:
            2D input data of (samples, features)
        centroids:
            2D array of centroids (k, features)
        distance:
            the distance function (defaults to Euclidean distance)
    """
    data = np.asarray(data)
    centroids = np.asarray(centroids)

    n_samples, n_features = data.shape
    k = len(centroids)
    distance = distance or euclidean_distance
    distances = np.empty([n_samples, k])
    for i, sample in enumerate(data):
        for j, centroid in enumerate(centroids):
            distances[i, j] = distance(sample, centroid)
    return distances


def compute_centroids(data, labels, k, aggregator=None):
    """
    Compute centroids from data and labels.

    Args:
        data:
            2D input data of (samples, features)
        labels:
            1D array with labels for each sample point.
        aggregator:
            aggregation function that receives a sub-sample and return the
            corresponding centroid.
    """
    aggregator = aggregator or mean_aggregator
    labels = np.asarray(labels)
    data = np.asarray(data)

    return np.array([aggregator(data[labels == k_]) for k_ in range(k)])


#
# Distance functions
#
# TODO: convert to functions at sklearn.metrics
def euclidean_distance(x, y):
    """
    Euclidean distance between two arrays.
    """
    x, y = np.asarray(x), np.asarray(y)
    diff = x - y
    diff *= diff
    return np.sqrt(np.sum(diff))


def euclidean_distance_non_zero(x, y):
    """
    Euclidean distance between two arrays ignoring components that have zeros.

    Squared distance is normalized by the number of non-zero components. The
    rationale is that zero represents missing data and should be ignored from
    computation.
    """
    x, y = np.asarray(x), np.asarray(y)
    zeros = (x == 0) | (y == 0)
    non_zero = len(x) - zeros.sum()
    diff = np.where(zeros, 0, x - y)
    diff *= diff
    return np.sqrt(np.sum(diff) / non_zero)


def euclidean_distance_finite(x, y):
    """
    Euclidean distance between two arrays ignoring NaN components.
    """
    x, y = np.asarray(x), np.asarray(y)
    not_null = np.isfinite(x) & np.isfinite(y)
    diff = np.where(not_null, x - y, 0)
    diff *= diff
    return np.sqrt(np.sum(diff) / len(not_null))


def l1_distance(x, y):
    """
    L1 (Manhattan/cab-driver) distance between two arrays.
    """
    return np.sum(np.abs(x - y))


DISTANCE_MAP = {
    None: euclidean_distance,
    "euclidean": euclidean_distance,
    "euclidean-non-zero": euclidean_distance_non_zero,
    "euclidiean-finite": euclidean_distance_finite,
    "l1": l1_distance,
    "l2": euclidean_distance,
}


def normalize_distance(value):
    """
    Normalizes distance value to a callable from user input.
    """
    if callable(value):
        return value
    try:
        return DISTANCE_MAP[value]
    except KeyError:
        raise ValueError(f"invalid distance: {value}")


def squared(x):
    return x * x


def vq(data, labels, centroids, distance=None, transform=squared):
    """
    Return the variation coefficient of data.
    """
    distance = distance or euclidean_distance
    return sum(
        sum(transform(distance(centroid, sample)) for sample in data[labels == k])
        for k, centroid in enumerate(centroids)
    )


#
# Aggregation functions
#
def mean_aggregator(data):
    """
    Return the mean value of a cluster.
    """
    return data.mean(axis=0)


def normalize_aggregator(value):
    if callable(value):
        return value
    elif value in ("mean", None):
        return mean_aggregator
    else:
        raise ValueError(f"invalid aggregator: {value}")
