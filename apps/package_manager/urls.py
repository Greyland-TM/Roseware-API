""" URLS for package_manager """
from django.urls import path

from .views import PackagePlanView, ProfilePackage, ServicePackageTemplateView, ServicePackageView

# Wire up our API using automatic URL routing.
# Additionally, we include login URLs for the browsable API.
urlpatterns = [
    path("create/", ProfilePackage.as_view(), name="current-user"),
    path("service-package-template/", ServicePackageTemplateView.as_view(), name="service-package-template"),
    path("package-plan/", PackagePlanView.as_view(), name="package-plan"),
    path("service-package/", ServicePackageView.as_view(), name="service-package"),
]
