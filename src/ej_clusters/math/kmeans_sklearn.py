from sklearn.cluster import KMeans
from sklearn.utils.validation import check_is_fitted

from .kmeans import (
    normalize_distance,
    normalize_aggregator,
    kmeans_stereotypes,
    compute_labels,
    np,
    compute_distance_matrix,
    vq,
)


class StereotypeKMeans(KMeans):
    """
    K-Means with stereotypes.

    Args:
        n_clusters (int):
            Number of returning clusters. The last "n_cluster" rows in the
            dataset are treated as stereotypes.
        max_iter (int):
            Maximum number of iterations
        distance (str or callable):
            Distance function (defaults to 'euclidean')
        aggregator (str or callable):
            Aggregator function used to form clusters (defaults to 'mean')
    """

    _fit_parameters = ("labels_", "cluster_centers_")

    # noinspection PyMissingConstructor
    def __init__(
        self, n_clusters=None, max_iter=20, distance=None, aggregator=None
    ):
        distance = normalize_distance(distance)
        aggregator = normalize_aggregator(aggregator)
        self.n_clusters = n_clusters
        self.max_iter = max_iter
        self.distance = distance
        self.aggregator = aggregator
        self._args = dict(
            max_iter=max_iter, distance=distance, aggregator=aggregator
        )

    # noinspection PyIncorrectDocstring
    def fit(self, X, y=None, sample_weight=None):  # noqa: N803
        """
        Compute k-means using stereotype initialization.

        Args:
            X (array[n_samples, n_features]):
                New data.
            y, sample_weight (ignored):
                not used, present here for API consistency by convention.
        """
        data = X[: -self.n_clusters]
        stereotypes = X[-self.n_clusters :]
        labels, centroids = kmeans_stereotypes(data, stereotypes, **self._args)
        stereotype_labels = compute_labels(
            stereotypes, centroids, distance=self.distance
        )
        self.labels_ = np.hstack([labels, stereotype_labels])  # noqa: N803
        self.cluster_centers_ = centroids  # noqa: N803
        return self

    def _transform(self, X):  # noqa: N803
        centers = self.cluster_centers_
        return compute_distance_matrix(X, centers, distance=self.distance)

    def predict(self, X, sample_weight=None):  # noqa: N803
        """
        Predict the closest cluster each sample in X belongs to.

        In the vector quantization literature, `cluster_centers_` is called
        the code book and each value returned by `predict` is the index of
        the closest code in the code book.

        Args:
            X (array[n_samples, n_features]):
                New data.
            sample_weight (ignored):
                not used, present here for API consistency by convention.

        Returns:
            labels (array[n_samples])
                Index of the cluster each sample belongs to.
        """
        check_is_fitted(self, "cluster_centers_")
        X = self._check_test_data(X)  # noqa: N806
        return compute_labels(X, self.cluster_centers_, self.distance)

    def score(self, X, y=None, sample_weight=None, squared=True):  # noqa: N803
        """
        Sum of all squared distances between samples and their respective
        clusters.

        Args:
            X (array[n_samples, n_features]):
                New data.
            y (ignored):
            sample_weight (ignored):
                Not used, present here for API consistency by convention.
            squared (bool):
                If False, do not square distances in the k-means objective.
                This is a more appropriate metric for L1 or other non-euclidean
                distances.

        Returns:
            score (float):
                Opposite of the value of X on the K-means objective.
        """
        check_is_fitted(self, "cluster_centers_")
        X = self._check_test_data(X)  # noqa: N806
        labels = self.predict(X)
        transform = (lambda x: x * x) if squared else (lambda x: x)
        return -vq(
            X,
            labels,
            self.cluster_centers_,
            distance=self.distance,
            transform=transform,
        )
