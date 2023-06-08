from knox.views import LogoutView
from django.urls import path, include
from .views import (
    LoginAPIView,
    CustomerAPIView,
    CreateCustomerAPIView
)

urlpatterns = [
    path("", include("knox.urls")),
    path("login", LoginAPIView.as_view()),
    path("logout", LogoutView.as_view(), name="knox_logout"),
    path('customer/', CustomerAPIView.as_view(), name='customer'),
    path('create-customer/', CreateCustomerAPIView.as_view(), name='create-customer')
]
