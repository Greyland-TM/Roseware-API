from django.urls import path, include
from .views import BlogArticleView

urlpatterns = [
    path("blog-articles/", BlogArticleView.as_view())
]