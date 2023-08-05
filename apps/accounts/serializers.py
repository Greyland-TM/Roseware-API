from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from rest_framework import serializers
from apps.accounts.models import Customer, Employee, Organization

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
    package_plans = serializers.SerializerMethodField("get_package_plans")

    def get_rep(self, obj=None):
        return obj.first_name + " " + obj.last_name
    
    def get_package_plans(self, obj=None):
        from apps.package_manager.models import PackagePlan
        from apps.package_manager.serializers import PackagePlanSerializer
        package_plans = PackagePlan.objects.filter(customer=obj)
        return PackagePlanSerializer(package_plans, many=True).data

    class Meta:
        model = Customer
        fields = (
            "id",
            "profile_picture",
            "first_name",
            "last_name",
            "email",
            "phone",
            "status",
            "onboarding_date",
            "representative",
            "package_plans",
            "has_synced_pipedrive",
            "has_synced_stripe",
        )
        
class OrganizationSerializer(serializers.ModelSerializer):
    model = Organization
    fields = ("name",)


class UserSerializer(serializers.ModelSerializer):
    
    status = serializers.SerializerMethodField("get_customer_status")
    
    def get_customer_status(self, obj=None):
        from .models import Customer
        try:
            customer = Customer.objects.get(user=obj)
            return customer.status
        except Exception as error:
            print(f'Error getting customer status: {error}')
            return None
    
    class Meta:
        model = User
        fields = ("id", "username", "email", "first_name", "last_name", "password", "status")


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
