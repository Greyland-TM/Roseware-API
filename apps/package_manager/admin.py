from django.contrib import admin
from .models import ServicePackage, ServicePackageTemplate, PackagePlan


@admin.register(ServicePackageTemplate)
class ServicePackageTemplateAdmin(admin.ModelAdmin):
    list_display = [
        "related_app",
        "type",
        "cost",
        "requires_onboarding",
        "action",
        "error",
    ]

@admin.register(ServicePackage)
class ServicePackageAdmin(admin.ModelAdmin):
    list_display = [
        "customer",
        "related_app",
        "type",
        "cost",
        "is_active",
        "last_completed",
        "date_started",
        "next_scheduled",
        "action",
        "error",
    ]

@admin.register(PackagePlan)
class PackagePlanAdmin(admin.ModelAdmin):
    list_display = [
        "customer",
        "name",
        "status",
        "description",
        "billing_cycle",
        "pipedrive_id",
    ]
