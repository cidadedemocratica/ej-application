from numbers import Number

from boogie.models import QuerySet

from ..math import imputation


class VoteQuerySet(QuerySet):
    """
    A table of votes.
    """

    def votes(self):
        return self

    def dataframe(self, *fields, index=None, verbose=False):
        if not fields:
            fields = ("author", "comment", "choice")
        return super().dataframe(*fields, index=index, verbose=verbose)

    def votes_table(self, data_imputation=None):
        """
        Return a dataframe with the default representation of vote data in the
        EJ platform.

        Args:
            data_imputation (str):
                Default imputation method for filling missing values. If not
                given, non-filled values become NaN.

                It accepts the following strategies:

                * 'mean': Uses the mean vote value for each comment.
                * 'zero': Uses zero as a filling parameter.
                * numeric value: Uses the given value to fill missing data.

        """
        if data_imputation == "zero":
            data_imputation = 0

        if isinstance(data_imputation, Number):
            return self.pivot_table(
                "author", "comment", "choice", fill_value=data_imputation
            )
        else:
            data = self.pivot_table("author", "comment", "choice")
            return imputation(data, data_imputation)
