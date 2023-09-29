from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
# from knox.auth import TokenAuthentication
from .models import BlogArticle
from .serializers import BlogArticleSerializer
import logging
from apps.accounts.models import Customer, Employee
from django.contrib.auth.models import User

# Create your views here.
logger = logging.getLogger(__name__)


class BlogArticleView(APIView):
    """CRUD operations for service package templates"""

    def get(self, request):
        try:
            if "customer_pk" in request.GET:
                customer_pk = request.GET["customer_pk"]
                customer = Customer.objects.get(pk=customer_pk)
                blog_articles = BlogArticle.objects.filter(author=customer.user)
                serialized_data = BlogArticleSerializer(blog_articles, many=True).data
                logger.info(f"Serialized data: {serialized_data}")
                return Response({"ok": True, "blog_articles": serialized_data})

            if "employee_pk" in request.GET:
                employee_pk = request.GET["employee_pk"]
                employee = Employee.objects.get(pk=employee_pk)
                blog_articles = BlogArticle.objects.filter(author=employee.user)
                serialized_data = BlogArticleSerializer(blog_articles, many=True).data
                logger.info(f"Serialized data: {serialized_data}")
                return Response({"ok": True, "blog_articles": serialized_data})
            
            if "article_pk" in request.GET:
                article_pk = request.GET["article_pk"]
                article = BlogArticle.objects.get(pk=article_pk)
                serialized_data = BlogArticleSerializer(article).data
                logger.info(f"Serialized data: {serialized_data}")
                return Response({"ok": True, "blog_article": serialized_data})
            
            blog_articles = BlogArticle.objects.all()
            serialized_data = BlogArticleSerializer(blog_articles, many=True).data
            return Response({"ok": True, "blog_articles": serialized_data})
        except Exception as error:
            logger.exception(error)
            return Response({"ok": False, "message": "Something went wrong."})