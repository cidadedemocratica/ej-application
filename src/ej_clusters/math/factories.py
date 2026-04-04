import matplotlib.pyplot as plt

from sidekick import import_later
from sklearn.decomposition import PCA, KernelPCA
from sklearn.manifold import (
    TSNE,
    Isomap,
    MDS,
    LocallyLinearEmbedding,
    SpectralEmbedding,
)
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import Imputer

pd = import_later("pandas")
np = import_later("numpy")
DEFAULT_ALPHA = 0.5


def random_clusterization(shape, n_comments, alpha=DEFAULT_ALPHA, missing=0.5):
    """
    Similar to random_cluster, but produces a full clusterization.

    First argument is either a list of cluster sizes.
    """
    # Fake data
    results = [
        random_cluster(n_users, n_comments, missing=missing, alpha=alpha)
        for n_users in shape
    ]
    votes = np.vstack([v for v, _ in results])
    centroids = np.vstack([c for _, c in results])
    return votes, centroids


def random_cluster(n_users, n_comments, alpha=DEFAULT_ALPHA, missing=0.25):
    """
    Return votes of a random cluster.

    Result is (votes, stereotypes) in which "votes" is an array of
    (size, n_comments) with vote data on cells and "stereotypes" is the location
    of the stereotype.
    """
    probs = np.random.dirichlet([alpha, alpha], size=n_comments)[:, 0]
    # votes = np.ones((n_users, n_comments), dtype='int8')
    # rand = np.random.uniform(size=(n_users, n_comments))
    # votes[rand > probs] = -1
    #
    # rand = np.random.uniform(size=(n_users, n_comments))
    # votes[rand < missing] = 0

    votes = np.vstack(
        [random_user(probs, missing=missing) for _ in range(n_users)]
    )

    # Fill-in again users who did not vote in anything
    for k, row in enumerate(votes):
        while (row == 0).all():
            row[:] = 1
            rand = np.random.uniform(size=n_comments)
            row[rand > probs] = -1

            rand = np.random.uniform(size=n_comments)
            row[rand < missing] = 0

    return votes, probs


def random_user(probs, missing=0.25):
    """
    Return a random user profile from probabilities.
    """
    rand = np.random.uniform(size=len(probs))
    user = np.ones(len(probs), dtype="int8")
    user[rand > probs] = -1

    rand = np.random.uniform(size=len(probs))
    user[rand < missing] = 0
    return user


def random_probs(n_options, alpha=DEFAULT_ALPHA):
    """
    Compute random probability distributions for each choice.
    """
    probs = np.random.dirichlet([alpha, alpha], size=n_options)[:, 0]
    skip_probs = (1 / 3) - abs(probs - 0.5)
    skip_probs = np.where(skip_probs > 0, skip_probs, 0)
    probs = np.array([probs, skip_probs, 1 - probs]).T
    probs /= probs.sum(axis=1)[:, None]
    return probs


def random_votes(sizes, n_comments, alpha=DEFAULT_ALPHA, missing=0.5):
    """
    Return a full votation based on clusters of the given sizes.
    """
    clusters = [
        random_cluster(size, n_comments, alpha, missing) for size in sizes
    ]
    data = np.vstack(clusters)
    return data


def remove_votes(votes, prob=0.5, gamma=2 * DEFAULT_ALPHA):
    """
    Remove a few votes from dataset.

    prob = mean of beta distribution = alpha / (2 * gamma)
    gamma = average alpha and beta parameters
    """
    votes = np.asarray(votes, dtype=float)
    n_users, n_comments = votes.shape

    alpha = prob * 2 * gamma
    beta = (1 - prob) * 2 * gamma
    e = 1e-25  # regularization constant
    profiles = np.random.beta(alpha + e, beta + e, size=n_users)

    for p, user_votes in zip(profiles, votes):
        remove = np.random.uniform(size=n_comments) < p
        user_votes[remove] = float("nan")
    return votes


def sizes_to_labels(sizes, values=None):
    """
    Convert cluster sizes to labels.

    >>> sizes_to_labels([1, 2, 3], 'abc')
    ['a', 'b', 'b', 'c', 'c', 'c']
    """
    if values is None:
        values = range(len(sizes))
    labels = []
    for size, label in zip(sizes, values):
        labels.extend([label] * size)
    return labels


def reduce_dimensionality(votes, method="pca", **kwargs):
    """
    Project dataset into 2 dimensions for better visualization.

    Return a pair of (transformed data, sklearn transformer instance).

    Methods:
    * 'pca': Principal component analysis, a classic ;)
    * 't-sne': Slow, but good at keeping clustering structures
    * 'mds': Tries to preserve the distances across the original and transformed spaces
    * 'isomap': *bad?*
    * 'lle': *bad?*
    * 'se': *bad?*
    """
    standard_methods = {
        "pca": (PCA, (2,), {}),
        "k-pca": (KernelPCA, (2,), {}),
        "t-sne": (TSNE, (2,), {}),
        "isomap": (Isomap, (2,), {}),
        "mds": (MDS, (2,), {}),
        "lle": (LocallyLinearEmbedding, (2,), {}),
        "se": (SpectralEmbedding, (2,), {}),
    }
    try:
        cls, args, kwargs = standard_methods[method]
    except KeyError:
        raise ValueError(f"invalid method: {method}")

    pipeline = Pipeline([("fill", Imputer()), ("reduce", cls(*args, *kwargs))])
    data = pipeline.fit_transform(votes)
    return data, pipeline


def show_votes(
    votes,
    method="pca",
    display=True,
    title=None,
    labels=None,
    legend=None,
    **kwargs,
):
    """
    Show votes dataset in a 2D plot.
    """

    data, _ = reduce_dimensionality(votes, method=method, **kwargs)
    if labels is not None:
        df = pd.DataFrame(data, columns=["x", "y"])
        df["label"] = labels
        for label, group in df.groupby("label"):
            plt.scatter(group.x, group.y, label=label)
        if legend is None:
            legend = True
    else:
        plt.scatter(*data.T)
    plt.title(title or f"Reduced votes ({method})")
    if legend:
        plt.legend()
    if display:
        plt.show()


def cluster_error(labels, true_labels):
    if len(labels) != len(true_labels):
        raise ValueError("two sets of labels must hve the same size")

    e = 1e-50  # regularization factor
    k = len(set(true_labels))
    pairs = set(zip(labels, true_labels))
    return (len(pairs) - k + e) / (len(labels) - k + e)
