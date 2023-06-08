""" URLS for monday.com """
from django.urls import path
from .views import ProcessModayWebhook


# Wire up our API using automatic URL routing.
# Additionally, we include login URLs for the browsable API.
urlpatterns = [path("monday-webhook/", ProcessModayWebhook.as_view(), name="monday-webhook")]
