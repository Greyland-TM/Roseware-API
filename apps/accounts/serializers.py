from django.contrib.auth import authenticate
from rest_framework import serializers
from apps.accounts.models import Customer, Employee, Organization, CustomUser
import logging

logger = logging.getLogger(__name__)

# CustomUser._meta.get_field("email")._unique = True

class EmployeeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Employee
        fields = (
            "id",
            "first_name",
            "last_name",
            "profile_picture",
            "bio",
            "role",
            "linkedin",
            "github",
            
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
            "beta_feature_flag"
        )
        
class OrganizationSerializer(serializers.ModelSerializer):
    model = Organization
    fields = ("name",)


from rest_framework.exceptions import ValidationError

class RegisterSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ("id", "email", "password", "first_name", "last_name")

    def validate(self, attrs):
        if CustomUser.objects.filter(email=attrs['email']).exists():
            raise ValidationError({'email': 'A user with that email already exists.'})
        return attrs

    def create(self, validated_data):
        try:
            user = CustomUser.objects.create_user(
                email=validated_data["email"],
                password=validated_data["password"],
                first_name=validated_data["first_name"],
                last_name=validated_data["last_name"],
            )
        except Exception as e:
            logger.error('Failed to make user: ', e)
        return user



class LoginSerializer(serializers.Serializer):
    email = serializers.CharField()
    password = serializers.CharField()

    def validate(self, data):
        user = authenticate(**data)
        if user and user.is_active:
            return user
        raise serializers.ValidationError("Incorrect Credentials")
