from rest_framework import serializers

from .models import Job


class JobSerializer(serializers.HyperlinkedModelSerializer):
    created_at = serializers.DateTimeField(format="%d-%m-%Y %H:%M")
    updated_at = serializers.DateTimeField(format="%d-%m-%Y %H:%M")

    class Meta:
        model = Job
        fields = ('id', 'url', 'result', 'type', 'status', 'conversation',
                  'created_at', 'updated_at',)
