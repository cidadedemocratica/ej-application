import json
from urllib import request
from datetime import datetime
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from ej.permissions import (
    IsAuthor,
    IsAuthenticatedOnlyGetView,
    IsRandomCommentAndNotAuthenticated,
    IsSuperUser,
    IsAuthenticatedCreationView,
    IsViewRetrieve,
    ParticipantCanAddComment,
)
from ej.viewsets import RestAPIBaseViewSet
from ej_conversations.models import Conversation, Comment, Vote
from ej_conversations.serializers import (
    ConversationSerializer,
    CommentSerializer,
    PartialConversationSerializer,
    VoteSerializer,
    CommentSummarySerializer,
    ConversationCardDataSerializer,
)
from ej_dataviz.utils import votes_as_dataframe


class CommentViewSet(RestAPIBaseViewSet):
    queryset = Comment.objects.all()
    serializer_class = CommentSerializer
    permission_classes = [IsAuthenticated, ParticipantCanAddComment]

    def list(self, request):
        is_author = self.request.query_params.get("is_author", None)
        if request.user.is_superuser and not is_author:
            queryset = Comment.objects.all()
        else:
            queryset = Comment.objects.filter(author=request.user)

        if not is_author:
            serializer = self.get_serializer(queryset, many=True)
        else:
            serializer = self.filter_comment_by_status(queryset)
        return Response(serializer.data)

    def filter_comment_by_status(self, queryset):
        is_approved = self.request.query_params.get("is_approved", None)
        is_rejected = self.request.query_params.get("is_rejected", None)
        is_pending = self.request.query_params.get("is_pending", None)
        status = []

        if is_approved:
            status.append(Comment.STATUS.approved)
        if is_rejected:
            status.append(Comment.STATUS.rejected)
        if is_pending:
            status.append("pending")

        if status:
            queryset = queryset.filter(status__in=status)
        serializer = CommentSummarySerializer(
            queryset, many=True, context={"request": request}
        )
        return serializer


class VoteViewSet(RestAPIBaseViewSet):
    queryset = Vote.objects.all()
    serializer_class = VoteSerializer
    permission_classes = (
        IsAuthenticatedCreationView | IsAuthor | IsSuperUser | IsAdminUser,
    )


class ConversationViewSet(RestAPIBaseViewSet):
    queryset = Conversation.objects.all()
    serializer_class = ConversationSerializer
    permission_classes = (
        IsAuthenticatedOnlyGetView | IsViewRetrieve | IsRandomCommentAndNotAuthenticated,
    )

    def retrieve(self, request, pk):
        conversation = self.get_object()
        if request.user.is_superuser or conversation.author == request.user:
            return Response(self.get_serializer(conversation).data)

        response = PartialConversationSerializer(conversation)
        return Response(response.data)

    def list(self, request):
        queryset = Conversation.objects.all()
        is_promoted_queryset = queryset.filter(is_promoted=True)
        is_promoted = self.request.query_params.get("is_promoted", None)
        is_author = self.request.query_params.get("is_author", None)
        search_text = self.request.query_params.get("search_text", None)
        tags = request.GET.getlist("tags")

        if is_author:
            return Response(
                self.filter_conversation_by_current_user(
                    request, queryset, tags, search_text
                )
            )

        if tags:
            return Response(
                self.filter_conversation_by_tag(
                    request, is_promoted_queryset, tags, search_text
                )
            )

        if is_promoted:
            return Response(
                self.get_promoted_conversations(
                    request, is_promoted_queryset, search_text
                )
            )

        if not request.user.is_superuser:
            queryset = is_promoted_queryset
        serializer = self.get_serializer(queryset, many=True)

        return Response(serializer.data)

    @action(detail=True, url_path="vote-dataset")
    def vote_dataset(self, request, pk):
        conversation = self.get_object()
        response = conversation.votes.dataframe().to_dict(orient="list")
        return Response(response)

    @action(detail=True)
    def votes(self, request, pk):
        conversation = self.get_object()
        votes = conversation.votes
        if request.GET.get("startDate") and request.GET.get("endDate"):
            start_date = datetime.fromisoformat(request.GET.get("startDate"))
            end_date = datetime.fromisoformat(request.GET.get("endDate"))
            votes = conversation.votes.filter(
                created__gte=start_date, created__lte=end_date
            )
        votes_dataframe = votes_as_dataframe(votes)
        votes_dataframe.reset_index(inplace=True)
        votes_dataframe_as_json = votes_dataframe.to_json(orient="records")
        return Response(json.loads(votes_dataframe_as_json))

    @action(detail=True, url_path="user-statistics")
    def user_statistics(self, request, pk):
        conversation = self.get_object()
        response = request.user.profile.conversation_statistics(conversation)
        return Response(response)

    @action(detail=True, url_path="approved-comments")
    def approved_comments(self, request, pk):
        conversation = self.get_object()
        comments = conversation.comments.approved()
        serializer = CommentSerializer(comments, context={"request": request}, many=True)

        return Response(serializer.data)

    @action(detail=True, url_path="user-comments")
    def user_comments(self, request, pk):
        conversation = self.get_object()
        comments = conversation.comments.filter(author=request.user)
        serializer = CommentSerializer(comments, context={"request": request}, many=True)

        return Response(serializer.data)

    @action(detail=True, url_path="user-pending-comments")
    def user_pending_comments(self, request, pk):
        conversation = self.get_object()
        comments = conversation.comments.filter(status="pending", author=request.user)
        serializer = CommentSerializer(comments, context={"request": request}, many=True)

        return Response(serializer.data)

    """
    random_comment will returns an unvoted comment, but
    if the request has an id parameter, it will be used
    to find a specific unvoted comment.

    This behavior is necessary for the integration between
    the mail template and the opinion component tool.
    """

    @action(detail=True, url_path="random-comment")
    def random_comment(self, request, pk):
        conversation = self.get_object()

        comment: Comment = None
        if not request.user.is_authenticated:
            comment = conversation.approved_comments.first()
        else:
            comment_id = request.GET.get("id")
            if comment_id:
                comment = conversation.next_comment_with_id(request.user, comment_id)
            else:
                comment = conversation.next_comment(request.user)

        serializer = CommentSerializer(comment, context={"request": request})
        return Response(serializer.data)

    def filter_conversation_by_tag(
        self, request, is_promoted_queryset, tags, search_text
    ):
        request.user.profile.filtered_home_tag = True
        request.user.profile.save()
        queryset = is_promoted_queryset.filter(tags__name__in=tags).distinct()

        queryset = queryset.filter_by_text_and_tag(search_text)
        serializer = ConversationCardDataSerializer(
            queryset, many=True, context={"request": request}
        )
        return serializer.data

    def get_promoted_conversations(self, request, is_promoted_queryset, search_text):
        is_promoted_queryset = is_promoted_queryset.filter_by_text_and_tag(search_text)
        serializer = ConversationCardDataSerializer(
            is_promoted_queryset, many=True, context={"request": request}
        )
        return serializer.data

    def filter_conversation_by_current_user(self, request, queryset, tags, search_text):
        queryset = queryset.filter(author=request.user)
        if tags:
            queryset = queryset.filter(tags__name__in=tags).distinct()

        queryset = queryset.filter_by_text_and_tag(search_text)
        serializer = ConversationCardDataSerializer(
            queryset, many=True, context={"request": request}
        )
        return serializer.data


def delete_vote(request, vote):
    user = request.user

    if user.is_superuser:
        vote.delete()
    elif vote.author_id != user.id:
        raise PermissionError("cannot delete vote from another user")
    else:
        raise PermissionError("user is not allowed to delete votes")
