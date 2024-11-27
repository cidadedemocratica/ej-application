from numbers import Number

from sidekick import import_later

pd = import_later("pandas")


# ==============================================================================
# BASIC STATISTICAL FUNCTIONS

# noinspection PyIncorrectDocstring
def comment_statistics(
    votes,
    author="author",
    comment="comment",
    choice="choice",
    convergence=False,
    participation=False,
    ratios=False,
):
    """
    Return a dataframe with ['agree', 'disagree', 'skipped'] columns that counts
    the number of votes for each comment/choice with those given values.

    Args:
        votes (dataframe):
            A dataframe of votes with at the "author", "comment", and "choice"
            columns.
        author, comment, choice (str):
            Names for the "author", "comment", and "choice" columns in the
            votes dataset.
        convergence (bool):
            If True, appends a "convergence" column to the dataframe that
            measures the proportional difference between "agree" and "disagree"
            choices.
        participation (bool):
            If True, appends a "participation" column to the dataframe that
            measures how the ratio of participation of users in each comment
            (i.e., what is the fraction of total users that interacted with
            each comment).
        ratios (bool):
            If True, return agree, disagree and skipped columns as fractions
            of the total votes in the given comment.

    Notes:
        Input data usually comes from a call to vote_queryset.dataframe().
    """
    table = _make_table(votes, comment, author, choice)
    table.index.name = "comment"
    if participation:
        participation = len(votes[author].unique())
    return _statistics(
        table, convergence=convergence, participation=participation, ratios=ratios
    )


def votes_statistics(
    votes,
    author="author",
    comment="comment",
    choice="choice",
    convergence=False,
    participation=False,
    ratios=False,
):
    """
    Similar to :func:`comments_statistics`, but gathers information by user,
    rather than by comment. It accepts the same parameters.
    """
    table = _make_table(votes, author, comment, choice)
    table.index.name = "user"
    if participation:
        participation = len(votes[comment].unique())
    return _statistics(
        table, convergence=convergence, participation=participation, ratios=ratios
    )


def _make_table(votes, row, col, choice):
    """
    Common implementation to :func:`comment_statistics` and :func:`user_statistics`
    functions.
    """
    group = votes.groupby([row, choice])
    df = group.count()
    df.reset_index(inplace=True)
    if df.shape[0] == 0:
        return pd.DataFrame({-1: [], 0: [], 1: []})
    return df.pivot_table(index=row, columns=choice, values=col, fill_value=0)


def _statistics(table, convergence=False, ratios=False, participation=False):
    """
    Common implementation to :func:`comment_statistics` and :func:`user_statistics`
    functions.
    """
    # Fill empty columns and update their names.
    col_names = {1: "agree", -1: "disagree", 0: "skipped"}
    for col in col_names:
        if col not in table:
            table[col] = 0
    table.columns = [col_names[k] for k in table.columns]
    table = table[["agree", "disagree", "skipped"]].copy()

    # Adds additional columns
    if convergence:
        table["convergence"] = compute_convergence(table["agree"], table["disagree"])
    if participation is not False:
        table["participation"] = compute_participation(table, participation)

    if ratios:
        e = 1e-50
        data = table[["agree", "disagree", "skipped"]]
        norm = data.sum(axis=1).values
        norm = norm[:, None][:, [0, 0, 0]]  # Adopts the same shape of the dataframe
        data /= norm + e
        table[["agree", "disagree", "skipped"]] = data
    return table


def compute_convergence(n_agree, n_disagree):
    """
    Compute the fractional convergence coefficient
    """
    e = 1e-50
    return abs(n_agree - n_disagree) / (n_agree + n_disagree + e)


def compute_participation(
    df, n_users, agree="agree", disagree="disagree", skipped="skipped"
):
    """
    Compute the participation ratio column from the total number of users and a
    dataframe that have 'agree', 'disagree' and 'skipped' columns.
    """
    e = 1e-50
    return (df[agree] + df[disagree] + df[skipped]) / (n_users + e)


# ==============================================================================
# IMPUTATION


def imputation(data, method, keep_empty=True):
    """
    Performs simple imputation method in dataframe.

    Args:
        data (dataframe):
            Input data.

        method (str, number):
            Default imputation method for filling missing values. If not
            given, non-filled values become NaN.

            It accepts the following strategies:

            * numeric value: Uses the given value to fill missing data.
            * 'mean': Uses the mean vote value for each comment.
            * 'zero': Uses zero as a filling parameter.
        keep_empty (bool):
            If True (default), keep columns with empty elements.
    """
    if isinstance(method, Number):
        data = data.fillna(method)
    elif method == "zero":
        data = data.fillna(0)
    elif method == "mean":
        data.fillna(data.mean(), inplace=True)
    elif method is not None:
        raise ValueError(f"invalid imputation method: {method}")
    if not keep_empty:
        data.dropna("columns", inplace=True)
    return data
