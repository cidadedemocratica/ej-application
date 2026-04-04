from rest_framework import serializers
from rest_framework.utils import model_meta
from rest_framework.serializers import raise_errors_on_nested_writes
import traceback


class BaseApiSerializer(serializers.HyperlinkedModelSerializer):
    # Django-boogie method
    # https://github.com/pencil-labs/django-boogie/blob/master/src/boogie/rest/serializers.py
    def create(self, validated_data):
        raise_errors_on_nested_writes("create", self, validated_data)
        request = self.context["request"]

        many_to_many = remove_many_to_many_relationships(
            self.Meta.model, validated_data
        )
        try:
            instance = self.get_instance(request, validated_data)
        except TypeError:
            tb = traceback.format_exc()
            msg = (
                "Got a `TypeError` when saving object. "
                "This may be because you have a writable field on the "
                "serializer class that is not a valid argument to the "
                "object constructor. You may need to make the field "
                "read-only, or register a save hook function to handle "
                "this correctly.\nOriginal exception was:\n %s" % tb
            )
            raise TypeError(msg)
        else:
            instance = self.save_hook(request, instance)

        if many_to_many:
            for field_name, value in many_to_many.items():
                field = getattr(instance, field_name)
                field.set(value)
        return instance

    # Django-boogie method
    # https://github.com/pencil-labs/django-boogie/blob/master/src/boogie/rest/serializers.py
    def update(self, instance, validated_data):
        raise_errors_on_nested_writes("update", self, validated_data)
        request = self.context["request"]
        info = model_meta.get_field_info(instance)

        for attr, value in validated_data.items():
            if attr in info.relations and info.relations[attr].to_many:
                field = getattr(instance, attr)
                field.set(value)
            else:
                setattr(instance, attr, value)

        return self.save_hook(request, instance)

    def save_hook(self, request, instance):
        instance.save()
        return instance

    def get_instance(self, request, validated_data):
        return self.Meta.model(**validated_data)


def remove_many_to_many_relationships(model_class, validated_data):
    # Remove many-to-many relationships from validated_data.
    # They are not valid arguments to the default `.create()` method,
    # as they require that the instance has already been saved.
    info = model_meta.get_field_info(model_class)
    many_to_many = {}
    for field_name, relation_info in info.relations.items():
        if relation_info.to_many and (field_name in validated_data):
            many_to_many[field_name] = validated_data.pop(field_name)
    return many_to_many
