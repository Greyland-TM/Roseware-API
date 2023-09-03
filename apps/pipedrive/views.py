import os
import json
import time
import stripe
import requests
from roseware.utils import make_logger
from django.db.models import Q
from rest_framework import status
from rest_framework.views import APIView
from knox.auth import TokenAuthentication
from decimal import ROUND_HALF_UP, Decimal
from rest_framework.response import Response
from apps.stripe.models import StripeSubscription
from apps.stripe.utils import setup_payment_details
from rest_framework.permissions import IsAuthenticated
from django.contrib.auth.models import User
from apps.accounts.custom_auth import WebhookAuthentication
from apps.accounts.models import Customer, Employee, OngoingSync, Toggles
from apps.accounts.serializers import CustomerSerializer, RegisterSerializer
from apps.package_manager.models import (
    PackagePlan,
    ServicePackage,
    ServicePackageTemplate,
)
from django.core.cache import cache
from .utils import (
    create_pipedrive_stripe_url_fields,
    create_pipedrive_type_fields,
    create_pipedrive_webhooks,
    set_pipedrive_keys,
)

logger = make_logger(__name__)


class PipedriveOauth(APIView):
    """
    This view will recieve a code from an oauth redirect from pipedrive.
    The code will be used to get an access token, which will be stored with amazon secretcs manager.
    """

    permission_classes = [IsAuthenticated]
    authentication_classes = [TokenAuthentication]

    def post(self, request):
        try:
            # Set base variables
            user = request.user
            code = request.data.get("code")
            customer = Customer.objects.get(user=user)
            frontend_url = os.environ.get("FRONTEND_URL")
            print('frontend_url: ', frontend_url)
            client_id = os.environ.get("PIPEDRIVE_CLIENT_ID")
            client_secret = os.environ.get("PIPEDRIVE_CLIENT_SECRET")

            # Get the customers Oauth tokens from pipedrive
            url = "https://oauth.pipedrive.com/oauth/token"
            payload = {
                "grant_type": "authorization_code",
                "code": code,
                "client_id": client_id,
                "client_secret": client_secret,
                "redirect_uri": f"{frontend_url}/dashboard/integrations",
            }
            response = requests.post(url, data=payload)
            data = response.json()

            # Check if the response was successful and set the access and refresh tokens
            if "success" in data and not data["success"]:
                logger.error(f"Failed to get Oauth tokens from Pipedrive. {data}")
                return Response(
                    {"ok": False, "message": "Error getting access token."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            else:
                access_token = data["access_token"]
                refresh_token = data["refresh_token"]
                set_pipedrive_keys(customer.pk, access_token, refresh_token)

            piprdrive_api_url = data["api_domain"]

            # Get the users Pipedrive id and save it to the customer
            url = "https://api.pipedrive.com/v1/users/me"
            headers = {"Authorization": f"Bearer {access_token}"}
            response = requests.get(url, headers=headers)
            pipedrive_user_id = response.json()["data"]["id"]
            customer.pipedrive_user_id = pipedrive_user_id
            customer.piprdrive_api_url = piprdrive_api_url
            customer.has_synced_pipedrive = True
            customer.save()

            employee = Employee.objects.all().first()
            print("\nNEW PACKAGE PLAN: ", customer, employee)

            # Get or create The Package Plan
            try:
                print(f'Check all the package plan data: {employee.user}, {customer}, {customer.first_name} {customer.last_name} - Deal')
                package_plan, created = PackagePlan.objects.get_or_create(
                    owner=employee.user,
                    customer=customer,
                    name=f"{customer.first_name} {customer.last_name} - Deal",
                    defaults={"status": "active"},
                )
                package_template = ServicePackageTemplate.objects.filter(
                    name="Roseware - Pipedrive Stripe Sync"
                ).first()
            except Exception as e:
                print(e)
            if created:
                setup_payment_details(
                    customer=customer,
                    payment_details={
                        "card_number": "4242424242424242",
                        "expiry_month": "01",
                        "expiry_year": "2025",
                        "cvc": "123",
                    },
                    package_plan=package_plan,
                )

                service_package = ServicePackage.objects.get_or_create(
                    customer=customer,
                    package_template=package_template,
                    package_plan=package_plan,
                    cost=package_template.cost,
                )

                if not service_package:
                    return Response(
                        {"ok": False, "message": "Error creating service package."},
                        status=status.HTTP_400_BAD_REQUEST,
                    )

                stripe_subscription = StripeSubscription(
                    customer=customer,
                    package_plan=package_plan,
                )
                stripe_subscription.save()

            create_pipedrive_webhooks(access_token, customer)
            create_pipedrive_type_fields(customer.pk)
            create_pipedrive_stripe_url_fields(customer.pk)

            return Response(
                {
                    "ok": True,
                    "message": "Access token stored successfully.",
                    "customer": CustomerSerializer(customer).data,
                },
                status=status.HTTP_200_OK,
            )
        except Exception as e:
            logger.error(f"Error getting Oauth tokens from Pipedrive: {e}")
            return Response(
                {"ok": False, "message": "Error getting access token."},
                status=status.HTTP_400_BAD_REQUEST,
            )


# Create your views here.
class PackageCreateWebhook(APIView):
    """
    This should run when a product is created on Pipedrive.
    It should only modify the Templates, not the actual ServicePackages.
    """

    permission_classes = [IsAuthenticated]
    authentication_classes = [WebhookAuthentication]

    def post(self, request):
        try:
            # Simetimes the webhooks come in too fast,
            # so we need to wait a second to make sure the OnGoingSync object is created
            time.sleep(1)

            # Check if we should stop processing pipedrive webhooks
            stop_pipedrive_webhooks = Toggles.objects.filter(name="Toggles").first()
            if stop_pipedrive_webhooks.stop_pipedrive_webhooks:
                return Response(
                    status=status.HTTP_200_OK,
                    data={"ok": True, "message": "Synced successfully."},
                )

            # Get the pipedrive id
            request_data = request.data["current"]
            pipedrive_id = request_data["id"]
            type_split = request_data["name"].split(" ")
            type = type_split[1]
            related_app = type_split[0]
            description = request_data["description"]
            unit = request_data["prices"][0]["price"]

            # Check if the webhook is being sent as a result of a sync
            ongoing_sync = OngoingSync.objects.filter(
                type="package_template", action="create"
            ).first()
            if ongoing_sync:
                ongoing_sync.has_recieved_pipedrive_webhook = True
                ongoing_sync.save()
                return Response(
                    status=status.HTTP_200_OK,
                    data={"ok": True, "message": "Synced successfully."},
                )

            # Check if the package already exists
            existing_package = ServicePackageTemplate.objects.filter(
                pipedrive_id=pipedrive_id
            ).first()
            if existing_package:
                return Response(
                    status=status.HTTP_200_OK,
                    data={"ok": True, "message": "Synced successfully."},
                )

            # Check the request url for the customer pk. If it's there, thens set the owner to that customer, otherwise set it to the representative
            # The reason for this is so that later we can check if the customer is owned by the rep or the customer, and make the correct api requests.
            # If an employee is the owner then api keys will be used, if it is a customer then oauth will be used.
            customer_pk = request.GET.get("pk")
            if customer_pk is not None:
                customer = Customer.objects.get(pk=customer_pk)
                owner = customer.user
            else:
                employee = Employee.objects.all().first()
                owner = employee.user

            # Create the package
            service_package = ServicePackageTemplate(
                owner=owner,
                pipedrive_id=pipedrive_id,
                name=request_data["name"],
                description=description,
                unit=int(unit),
                type=type,
                related_app=related_app,
                cost=request_data["prices"][0]["price"],
                last_synced_from="pipedrive",
                original_sync_from="pipedrive",
            )
            service_package.save(should_sync_pipedrive=False, should_sync_stripe=True)
            return Response(status=status.HTTP_200_OK, data={"ok": True})
        except Exception as e:
            logger.error(e)
            return Response(
                status=status.HTTP_400_BAD_REQUEST,
                data={"ok": False, "message": "Failed to process request."},
            )


class PackageSyncWebhook(APIView):
    """
    This should run when a product is created, updated or deleted on Pipedrive.
    It should only modify the Templates, not the actual ServicePackages.
    """

    permission_classes = [IsAuthenticated]
    authentication_classes = [WebhookAuthentication]

    def post(self, request):
        try:
            # Simetimes the webhooks come in too fast,
            # so we need to wait a second to make sure the OnGoingSync object is created
            time.sleep(1)

            # Check if we should stop processing pipedrive webhooks
            stop_pipedrive_webhooks = Toggles.objects.filter(name="Toggles").first()
            if stop_pipedrive_webhooks.stop_pipedrive_webhooks:
                return Response(
                    status=status.HTTP_200_OK,
                    data={"ok": True, "message": "Synced successfully."},
                )

            # Get product data from the request
            request_data = request.data["current"]
            pipedrive_id = request_data["id"]
            pipedrive_price = Decimal(str(request_data["prices"][0]["price"])).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )
            pipedrive_name = request_data["name"]
            description = request_data["description"]
            unit = request_data["unit"]

            # Get the package template
            package_template = ServicePackageTemplate.objects.filter(
                pipedrive_id=pipedrive_id
            ).first()

            # Convert package_template.cost to Decimal and quantize
            package_template_cost = Decimal(str(package_template.cost)).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )

            # Check if the webhook is being sent as a result of a sync
            ongoing_sync = OngoingSync.objects.filter(
                type="package_template", action="update"
            ).first()
            if ongoing_sync:
                ongoing_sync.has_recieved_pipedrive_webhook = True
                ongoing_sync.save()
                if not ongoing_sync.stop_pipedrive_webhook:
                    return Response(
                        status=status.HTTP_200_OK,
                        data={"ok": True, "message": "Synced successfully."},
                    )

            # check if request pipedrive_id, name, or cost are different from the existing package template
            # if they are, continue with the update
            is_same_id = int(package_template.pipedrive_id) == int(pipedrive_id)
            is_same_name = package_template.name == pipedrive_name
            is_same_cost = package_template_cost == pipedrive_price
            is_same_description = package_template.description == description
            is_same_unit = package_template.unit == unit
            is_same = (
                is_same_id
                and is_same_name
                and is_same_cost
                and is_same_description
                and is_same_unit
            )
            if is_same:
                return Response(
                    status=status.HTTP_200_OK,
                    data={"ok": True, "message": "Synced successfully."},
                )

            # Check the request url for the customer pk. If it's there, thens set the owner to that customer, otherwise set it to the representative
            # The reason for this is so that later we can check if the customer is owned by the rep or the customer, and make the correct api requests.
            # If an employee is the owner then api keys will be used, if it is a customer then oauth will be used.
            customer_pk = request.GET.get("pk")
            if customer_pk is not None:
                customer = Customer.objects.get(pk=customer_pk)
                owner = customer.user
            else:
                employee = Employee.objects.all().first()
                owner = employee.user

            # Create the package if it doesn't exist
            if not package_template:
                package_template = ServicePackageTemplate(
                    owner=owner,
                    pipedrive_id=pipedrive_id,
                )

            # Update the package
            package_template.pipedrive_id = pipedrive_id
            package_template.name = request_data["name"]
            package_template.cost = request_data["prices"][0]["price"]
            package_template.last_synced_from = "pipedrive"
            package_template.original_sync_from = "pipedrive"
            package_template.description = description
            package_template.unit = int(unit)
            package_template.save(should_sync_pipedrive=False, should_sync_stripe=True)
            return Response(status=status.HTTP_200_OK, data={"ok": True})
        except Exception as e:
            logger.error(e)
            return Response(
                status=status.HTTP_400_BAD_REQUEST,
                data={"ok": False, "message": "Failed to process request."},
            )


class PackageDeleteWebhook(APIView):
    """
    This should run when a product is deleted on Pipedrive.
    It should only modify the Templates, not the actual ServicePackages.
    """

    permission_classes = [IsAuthenticated]
    authentication_classes = [WebhookAuthentication]

    def post(self, request):
        try:
            stop_pipedrive_webhooks = Toggles.objects.filter(name="Toggles").first()
            if stop_pipedrive_webhooks.stop_pipedrive_webhooks:
                return Response(
                    status=status.HTTP_200_OK,
                    data={"ok": True, "message": "Synced successfully."},
                )

            webhook_data = request.data
            pipedrive_id = webhook_data["previous"]["id"]
            package = ServicePackageTemplate.objects.filter(
                pipedrive_id=pipedrive_id
            ).first()
            package.delete()
            return Response(status=status.HTTP_200_OK, data={"ok": True})
        except Exception as e:
            logger.error(e)
            return Response(
                status=status.HTTP_400_BAD_REQUEST,
                data={"ok": False, "message": "Failed to process request."},
            )


class CustomerCreateWebhook(APIView):
    """
    This is the webhook that Pipedrive will send to when a customer is created or updated.
    It should just create, update or delete the customer in our database.
    """

    permission_classes = [IsAuthenticated]
    authentication_classes = [WebhookAuthentication]

    def post(self, request):
        # with cache.lock('CustomerCreateWebhookLock'):
        try:
            # temporary fix tp prevent webhook cashig errror
            if "pk" in request.GET:
                return Response({"ok": True}, status=status.HTTP_200_OK)
            
            print('\n\n In the webook!')
            # Simetimes the webhooks come in too fast,
            # so we need to wait a second to make sure the OnGoingSync object is created
            time.sleep(1)

            # Check if we should stop processing pipedrive webhooks
            stop_pipedrive_webhooks = Toggles.objects.filter(name="Toggles").first()
            if stop_pipedrive_webhooks.stop_pipedrive_webhooks:
                return Response(
                    status=status.HTTP_200_OK,
                    data={"ok": True, "message": "Synced successfully."},
                )

            # Get the pipedrive id
            data = request.data['current']
            # if data['current'] is None:
            #     return Response(
            #         status=status.HTTP_200_OK,
            #         data={"ok": True},
            #     )
            print('\n\nget the pipedrive id: ', data)
            # print('\nmeta data: ', data['meta'])
            # meta_data = data["meta"]
            print('id: ', data['id'])
            pipedrive_id = data["id"]

            # Check if the webhook is being sent as a result of a sync
            ongoing_sync = OngoingSync.objects.filter(
                type="customer", action="create"
            ).first()
            if ongoing_sync:
                ongoing_sync.has_recieved_pipedrive_webhook = True
                ongoing_sync.save()
                return Response(
                    status=status.HTTP_200_OK,
                    data={"ok": True, "message": "Synced successfully."},
                )

            # Check if the customer already exists
            existing_customer = Customer.objects.filter(
                pipedrive_id=pipedrive_id
            ).first()
            if existing_customer:
                return Response(
                    status=status.HTTP_200_OK,
                    data={"ok": True, "message": "Synced successfully."},
                )

            # print('\n\nChecking data: ', data)
            # Extract user data from webhook payload
            email = data["email"][0]["value"]
            first_name = data["first_name"]
            last_name = data["last_name"]
            phone = (
                data["phone"][0]["value"]
                if data["phone"]
                else None
            )
            password = "markittemppass2023"  # TODO - Set a default password or generate a random one

            # Create user object using the serializer
            # try:
            serializer_data = {
                "first_name": first_name,
                "last_name": last_name,
                "username": email,
                "email": email,
                "password": password,
            }
            # Check if a user with the provided email already exists
            if User.objects.filter(Q(email=email) | Q(username=email)).exists():
                print('\n\nUser already exists')
                return Response(
                    {"error": "A user with this email or username already exists."},
                    status=status.HTTP_200_OK,
                )

            print('\n\ncreating user...')
            try:
                serializer = RegisterSerializer(data=serializer_data)
                serializer.is_valid(raise_exception=True)
                user = serializer.save()
            except Exception as e:
                print('\n\nPipedrive customer creatwe webook failed with error: ', e)
                return Response(
                    status=status.HTTP_400_BAD_REQUEST,
                    data={"ok": False, "message": "Failed to process request."},
                )
            print('\n\nUser created: ', user)

            # Get the representative TODO - do this better
            

            print('\nGot a rep...')

            # Check the request url for the customer pk. If it's there, thens set the owner to that customer, otherwise set it to the representative
            # The reason for this is so that later we can check if the customer is owned by the rep or the customer, and make the correct api requests.
            # If an employee is the owner then api keys will be used, if it is a customer then oauth will be used.
            if "pk" in request.GET:
                print('Getting customer pk')
                customer_pk = request.GET.get("pk")
                print('customer_pk: ', customer_pk)
                customer = Customer.objects.get(pk=customer_pk)
                owner = customer.user
            else:
                print('\nGetting employee...\n')
                representative = Employee.objects.all().first()
                owner = representative.user

            print('\nChecking pipedrive_id: ', pipedrive_id)
            # Create customer object
            customer = Customer(
                user=user,
                owner=owner,
                pipedrive_id=pipedrive_id,
                rep=representative,
                phone=phone,
            )
            print('\nCustomer created: ', customer)
            customer.save(should_sync_pipedrive=False, should_sync_stripe=True)
            print('\nCustomer saved: ')
            return Response(status=status.HTTP_200_OK, data={"ok": True})
        except Exception as e:
            print('\n\nPipedrive customer creatwe webook failed with secondary error: ', e)
            return Response(
                status=status.HTTP_400_BAD_REQUEST,
                data={"ok": False, "message": "Failed to process request."},
            )


class CustomerSyncWebhook(APIView):
    """
    This is the webhook that Pipedrive will send to when a customer is created or updated.
    Is should just create, update or delete the customer in our database.
    """

    permission_classes = [IsAuthenticated]
    authentication_classes = [WebhookAuthentication]

    def post(self, request):
        # with cache.lock('CustomerSyncWebhookLock'):
        try:
            # Simetimes the webhooks come in too fast,
            # so we need to wait a second to make sure the OnGoingSync object is created
            time.sleep(3)
            # Check if we should stop processing pipedrive webhooks
            stop_pipedrive_webhooks = Toggles.objects.filter(name="Toggles").first()
            if stop_pipedrive_webhooks.stop_pipedrive_webhooks:
                return Response(
                    status=status.HTTP_200_OK,
                    data={"ok": True, "message": "Synced successfully."},
                )

            # request_data = request.data
            if request.data['current'] is None:
                return Response(
                    status=status.HTTP_200_OK,
                    data={"ok": True},
                )
            request_data = request.data['current']
            print('\n\nChecking request data: ', request_data)
            pipedrive_id = request_data["id"]
            customer = Customer.objects.filter(pipedrive_id=pipedrive_id).first()
            if not customer:
                return Response(
                    status=status.HTTP_404_NOT_FOUND,
                    data={"ok": False},
                )

            # Check if the webhook is being sent as a result of a sync
            ongoing_sync = OngoingSync.objects.filter(
                type="customer", action="update"
            ).first()
            if ongoing_sync:
                ongoing_sync.has_recieved_pipedrive_webhook = True
                ongoing_sync.save()
                return Response(
                    status=status.HTTP_200_OK,
                    data={"ok": True, "message": "Synced successfully."},
                )

            pipedrive_email = request_data["email"][0]["value"]
            pipedrive_first_name = request_data["first_name"]
            pipedrive_last_name = request_data["last_name"]
            pipedrive_phone = (
                request_data["phone"][0]["value"]
                if request_data["phone"]
                else None
            )
            
            print('Checking customer: ', customer)
            # Check if the customer data is the same as the data in the webhook
            # If it is, then we don't need to update the customer
            try:
                is_first_name_same = customer.first_name == pipedrive_first_name
                is_last_name_same = customer.last_name == pipedrive_last_name
                is_email_same = customer.email == pipedrive_email
                if customer.phone is None and pipedrive_phone == "None":
                    is_phone_same = True
                else:
                    is_phone_same = customer.phone == pipedrive_phone
                is_same = (
                    is_first_name_same
                    and is_last_name_same
                    and is_email_same
                    and is_phone_same
                )
                if is_same:
                    return Response(
                        status=status.HTTP_200_OK,
                        data={"ok": True, "message": "Synced successfully."},
                    )
            except Exception as e:
                print('\n\nPipedrive customer sync webhook failed: ', e)
                return Response(
                    status=status.HTTP_400_BAD_REQUEST,
                    data={"ok": False, "message": "Failed to process request."},
                )

            # Update customer data
            customer.first_name = request_data["first_name"]
            customer.last_name = request_data["last_name"]
            customer.email = request_data["email"][0]["value"]
            customer.phone = request_data["phone"][0]["value"]
            customer.save(should_sync_pipedrive=False)

            return Response(status=status.HTTP_200_OK, data={"ok": True})
        except Exception as e:
            print('\n\nPipedrive customer sync failed: ', e)
            return Response(
                status=status.HTTP_400_BAD_REQUEST,
                data={"ok": False, "message": "Failed to process request."},
            )


class CustomerDeleteWebhook(APIView):
    """
    This is the webhook that Pipedrive will send to when a customer is created or updated.
    Is should just create, update or delete the customer in our database.
    """

    permission_classes = [IsAuthenticated]
    authentication_classes = [WebhookAuthentication]

    def post(self, request):
        try:
            # Check if we should stop processing pipedrive webhooks
            stop_pipedrive_webhooks = Toggles.objects.filter(name="Toggles").first()
            if stop_pipedrive_webhooks.stop_pipedrive_webhooks:
                return Response(
                    status=status.HTTP_200_OK,
                    data={"ok": True, "message": "Synced successfully."},
                )

            meta_data = request.data["meta"]
            pipedrive_id = meta_data["id"]
            customer = Customer.objects.filter(pipedrive_id=pipedrive_id).first()
            customer.delete()
            return Response(status=status.HTTP_200_OK, data={"ok": True})
        except Exception as e:
            logger.error(e)
            return Response(
                status=status.HTTP_400_BAD_REQUEST,
                data={"ok": False, "message": "Failed to process request."},
            )


class DealCreateWebhook(APIView):
    """
    This should run when a deal is created on Pipedrive.
    It should create the ServicePackage and add the products to it.
    """

    permission_classes = [IsAuthenticated]
    authentication_classes = [WebhookAuthentication]

    def post(self, request):
        try:
            # Simetimes the webhooks come in too fast,
            # so we need to wait a second to make sure the OnGoingSync object is created
            time.sleep(1)

            # Check if we should stop processing pipedrive webhooks
            stop_pipedrive_webhooks = Toggles.objects.filter(name="Toggles").first()
            if stop_pipedrive_webhooks.stop_pipedrive_webhooks:
                return Response(
                    status=status.HTTP_200_OK,
                    data={"ok": True, "message": "Synced successfully."},
                )

            # Get the pipedrive id
            request_data = request.data["current"]
            pipedrive_id = request_data["id"]

            # Get the customer associated with this deal
            customer_pipedrive_id = request_data["person_id"]
            customer = Customer.objects.filter(
                pipedrive_id=customer_pipedrive_id
            ).first()
            if not customer:
                return Response(
                    status=status.HTTP_400_BAD_REQUEST,
                    data={
                        "ok": False,
                        "message": "No customer found with this pipedrive id.",
                    },
                )

            # Check if the webhook is being sent as a result of a sync
            ongoing_sync = OngoingSync.objects.filter(
                type="package_plan", action="create"
            ).first()
            # logger.info('\nChecking pipedrive webhook sync: ')
            if ongoing_sync:
                # logger.info(f'\nSTOPPING PIPEDRIVE DEAL CREATE WEBHOOK: {ongoing_sync}')
                ongoing_sync.has_recieved_pipedrive_webhook = True
                ongoing_sync.save()
                return Response(
                    status=status.HTTP_200_OK,
                    data={"ok": True, "message": "Synced successfully."},
                )

            # Check if the package already exists
            # logger.info('Checking if package already exists in the database')
            existing_package = PackagePlan.objects.filter(
                pipedrive_id=pipedrive_id
            ).first()
            if existing_package:
                return Response(status=status.HTTP_200_OK, data={"ok": True})

            # Check the request url for the customer pk. If it's there, thens set the owner to that customer, otherwise set it to the representative
            # The reason for this is so that later we can check if the customer is owned by the rep or the customer, and make the correct api requests.
            # If an employee is the owner then api keys will be used, if it is a customer then oauth will be used.
            customer_pk = request.GET.get("pk")
            if customer_pk is not None:
                customer = Customer.objects.get(pk=customer_pk)
                owner = customer.user
            else:
                employee = Employee.objects.all().first()
                owner = employee.user

            # Create the package
            service_package = PackagePlan(
                owner=owner,
                pipedrive_id=pipedrive_id,
                customer=customer,
                name=request_data["title"],
                # status=deal_status,
                # type=payment_selection.lower() if payment_selection is not None else None,
            )

            service_package.save(should_sync_pipedrive=False, should_sync_stripe=False)

            return Response(status=status.HTTP_200_OK, data={"ok": True})
        except Exception as e:
            logger.error(e)
            return Response(
                status=status.HTTP_400_BAD_REQUEST,
                data={"ok": False, "message": "Failed to process request."},
            )


class DealSyncWebhook(APIView):
    """
    This should run when a deal is updated on Pipedrive.
    It should update the ServicePackage and add the products to it.
    """

    permission_classes = [IsAuthenticated]
    authentication_classes = [WebhookAuthentication]

    def post(self, request):
        from apps.stripe.models import StripeSubscription
        from apps.stripe.tasks import sync_stripe
        from .utils import get_pipedrive_oauth_tokens

        # ----------------------------

        def is_data_same(package_plan, request_data, deal_products):
            # Compare the name and status fields
            if package_plan.name != request_data["title"]:
                return False

            # Compare the products
            service_package_products = ServicePackage.objects.filter(
                package_plan=package_plan
            )
            if (
                not service_package_products
                or not deal_products
                or len(service_package_products) != len(deal_products)
            ):
                return False

            # Compare the products
            service_package_list = list(service_package_products.values())
            for deal_product in deal_products:
                # Check if the product exists in the service_package_list
                matching_service_package = None
                for service_package in service_package_list:
                    if (
                        str(deal_product["id"])
                        == service_package["pipedrive_product_attachment_id"]
                    ):
                        matching_service_package = service_package
                        break

                if matching_service_package is None:
                    return False

                if float(deal_product["item_price"]) != float(
                    matching_service_package["cost"]
                ):
                    return False

                if deal_product["quantity"] != matching_service_package["quantity"]:
                    return False

            return True

        # ----------------------------

        try:
            # Simetimes the webhooks come in too fast,
            # so we need to wait a second to make sure the OnGoingSync object is created
            time.sleep(1)

            # Check if we should stop processing pipedrive webhooks
            stop_pipedrive_webhooks = Toggles.objects.filter(name="Toggles").first()
            if stop_pipedrive_webhooks.stop_pipedrive_webhooks:
                return Response(
                    status=status.HTTP_200_OK,
                    data={"ok": True, "message": "Synced successfully."},
                )

            # Check if the webhook is being sent as a result of a sync
            ongoing_sync = OngoingSync.objects.filter(
                type="package_plan", action="update"
            ).first()
            if ongoing_sync:
                ongoing_sync.has_recieved_pipedrive_webhook = True
                ongoing_sync.save()
                return Response(
                    status=status.HTTP_200_OK,
                    data={"ok": True, "message": "Synced successfully."},
                )

            # Get the pipedrive data
            if not request_data.get('current'):
                print('data.current is None')
                return Response(
                    status=status.HTTP_400_BAD_REQUEST,
                    data={"ok": False, "message": "data.current is None"},
                )
            request_data = request.data["current"]
            pipedrive_id = request_data["id"]

            # Check if the PackagePlan exists
            package_plan = PackagePlan.objects.filter(pipedrive_id=pipedrive_id).first()
            if not package_plan:
                return Response(
                    status=status.HTTP_400_BAD_REQUEST,
                    data={
                        "ok": False,
                        "message": "No service package found with this pipedrive id.",
                    },
                )

            # If the owner is a custopmer use oauth, else use api key
            headers = None
            if package_plan.owner.is_staff:
                pipedrive_key = os.environ.get("PIPEDRIVE_API_KEY")
                pipedrive_domain = os.environ.get("PIPEDRIVE_DOMAIN")

                payment_field_key = os.environ.get("PIPEDRIVE_DEAL_TYPE_FIELD")
                processing_field_key = os.environ.get("PIPEDRIVE_DEAL_PROCESSING_FIELD")
                subscription_selector = os.environ.get(
                    "PIPEDRIVE_DEAL_SUBSCRIPTION_SELECTOR"
                )
                payout_selector = os.environ.get("PIPEDRIVE_DEAL_PAYOUT_SELECTOR")
                pipedrive_deal_invoice_selector = os.environ.get(
                    "PIPEDRIVE_DEAL_INVOICE_SELECTOR"
                )
                pipedrive_deal_process_now_selector = os.environ.get(
                    "PIPEDRIVE_DEAL_PROCESS_NOW_SELECTOR"
                )
            else:
                plan_owner = Customer.objects.filter(user=package_plan.owner)
                payment_field_key = plan_owner.PIPEDRIVE_DEAL_TYPE_FIELD
                processing_field_key = plan_owner.PIPEDRIVE_DEAL_PROCESSING_FIELD
                subscription_selector = plan_owner.PIPEDRIVE_DEAL_SUBSCRIPTION_SELECTOR
                payout_selector = plan_owner.PIPEDRIVE_DEAL_PAYOUT_SELECTOR
                pipedrive_deal_invoice_selector = (
                    plan_owner.PIPEDRIVE_DEAL_INVOICE_SELECTOR
                )
                pipedrive_deal_process_now_selector = (
                    plan_owner.PIPEDRIVE_DEAL_PROCESS_NOW_SELECTOR
                )
                pipedrive_domain = plan_owner.piprdrive_api_url
                tokens = get_pipedrive_oauth_tokens(plan_owner.owner.pk)
                headers = {
                    "Authorization": f'Bearer {tokens["access_token"]}',
                }

            # Update package plan details
            package_plan.name = request_data["title"]
            payment_selection = request_data[f"{payment_field_key}"]
            processing_selection = request_data[f"{processing_field_key}"]
            if payment_selection == None or processing_selection == None:
                package_plan.status = "lost"
            else:
                package_plan.status = request_data["status"]
            package_plan.type = (
                payment_selection.lower() if payment_selection is not None else None
            )

            # Get the products from the deal and return if there are no changes
            if not headers:
                url = f"https://{pipedrive_domain}.pipedrive.com/v1/deals/{package_plan.pipedrive_id}/products?api_token={pipedrive_key}"
                response = requests.get(url)
            else:
                url = (
                    f"{pipedrive_domain}/v1/deals/{package_plan.pipedrive_id}/products"
                )
                response = requests.get(url, headers=headers)

            deal_products = response.json()["data"]
            if is_data_same(package_plan, request_data, deal_products):
                return Response(
                    status=status.HTTP_200_OK,
                    data={
                        "ok": True,
                        "message": "Data is the same, no need to update.",
                    },
                )

            # Delete all ServicePackage objects that are not in the products list
            service_package_products = ServicePackage.objects.filter(
                package_plan=package_plan
            )
            if service_package_products:
                products_ids = [product["id"] for product in deal_products]
                for service_package_product in service_package_products:
                    if (
                        service_package_product.pipedrive_product_attachment_id
                        not in str(products_ids)
                    ):
                        service_package_product.delete(should_sync_pipedrive=False)

            # Add all products to the ServicePackage
            for product in deal_products:
                pipedrive_product_attachment_id = product["id"]
                service_package = ServicePackage.objects.filter(
                    pipedrive_product_attachment_id=pipedrive_product_attachment_id
                ).first()
                if not service_package:
                    product_id = product["product_id"]
                    package_template = ServicePackageTemplate.objects.filter(
                        pipedrive_id=product_id
                    ).first()
                    service_package = ServicePackage(
                        pipedrive_product_attachment_id=pipedrive_product_attachment_id,
                        package_plan=package_plan,
                        customer=package_plan.customer,
                        package_template=package_template,
                        cost=product["item_price"],
                        quantity=product["quantity"],
                    )
                    service_package.save(
                        should_sync_pipedrive=False, should_sync_stripe=True
                    )

            # Check if the customer has a payment method setup in Stripe
            stripe.api_key = os.environ.get("STRIPE_PRIVATE")
            customer_id = package_plan.customer.stripe_customer_id
            try:
                customer = stripe.Customer.retrieve(customer_id)
                payment_methods = customer["default_source"]
                if len(deal_products) > 0 and not payment_methods:
                    package_plan.status = "lost"
                    package_plan.save(
                        should_sync_pipedrive=True, should_sync_stripe=False
                    )
                    return Response(
                        status=status.HTTP_400_OK,
                        data={
                            "ok": True,
                            "message": "No payment method found for this customer.",
                        },
                    )
            except stripe.error.StripeError as e:
                return Response(
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    data={
                        "ok": False,
                        "message": "Failed to retrieve customer payment methods.",
                    },
                )

            # Set up the Stripe Subscription or Payout
            # This is looking at the payment selection and processing selection to determine what to do
            # This should create either a subscription or a paymanet intent, and then either send an invoice or process the payment
            # These values come from the selection cields created in Pipedrive when an account is created
            if payment_selection == str(subscription_selector):
                if processing_selection == str(pipedrive_deal_process_now_selector):
                    logger.info(
                        "Creating a new subscription for the customer. Processing now..."
                    )
                    stripe_subscription = StripeSubscription.objects.filter(
                        customer=package_plan.customer
                    ).first()
                    if stripe_subscription:
                        subscription_pk = stripe_subscription.pk
                        sync_stripe.delay(subscription_pk, "update", "subscription")
                        return Response(status=status.HTTP_200_OK, data={"ok": True})
                    else:
                        stripe_subscription = StripeSubscription(
                            customer=package_plan.customer,
                            package_plan=package_plan,
                        )
                        stripe_subscription.save()
                        package_plan.status = "won"
                        package_plan.save()
                        return Response(status=status.HTTP_200_OK, data={"ok": True})
                else:
                    logger.info(
                        "Creating a new subscription for the customer. Sending invoice now..."
                    )
                    package_plan.status = "lost"
                    package_plan.save()
                    return Response(status=status.HTTP_200_OK, data={"ok": True})

            elif payment_selection == str(payout_selector):
                if processing_selection == str(pipedrive_deal_process_now_selector):
                    logger.info("** Creating Stripe Payout. Processing now...")
                    package_plan.status = "lost"
                    package_plan.save()
                    return Response(status=status.HTTP_200_OK, data={"ok": True})
                else:
                    package_plan.status = "lost"
                    package_plan.save()
                    logger.info("** Creating Stripe Payout. Sending invoice...")
                    return Response(status=status.HTTP_200_OK, data={"ok": True})
            else:
                package_plan.status = "lost"
                package_plan.save(should_sync_pipedrive=True, should_sync_stripe=False)
                return Response(
                    status=status.HTTP_400_OK,
                    data={"ok": False, "message": "Unknown deal type."},
                )

        except Exception as e:
            logger.error(e)
            return Response(
                status=status.HTTP_400_BAD_REQUEST,
                data={"ok": False, "message": "Failed to process request."},
            )


class DealDeleteWebhook(APIView):
    """
    This should run when a deal is deleted on Pipedrive.
    It should delete the ServicePackage and remove the products from it.
    """

    permission_classes = [IsAuthenticated]
    authentication_classes = [WebhookAuthentication]

    def post(self, request):
        try:
            # Check if we should stop processing pipedrive webhooks
            stop_pipedrive_webhooks = Toggles.objects.filter(name="Toggles").first()
            if stop_pipedrive_webhooks.stop_pipedrive_webhooks:
                return Response(
                    status=status.HTTP_200_OK,
                    data={"ok": True, "message": "Synced successfully."},
                )

            webhook_data = request.data
            pipedrive_id = webhook_data["previous"]["id"]
            service_package = PackagePlan.objects.filter(
                pipedrive_id=pipedrive_id
            ).first()
            service_package.delete()
            return Response(status=status.HTTP_200_OK, data={"ok": True})
        except Exception as e:
            logger.error(e)
            return Response(
                status=status.HTTP_400_BAD_REQUEST,
                data={"ok": False, "message": "Failed to process request."},
            )
