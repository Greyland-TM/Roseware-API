""" Package manager serializers """

from rest_framework import serializers

from .models import PackagePlan, ServicePackage, ServicePackageTemplate


class ServicePackageTemplateSerializer(serializers.ModelSerializer):
    """Serializer for service package templates"""

    class Meta:
        """Meta class for ServicePackageTemplate"""

        model = ServicePackageTemplate
        fields = ("id", "related_app", "description", "name", "type", "cost", "requires_onboarding")


class PackagePlanSerializer(serializers.ModelSerializer):
    """Serializer for package plans"""
    service_packages = serializers.SerializerMethodField()

    def get_service_packages(self, obj=None):
        """Serializing the service packages"""
        service_packages = ServicePackage.objects.filter(package_plan=obj)
        return ServicePackageSerializer(service_packages, many=True).data

    class Meta:
        """Meta class for PackagePlanSerializer"""

        model = PackagePlan
        fields = ("id", "name", "status", "type", "description", "billing_cycle", "service_packages")



# TODO - This serializer is broken, and not used anywhere
class ServicePackageSerializer(serializers.ModelSerializer):
    """Serializer for service packages"""

    class Meta:
        """Meta class for ServicePackageSerializer"""

        model = ServicePackage
        fields = (
            "id",
            "related_app",
            "type",
            "is_active",
            "cost",
            "quantity",
        )
