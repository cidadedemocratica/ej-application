from django.utils.translation import gettext_lazy as _
from rest_framework import serializers
from .models import User


class UsersSerializer(serializers.ModelSerializer):
    name = serializers.CharField(max_length=50, min_length=5, required=True)
    email = serializers.EmailField(required=True)
    password = serializers.CharField(
        required=True, write_only=True, style={"input_type": "password"}, max_length=128
    )
    password_confirm = serializers.CharField(
        required=True, write_only=True, style={"input_type": "password"}, max_length=128
    )
    secret_id = serializers.CharField(required=False, max_length=200)
    has_completed_registration = serializers.BooleanField(required=False, default=True)
    phone_number = serializers.CharField(required=False, max_length=200)

    class Meta:
        model = User
        fields = [
            "id",
            "name",
            "email",
            "password",
            "password_confirm",
            "secret_id",
            "has_completed_registration",
            "phone_number",
        ]

    def validate(self, data):
        if data["password"] != data["password_confirm"]:
            raise serializers.ValidationError(_("Passwords do not match"))
        return data

    def validate_email(self, data):
        if User.objects.filter(email=data).exists():
            raise serializers.ValidationError(_("Email already exists"))
        return data

    def validate_secret_id(self, data):
        if User.objects.filter(secret_id=data).exists():
            raise serializers.ValidationError(_("Secret ID already exists"))
        return data

    def create(self, validated_data):
        user = User(
            email=validated_data["email"],
            name=validated_data["name"],
            secret_id=User.encode_secret_id(validated_data.get("secret_id", None)),
            has_completed_registration=validated_data["has_completed_registration"],
        )
        user.set_password(validated_data["password"])

        # monkeypatching the user object to retrieve the phone_number during Profile creation.
        # In cases where the phone_number is available during user registration, we can send
        # it along other user fields.
        # The User profile is automatically created in create_user_profile method.
        if "phone_number" in validated_data:
            user.phone_number = validated_data["phone_number"]

        user.save()
        return user


class UserAuthSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)
    password = serializers.CharField(
        required=True, write_only=True, style={"input_type": "password"}
    )
