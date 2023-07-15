from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from rest_framework import serializers

from apps.accounts.models import Customer, Employee

User._meta.get_field("email")._unique = True

class EmployeeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Employee
        fields = (
            "id",
            "first_name",
            "last_name"
        )

class CustomerSerializer(serializers.ModelSerializer):
    representative = serializers.SerializerMethodField("get_rep")

    def get_rep(self, obj=None):
        return obj.first_name + " " + obj.last_name

    class Meta:
        model = Customer
        fields = (
            "id",
            "first_name",
            "last_name",
            "email",
            "phone",
            "status",
            "onboarding_date",
            "representative",
        )


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("id", "username", "email", "first_name", "last_name", "password")


class RegisterSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("id", "username", "email", "password", "first_name", "last_name")

    def create(self, validated_data):
        try:
            user = User.objects.create_user(
                username=validated_data["username"],
                email=validated_data["email"],
                password=validated_data["password"],
                first_name=validated_data["first_name"],
                last_name=validated_data["last_name"],
            )
        except Exception as e:
            print('Failed to make user: ', e)
        return user


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField()

    def validate(self, data):
        user = authenticate(**data)
        if user and user.is_active:
            return user
        raise serializers.ValidationError("Incorrect Credentials")
