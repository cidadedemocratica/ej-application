import sidekick as sk
from sklearn import pipeline as pipeline_, preprocessing, decomposition

from .kmeans_sklearn import StereotypeKMeans


#
# Default pipeline
#
def clusterization_pipeline(whiten=False, distance=None, only_preprocess=False):
    """
    Define the main clusterization pipeline that starts with some vote_table().
    that should include some stereotype votes.
    """

    def make_pipeline(k):
        scaler = preprocessing.StandardScaler()
        whitener = optional_whitener(whiten)

        # Select clusterizer
        if only_preprocess:
            clusterization_method = identity_transformer
        else:
            clusterization_method = StereotypeKMeans(k, distance=distance)

        return pipeline(
            scale=scaler, whiten=whitener, clusterize=clusterization_method
        )

    return make_pipeline


#
# Utility methods
#
def pipeline(memory=None, **kwargs):
    """
    Helper function to declare pipelines that uses the fact that Python 3.6+
    collects kwargs in a ordered dictionary.
    """
    return pipeline_.Pipeline(list(kwargs.items()), memory=memory)


identity_transformer = preprocessing.FunctionTransformer(
    sk.identity, sk.identity, validate=True, accept_sparse=True
)


def optional_whitener(enable):
    """
    Select between a PCA-based whitener vs. no whitening at all.
    """
    if enable:
        return decomposition.PCA(whiten=True)
    else:
        return identity_transformer
