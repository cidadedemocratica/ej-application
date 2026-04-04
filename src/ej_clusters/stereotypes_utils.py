def stereotype_vote_information(
    stereotype,
    clusterization,
    conversation,
    order_option=1,
    order_direction="-",
):
    if stereotype:
        comments = conversation.comments.approved()

        # Mark stereotypes with information about votes
        stereotype_votes = clusterization.stereotype_votes.filter(
            author=stereotype
        )

        voted = set(vote.comment for vote in stereotype_votes)
        stereotype.non_voted_comments = [x for x in comments if x not in voted]
        stereotype.given_votes = stereotype_votes

        return stereotype
