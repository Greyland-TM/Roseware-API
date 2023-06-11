# from datetime import datetime
# from rest_framework.decorators import authentication_classes, permission_classes
# import authentication_classes
from knox.auth import TokenAuthentication
from knox.models import AuthToken
from rest_framework import generics, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from .models import Customer, Employee
from .serializers import CustomerSerializer, LoginSerializer, UserSerializer
from apps.pipedrive.tasks import sync_pipedrive


class LoginAPIView(generics.GenericAPIView):
    serializer_class = LoginSerializer

    def post(self, request):
        try:
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            user = serializer.validated_data
            return Response(
                {
                    "user": UserSerializer(user, context=self.get_serializer_context()).data,
                    "token": AuthToken.objects.create(user)[1],
                }
            )
        except Exception as error:
            print(f"Error: {error}")
            return Response({"ok": False, "error": str(error)}, status=status.HTTP_400_BAD_REQUEST)

from rest_framework.permissions import AllowAny
from rest_framework.authentication import SessionAuthentication, BasicAuthentication

class CreateCustomerAPIView(APIView):
    """API view to create a customer"""

    serializer_class = UserSerializer
    permission_classes = [AllowAny]
    authentication_classes = [SessionAuthentication, BasicAuthentication]

    def post(self, request):
        """Create a new customer"""
        try:
            # Make sure the request has a first_name, last_name, email and phone
            required_fields = ["first_name", "last_name", "email", "phone"]
            missing_fields = [field for field in required_fields if field not in request.data]
            if missing_fields:
                missing_fields_str = ", ".join(missing_fields)
                error_message = f"Missing required fields: {missing_fields_str}"
                return Response({"ok": False, "error": error_message}, status=status.HTTP_400_BAD_REQUEST)

            # If type and password are not sent in request then save as defaults here...
            new_user_data = {
                "first_name": request.data.get("first_name", None),
                "last_name": request.data.get("last_name", None),
                "username": request.data.get("email", None),
                "email": request.data.get("email", None),
                # "phone": request.data.get("phone", None),
                "password": request.data.get("password", "markittemppass2023"),
            }

            # Now pass the 'data' dictionary to the serializer
            serializer = UserSerializer(data=new_user_data)
            serializer.is_valid(raise_exception=True)
            user = serializer.save()

            # Get the represantative to set as the default rep for the customer
            representative = Employee.objects.all().first()

            # Create the customer
            customer = Customer(
                user=user,
                rep=representative,
                phone=request.data["phone"],
            )
            customer.save()
            
            if customer.status == "lead":
                sync_pipedrive.delay(customer.pk, "create", "lead")
                
            return Response(
                {
                    "ok": True,
                    "new_customer": CustomerSerializer(customer).data,
                    "token": AuthToken.objects.create(user)[1],
                }
            )
        except Exception as error:
            print(f"*** Error 2: {error}")
            return Response({"ok": False, "error": str(error)}, status=status.HTTP_400_BAD_REQUEST)

class CustomerAPIView(APIView):
    """API view for customers"""

    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]
    authentication_classes = [TokenAuthentication]

    def get(self, request):
        """Get a customer by pk"""

        try:
            # Check if the user has an employee attribute before trying to access it
            user = request.user
            if not hasattr(user, 'employee') or not user.employee:

                # If not, and the pk to update is not the user's pk, return an error
                customer = Customer.objects.get(user=user)
                if customer.pk != request.GET["pk"]:
                    return Response(
                        {"ok": False, "error": "Not Authorized"},
                        status=status.HTTP_401_UNAUTHORIZED
                    )

            # Get the customer
            customer_pk = request.GET["pk"]
            if not customer_pk:
                customer_pk = customer.pk
            customer = Customer.objects.get(pk=customer_pk)
            return Response({"ok": True, "customer": CustomerSerializer(customer).data})
        except Exception as error:
            print(f"Error: {error}")
            return Response({"ok": False, "error": str(error)}, status=status.HTTP_400_BAD_REQUEST)

    def put(self, request):
        """Update a customer"""

        try:
            # Check if the user is an employee
            user = request.user
            if not hasattr(user, 'employee') or not user.employee:

                # If not, and the pk to update is not the user's pk, return an error
                customer = Customer.objects.get(user=user)
                if customer.pk != request.data["pk"]:
                    return Response(
                        {"ok": False, "error": "Not Authorized"},
                        status=status.HTTP_401_UNAUTHORIZED
                    )

            # Make sure the request has all the required fields
            required_fields = ["first_name", "last_name", "phone", "pk"]
            missing_fields = [field for field in required_fields if field not in request.data]
            if missing_fields:
                missing_fields_str = ", ".join(missing_fields)
                error_message = f"Missing required fields: {missing_fields_str}"
                return Response({"ok": False, "error": error_message}, status=status.HTTP_400_BAD_REQUEST)

            # Update the customer
            customer = Customer.objects.get(pk=request.data["pk"])
            if not customer:
                return Response({"ok": False, "error": "Customer not found"}, status=status.HTTP_400_BAD_REQUEST)

            customer.first_name = request.data["first_name"]
            customer.last_name = request.data["last_name"]
            customer.phone = request.data["phone"]
            customer.save()
            return Response({"ok": True, "customer": CustomerSerializer(customer).data}, status=status.HTTP_200_OK)

        except Exception as error:
            print(f"*** Error 2: {error}")
            return Response({"ok": False, "error": str(error)}, status=status.HTTP_400_BAD_REQUEST)
