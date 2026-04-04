from rest_framework import serializers
from rest_framework.reverse import reverse
from .models.clusterization import Clusterization
from .models.cluster import Cluster
from .models.stereotype import Stereotype
from ej.serializers import BaseApiSerializer


class ClusterSerializer(BaseApiSerializer):
    clusterization = serializers.StringRelatedField()
    links = serializers.SerializerMethodField()
    user_list = serializers.SerializerMethodField()
    positive_comments = serializers.SerializerMethodField()
    negative_comments = serializers.SerializerMethodField()

    class Meta:
        model = Cluster
        fields = [
            "links",
            "clusterization",
            "name",
            "description",
            "user_list",
            "positive_comments",
            "negative_comments",
        ]

    def get_links(self, obj):
        return {
            "clusterization": reverse(
                "v1-clusterizations-detail",
                args=[obj.id],
                request=self.context["request"],
            ),
        }

    def get_user_list(self, cluster):
        return list(cluster.users.all().values_list("id", flat=True))

    def get_positive_comments(self, cluster):
        top5_positive_comments = cluster.separate_comments()[0][0:5]
        return list(
            map(
                lambda comment: dict([(comment.agree, comment.content)]),
                top5_positive_comments,
            )
        )

    def get_negative_comments(self, cluster):
        top5_negative_comments = cluster.separate_comments()[1][0:5]
        return list(
            map(
                lambda comment: dict([(comment.disagree, comment.content)]),
                top5_negative_comments,
            )
        )


class ClusterizationSerializer(BaseApiSerializer):
    conversation = serializers.SlugRelatedField(
        read_only=True, slug_field="slug"
    )
    links = serializers.SerializerMethodField()

    class Meta:
        model = Clusterization
        fields = ["links", "conversation", "cluster_status"]

    def get_links(self, obj):
        return {
            "self": reverse(
                "v1-clusterizations-detail",
                args=[obj.id],
                request=self.context["request"],
            ),
            "clusters": reverse(
                "v1-clusterizations-clusters",
                args=[obj.id],
                request=self.context["request"],
            ),
            "affinities": reverse(
                "v1-clusterizations-affinities",
                args=[obj.id],
                request=self.context["request"],
            ),
            "stereotypes": reverse(
                "v1-clusterizations-stereotypes",
                args=[obj.id],
                request=self.context["request"],
            ),
            "conversation": reverse(
                "v1-conversations-detail",
                args=[obj.conversation.id],
                request=self.context["request"],
            ),
        }


class StereotypeSerializer(BaseApiSerializer):
    links = serializers.SerializerMethodField()
    owner = serializers.SlugRelatedField(read_only=True, slug_field="email")

    class Meta:
        model = Stereotype
        fields = ["links", "name", "description", "owner"]

    def get_links(self, obj):
        return {
            "owner": reverse(
                "v1-users-detail",
                args=[obj.owner.id],
                request=self.context["request"],
            ),
        }
