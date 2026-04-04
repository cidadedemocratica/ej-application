import pytest
from numpy.testing import assert_almost_equal, assert_equal
from sidekick import import_later

from ej_clusters.math import kmeans

np = import_later("numpy")

# A very easy dataset with k=2
STEREOTYPES = np.array([[1, 1, 1], [-1, -1, -1]], dtype=float)
DATA = np.array(
    [[1, 0, 1], [1, 1, 1], [0, 1, 1], [-1, 0, -1], [-1, -1, 0], [-1, -1, -1]],
    dtype=float,
)


class TestAuxiliaryMathFunctions:
    @pytest.fixture
    def a(self):
        return STEREOTYPES[0].copy()

    @pytest.fixture
    def b(self):
        return STEREOTYPES[1].copy()

    def test_euclidean_distance(self, a, b):
        assert kmeans.euclidean_distance(a, a) == 0
        assert kmeans.euclidean_distance(b, b) == 0
        assert_almost_equal(kmeans.euclidean_distance(a, b), np.sqrt(12))

    def test_l1_distance(self, a, b):
        assert kmeans.l1_distance(a, a) == 0
        assert kmeans.l1_distance(b, b) == 0
        assert kmeans.l1_distance(a, b) == 6.0

    def test_euclidean_distance_non_zero(self, a, b):
        assert kmeans.euclidean_distance_non_zero(a, a) == 0
        assert kmeans.euclidean_distance_non_zero(b, b) == 0
        assert_almost_equal(
            kmeans.euclidean_distance_non_zero(a, b), np.sqrt(12 / 3)
        )
        assert_almost_equal(
            kmeans.euclidean_distance_non_zero([0, 1, 0], [-1, -1, 0]), 2.0
        )

    def test_mean_aggregator(self):
        assert_almost_equal(kmeans.mean_aggregator(STEREOTYPES), [0, 0, 0])

    def test_compute_centroids(self):
        centroids = kmeans.compute_centroids(DATA, [0, 0, 0, 1, 1, 1], 2)
        expected = [[2 / 3, 2 / 3, 1], [-1, -2 / 3, -2 / 3]]
        assert_almost_equal(centroids, expected)


class TestKmeansWithStereotypes:
    def test_run_with_stereotypes(self):
        labels, centroids = kmeans.kmeans_stereotypes(DATA, STEREOTYPES)
        assert_equal(labels, [0, 0, 0, 1, 1, 1])

    def test_kmeans_convergence(self):
        # This dataset is so easy it converges in a single iteration!
        labels, clusters = kmeans.kmeans_stereotypes(
            DATA, STEREOTYPES, max_iter=1
        )
        assert_equal(labels, [0, 0, 0, 1, 1, 1])

    def test_kmeans_with_missing_data(self):
        distance = kmeans.euclidean_distance_non_zero
        labels, clusters = kmeans.kmeans_stereotypes(
            DATA, STEREOTYPES, distance=distance
        )
        assert_equal(labels, [0, 0, 0, 1, 1, 1])


class TestKmeans:
    def test_kmeans(self):
        labels, _centroids = kmeans.kmeans(DATA, 2, n_runs=5)
        labels = list(labels)

        # K-means is invariant by label permutations, hence we can always have two
        # different classifications
        assert labels == [0, 0, 0, 1, 1, 1] or labels == [1, 1, 1, 0, 0, 0]

    def test_kmeans_requires_k_gt_n(self):
        with pytest.raises(ValueError):
            kmeans.kmeans(DATA, len(DATA) + 1, n_runs=5)

    def test_trivial_classification_if_number_of_clusters_equal_to_number_of_samples(
        self,
    ):
        labels, clusters = kmeans.kmeans(DATA, len(DATA), n_runs=5)
        assert_equal(labels, range(len(DATA)))
        assert_equal(clusters, DATA)

    def test_kmeans_convergence(self):
        # If no guidance is given, convergence is unlikely to happen
        labels, clusters = kmeans.kmeans(DATA, 2, max_iter=1, n_runs=2)
        assert (labels != [0, 0, 0, 1, 1, 1]).any()
