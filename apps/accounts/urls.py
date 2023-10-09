from knox.views import LogoutView
from django.urls import path, include
from .views import (
    LoginAPIView,
    LogoutView,
    CustomerAPIView,
    CreateCustomerAPIView,
    OrganizationsView,
)

urlpatterns = [
    path("login/", LoginAPIView.as_view()),
    path('logout', LogoutView.as_view(), name='logout'),
    path('customer/', CustomerAPIView.as_view(), name='customer'),
    path('create-customer/', CreateCustomerAPIView.as_view(), name='create-customer'),
    path("organizations/", OrganizationsView.as_view(), name="organizations"),
]
