from knox.auth import TokenAuthentication
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.models import Customer

from .models import PackagePlan, ServicePackage, ServicePackageTemplate
from .serializers import (PackagePlanSerializer, ServicePackageSerializer,
                          ServicePackageTemplateSerializer)


class ServicePackageTemplateView(APIView):
    """CRUD operations for service package templates"""
    
    permission_classes = [IsAuthenticated]
    authentication_classes = [TokenAuthentication]

    def get(self, request):
        """Retrieve a service package template by pk"""
        try:
            # Employees Only
            user = request.user
            if not hasattr(user, "employee") or not user.employee:
                return Response({"ok": False, "error": "Not Authorized, Employees Only"}, status=status.HTTP_401_UNAUTHORIZED)

            template_pk = request.GET.get("pk", None)
            if not template_pk:
                return Response({"ok": False, "error": "pk not found in query params. Please add it and try again."}, status=status.HTTP_400_BAD_REQUEST)

            template = ServicePackageTemplate.objects.filter(pk=template_pk).first()
            if not template:
                return Response({"ok": False, "error": "Service Package Template not found"}, status=status.HTTP_404_NOT_FOUND)

            return Response({"ok": True, "package_template": ServicePackageTemplateSerializer(template).data}, status=status.HTTP_200_OK)

        except Exception as error:
            return Response({"ok": False, "error": error}, status=status.HTTP_400_BAD_REQUEST)

    def post(self, request):
        """Create a new service package template"""
        try:
            # Check that required fields are sent in the request
            required_fields = ["name", "description", "cost", "unit"]
            for field in required_fields:
                if field not in request.data:
                    return Response({"ok": False, "error": f"Missing required field: {field}"}, status=status.HTTP_400_BAD_REQUEST)

            # Employees Only
            user = request.user
            if not hasattr(user, "employee") or not user.employee:
                return Response({"ok": False, "error": "Not Authorized, Employees Only"}, status=status.HTTP_401_UNAUTHORIZED)

            # Create the new package template
            data = request.data
            new_package_template = ServicePackageTemplate(
                name=data["name"],
                description=data["description"],
                cost=data["cost"],
                unit=data["unit"]
            )

            # List of fields to assign from request data
            fields_to_assign = ["related_app", "type", "requires_onboarding"]

            # Iterate over the fields to assign and check if they exist in the request data before assigning them
            for field in fields_to_assign:
                if field in data:
                    setattr(new_package_template, field, data[field])

            new_package_template.save()
            return Response(
                {
                    "ok": True,
                    "service-package-template": ServicePackageTemplateSerializer(new_package_template).data
                }, 
                status=status.HTTP_200_OK
            )

        except Exception as error:
            return Response({"ok": False, "error": error}, status=status.HTTP_400_BAD_REQUEST)

    def put(self, request):
        """Update a service package template"""
        try:
            # Employees Only
            user = request.user
            if not hasattr(user, "employee") or not user.employee:
                return Response({"ok": False, "error": "Not Authorized, Employees Only"}, status=status.HTTP_401_UNAUTHORIZED)

            # Get the package template pk from the request
            package_template_pk = request.GET["pk"]
            package_template = ServicePackageTemplate.objects.filter(pk=package_template_pk).first()
            if not package_template:
                return Response({"ok": False, "error": "Service Package Template not found"}, status=status.HTTP_404_NOT_FOUND)

            # Update the required fields from the request data
            data = request.data
            package_template.name = data["name"]
            package_template.description = data["description"]
            package_template.cost = data["cost"]
            package_template.unit = data["unit"]

            # Update the optional fields from the request data
            fields_to_assign = ["related_app", "type", "requires_onboarding"]
            for field in fields_to_assign:
                if field in data:
                    setattr(package_template, field, data[field])

            # Save the updated package template
            package_template.save()
            return Response(
                {
                    "ok": True, 
                    "service-package-template": ServicePackageTemplateSerializer(package_template).data
                }, 
                status=status.HTTP_200_OK
            )
        except Exception as error:
            return Response({"ok": False, "error": error}, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request):
        """Request for deleting a package template"""
        try:
            # Employees Only
            user = request.user
            if not hasattr(user, "employee") or not user.employee:
                return Response({"ok": False, "error": "Not Authorized, Employees Only"}, status=status.HTTP_401_UNAUTHORIZED)

            # Get the package template pk from the request
            package_template_pk = request.GET["pk"]
            package_template = ServicePackageTemplate.objects.filter(pk=package_template_pk).first()
            if not package_template:
                return Response({"ok": False, "error": "Service Package Template not found"}, status=status.HTTP_404_NOT_FOUND)

            # Delete the package template
            package_template.delete()
            return Response({"ok": True}, status=status.HTTP_200_OK)
        except Exception as error:
            return Response({"ok": False, "error": error}, status=status.HTTP_400_BAD_REQUEST)


class PackagePlanView(APIView):
    """CRUD operations for package plans"""
    
    permission_classes = [IsAuthenticated]
    authentication_classes = [TokenAuthentication]

    def get(self, request):
        """Retrieve a package plan by pk"""
        try:
            # Get the package plan pk from the request
            package_plan_pk = request.GET["pk"]
            package_plan = PackagePlan.objects.filter(pk=package_plan_pk).first()

            # Check if request is from an employee
            user = request.user
            if not hasattr(user, "employee") or not user.employee:
                # Check if the request is coming from the owner of the package plan
                customer = Customer.objects.get(user=user)
                if customer != package_plan.customer:
                    return Response({"ok": False, "error": "Not Authorized"}, status=status.HTTP_401_UNAUTHORIZED)

            # Return an error if the plan doesnt exist
            if not package_plan:
                return Response({"ok": False, "error": "Package Plan Not Found"}, status=status.HTTP_404_NOT_FOUND)

            # Return the package plan
            return Response({"ok": True, "package_plan": PackagePlanSerializer(package_plan).data}, status=status.HTTP_200_OK)
        except Exception as error:
            return Response({"ok": False, "error": error}, status=status.HTTP_400_BAD_REQUEST)
    
    def post(self, request):
        """Create a new package plan"""
        try:
            # Get request data and set required / optional fields
            required_fields = ["name", "type", "customer_pk"]
            fields_to_assign = ["status", "description", "billing_cycle"]
            data = request.data

            # Set the customer
            user = request.user
            if not hasattr(user, "employee") or not user.employee:
                customer = user
            else:
                if "customer_pk" not in data:
                    return Response({"ok": False, "error": "You need to supply a customer_pk in the request body."}, status=status.HTTP_404_NOT_FOUND)
                customer_pk = data["customer_pk"]
                if not customer_pk:
                    return Response({"ok": False, "error": "Customer not found"}, status=status.HTTP_404_NOT_FOUND)
                customer = Customer.objects.filter(pk=customer_pk).first()

            # Check if the required fields are in the request data
            for field in required_fields:
                if field not in data:
                    return Response({"ok": False, "error": f"{field} is required"}, status=status.HTTP_400_BAD_REQUEST)

            # Create a new package plan with required fields
            package_plan = PackagePlan(
                customer=customer,
                name=data["name"],
                type=data["type"],
            )

            # Update the optional fields from the request data
            for field in fields_to_assign:
                if field in data:
                    setattr(package_plan, field, data[field])

            # Save and return the package plan
            package_plan.save()
            return Response({"ok": True, "package_plan": PackagePlanSerializer(package_plan).data}, status=status.HTTP_200_OK)
        except Exception as error:
            return Response({"ok": False, "error": error}, status=status.HTTP_400_BAD_REQUEST)

    def put(self, request):
        """Update a package plan"""
        try:
            # Get the package plan pk from the request
            package_plan_pk = request.GET["pk"]
            package_plan = PackagePlan.objects.filter(pk=package_plan_pk).first()

            # Check if request is from an employee
            user = request.user
            if not hasattr(user, "employee") or not user.employee:
                # Check if the request is coming from the owner of the package plan
                customer = Customer.objects.get(user=user)
                if customer != package_plan.customer:
                    return Response({"ok": False, "error": "Not Authorized"}, status=status.HTTP_401_UNAUTHORIZED)

            # Return an error if the plan doesnt exist
            if not package_plan:
                return Response({"ok": False, "error": "Package Plan Not Found"}, status=status.HTTP_404_NOT_FOUND)

            # Get request data and set available fields
            fields_to_assign = ["name", "type", "billing_cycle", "status", "description"]
            data = request.data

            # Update the optional fields from the request data
            for field in fields_to_assign:
                if field in data:
                    setattr(package_plan, field, data[field])

            # Save and return the package plan
            package_plan.save()

            return Response({"ok": True, 'package_plan': PackagePlanSerializer(package_plan).data}, status=status.HTTP_200_OK)

        except Exception as error:
            return Response({"ok": False, "error": error}, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request):
        """ Delete a package plan """
        try:
            # Get the package plan pk from the request
            package_plan_pk = request.GET["pk"]
            package_plan = PackagePlan.objects.filter(pk=package_plan_pk).first()

            # Check if request is from an employee
            user = request.user
            if not hasattr(user, "employee") or not user.employee:
                # Check if the request is coming from the owner of the package plan
                customer = Customer.objects.get(user=user)
                if customer != package_plan.customer:
                    return Response({"ok": False, "error": "Not Authorized"}, status=status.HTTP_401_UNAUTHORIZED)

            # Return an error if the plan doesnt exist
            if not package_plan:
                return Response({"ok": False, "error": "Package Plan Not Found"}, status=status.HTTP_404_NOT_FOUND)

            # Delete the package plan
            package_plan.delete()
            return Response({"ok": True}, status=status.HTTP_200_OK)
        except Exception as error:
            return Response({"ok": False, "error": error}, status=status.HTTP_400_BAD_REQUEST)

class ServicePackageView(APIView):
    """CRUD operations for service packages"""
    
    permission_classes = [IsAuthenticated]
    authentication_classes = [TokenAuthentication]

    def get(self, request):
        """Retrieve a service package by pk"""
        try:
            # Get the service package pk from the request
            service_package_pk = request.GET["pk"]
            service_package = ServicePackage.objects.filter(pk=service_package_pk).first()

            # Check if request is from an employee
            user = request.user
            if not hasattr(user, "employee") or not user.employee:
                # Check if the request is coming from the owner of the service package
                customer = Customer.objects.get(user=user)
                if customer != service_package.customer:
                    return Response({"ok": False, "error": "Not Authorized"}, status=status.HTTP_401_UNAUTHORIZED)

            # Return an error if the plan doesnt exist
            if not service_package:
                return Response({"ok": False, "error": "service package Not Found"}, status=status.HTTP_404_NOT_FOUND)

            # Return the service package
            return Response({"ok": True, "service_package": ServicePackageSerializer(service_package).data}, status=status.HTTP_200_OK)
        except Exception as error:
            return Response({"ok": False, "error": error}, status=status.HTTP_400_BAD_REQUEST)

    def post(self, request):
        """Create a new service package"""
        try:
            # Get request data and check for required fields
            data = request.data
            required_fields = ["package_plan_pk", "package_template_pk", "package_template_pk", "related_app", "type", "is_active", "cost", "quantity"]
            for field in required_fields:
                if field not in data:
                    return Response({"ok": False, "error": f"You need to supply a {field} in the request body."}, status=status.HTTP_404_NOT_FOUND)

            # Set the customer
            user = request.user
            if not hasattr(user, "employee") or not user.employee:
                customer = user
            else:
                if "customer_pk" not in data:
                    return Response({"ok": False, "error": "You need to supply a customer_pk in the request body."}, status=status.HTTP_404_NOT_FOUND)
                customer_pk = data["customer_pk"]
                if not customer_pk:
                    return Response({"ok": False, "error": "Customer not found"}, status=status.HTTP_404_NOT_FOUND)
                customer = Customer.objects.filter(pk=customer_pk).first()

            # Get the package plan and template
            package_plan_pk = data["package_plan_pk"]
            package_template_pk = data["package_template_pk"]
            package_plan = PackagePlan.objects.filter(pk=package_plan_pk).first()
            package_template = ServicePackageTemplate.objects.filter(pk=package_template_pk).first()

            # Return an error if the plan doesnt exist
            if not package_plan:
                return Response({"ok": False, "error": "Package Plan Not Found"}, status=status.HTTP_404_NOT_FOUND)

            # Return an error if the package template doesnt exist
            if not package_template:
                return Response({"ok": False, "error": "Package Template Not Found"}, status=status.HTTP_404_NOT_FOUND)

            # Create the service package
            service_package = ServicePackage(
                customer=customer,
                package_plan=package_plan,
                package_template=package_template,
                related_app=data["related_app"],
                type=data["type"],
                is_active=data["is_active"],
                cost=data["cost"],
                quantity=data["quantity"]
            )
            service_package.save()
            return Response({"ok": True, "service_package": ServicePackageSerializer(package_plan).data}, status=status.HTTP_200_OK)
        except Exception as error:
            return Response({"ok": False, "error": error}, status=status.HTTP_400_BAD_REQUEST)

    def put(self, request):
        """Update a service package"""
        # Get the service package pk from the request
        service_package_pk = request.GET["pk"]
        service_package = ServicePackage.objects.filter(pk=service_package_pk).first()

        # Check if request is from an employee
        user = request.user
        if not hasattr(user, "employee") or not user.employee:
            # Check if the request is coming from the owner of the service package
            customer = Customer.objects.get(user=user)
            if customer != service_package.customer:
                return Response({"ok": False, "error": "Not Authorized"}, status=status.HTTP_401_UNAUTHORIZED)

        # Return an error if the plan doesnt exist
        if not service_package:
            return Response({"ok": False, "error": "service package Not Found"}, status=status.HTTP_404_NOT_FOUND)
        
        # Update any field sent in the request body
        data = request.data
        fields_to_assign = ["related_app", "type", "is_active", "cost", "quantity"]
        for field in fields_to_assign:
            if field in data:
                setattr(service_package, field, data[field])
        
        # Save and return the service package
        service_package.save()
        return Response({"ok": True}, status=status.HTTP_200_OK)
    
    def delete(self, request):
        """Delete a service package"""
        # Get the service package pk from the request
        service_package_pk = request.GET["pk"]
        service_package = ServicePackage.objects.filter(pk=service_package_pk).first()

        # Check if request is from an employee
        user = request.user
        if not hasattr(user, "employee") or not user.employee:
            # Check if the request is coming from the owner of the service package
            customer = Customer.objects.get(user=user)
            if customer != service_package.customer:
                return Response({"ok": False, "error": "Not Authorized"}, status=status.HTTP_401_UNAUTHORIZED)

        # Return an error if the plan doesnt exist
        if not service_package:
            return Response({"ok": False, "error": "service package Not Found"}, status=status.HTTP_404_NOT_FOUND)
        
        # Delete the service package
        service_package.delete()
        return Response({"ok": True}, status=status.HTTP_200_OK)

class ProfilePackage(APIView):
    """CRUD operations for social media ads"""
    
    permission_classes = [IsAuthenticated]
    authentication_classes = [TokenAuthentication]

    def post(self, request):
        """Post request for making a new add"""
        packages = request.data["packages"]
        customer_pk = request.data["customer_pk"]
        print(packages, customer_pk)
        try:
            customer = Customer.objects.get(pk=customer_pk)
            new_package_plan = PackagePlan(
                customer=customer,
                name=packages["name"],
                status=packages["status"],
                description=packages["description"],
                billing_cycle="Subscription",
            )
            new_package_plan.save()
            print("new_package_plan: ", new_package_plan)
            for package in packages:
                print("package: ", package)
                package_template = ServicePackageTemplate.objects.filter(related_app=package["related_app"], type=package["type"])

                new_service_package = ServicePackage(
                    customer=customer,
                    package_plan=new_package_plan,
                    package_template=package_template,
                    related_app=package["related_app"],
                    type=package["type"],
                    cost=package_template.cost,
                    is_active=package["is_active"],
                    requires_onboarding=package["requires_onboarding"],
                )
                new_service_package.save()
            print("customer: ", customer)
        except Exception as error:
            print(f"\nError: {error}")

        return Response(status=status.HTTP_200_OK, data={"ok": True, "message": "Packages Created"})
