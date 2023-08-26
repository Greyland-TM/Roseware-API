from rest_framework import serializers
from .models import BlogArticle
from apps.accounts.models import Customer
from apps.accounts.serializers import CustomerSerializer, EmployeeSerializer

class BlogArticleSerializer(serializers.ModelSerializer):
    author_details = serializers.SerializerMethodField()

    class Meta:
        model = BlogArticle
        fields = ("id", "title", "description", "author_details", "created_at", "image", "body", "category")

    def get_author_details(self, obj):
        if isinstance(obj.author, Customer):  
            return CustomerSerializer(obj.author.customer).data
        else:
            return EmployeeSerializer(obj.author.employee).data