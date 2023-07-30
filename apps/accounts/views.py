# from datetime import datetime
# from rest_framework.decorators import authentication_classes, permission_classes
# import authentication_classes
from knox.auth import TokenAuthentication
from knox.models import AuthToken
from rest_framework import generics, status
from rest_framework.authentication import (BasicAuthentication,
                                           SessionAuthentication)
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from knox.views import LogoutView as KnoxLogoutView

from apps.pipedrive.tasks import sync_pipedrive

from .models import Customer, Employee
from .serializers import (CustomerSerializer, LoginSerializer,
                          RegisterSerializer, UserSerializer)


class LoginAPIView(generics.GenericAPIView):
    serializer_class = LoginSerializer

    def post(self, request):
        try:
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            user = serializer.validated_data
            token = AuthToken.objects.create(user)[1]
            return Response( 
                {
                    "user": UserSerializer(user, context=self.get_serializer_context()).data,
                    "token": token,
                }
            )
        except Exception as error:
            print(f"Error logging in: {error}")
            return Response({"ok": False, "error": str(error)}, status=status.HTTP_400_BAD_REQUEST)

class LogoutView(KnoxLogoutView):
    """ I was having trouble with the knox logout view so I made my own """
    
    authentication_classes = [TokenAuthentication]

    def post(self, request, format=None):
        try:
            super().post(request, format=None)
            return Response({"ok": True, "message": "Successfully logged out."}, status=200)
        except Exception as error:
            print(f'Error logging out: {error}')
            return Response({"ok": False, "error": str(error)}, status=status.HTTP_400_BAD_REQUEST)



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

            password = request.data.get("password")
            # If type and password are not sent in request then save as defaults here...
            new_user_data = {
                "first_name": request.data.get("first_name", None),
                "last_name": request.data.get("last_name", None),
                "username": request.data.get("email", None),
                "email": request.data.get("email", None),
                "phone": request.data.get("phone", None),
                "password": password,
            }

            # Now pass the 'data' dictionary to the serializer
            serializer = RegisterSerializer(data=new_user_data)
            serializer.is_valid(raise_exception=True)
            user = serializer.save()

            # Get the represantative to set as the default rep for the customer
            representative = Employee.objects.all().first()
            
            # Check the request url for the customer pk. If it's there, thens set the owner to that customer, otherwise set it to the representative
            # The reason for this is so that later we can check if the customer is owned by the rep or the customer, and make the correct api requests.
            # If an employee is the owner then api keys will be used, if it is a customer then oauth will be used.
            customer_pk = request.GET.get('pk')
            if customer_pk is not None:
                customer = Customer.objects.get(pk=customer_pk)
                owner = customer.user
            else:
                owner = representative.user

            # Create the customer
            customer = Customer(
                user=user,
                owner=owner,
                rep=representative,
                phone=request.data["phone"],
            )
            customer.save()
            
            if customer.status == "lead":
                sync_pipedrive.delay(customer.pk, "create", "lead")
            ## TODO - Else create a customer
                
            login_seralizer = LoginSerializer(data={"username": user.username, "password": password})
            login_seralizer.is_valid(raise_exception=True)
            user = login_seralizer.validated_data
            token = AuthToken.objects.create(user)[1]
            return Response(
                {
                    "user": UserSerializer(user).data,
                    "token": token,
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
            
            try:
                customer = Customer.objects.get(user=user)
            except Customer.DoesNotExist:
                return Response({"error": "Customer does not exist"}, status=404)

            pk = request.GET.get("pk")
            if pk is None:
                return Response(
                    {"ok": True, "customer": CustomerSerializer(customer).data}
                )

            if not hasattr(user, 'employee') or not user.employee:
                # If not, and the pk to update is not the user's pk, return an error
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
