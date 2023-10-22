import os, time, json, stripe
from decimal import ROUND_HALF_UP, Decimal
# import requests
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from apps.accounts.custom_auth import WebhookAuthentication
from apps.accounts.models import Customer, Employee, OngoingSync, Toggles
from apps.package_manager.models import (
    PackagePlan,
    ServicePackage,
    ServicePackageTemplate,
)
import logging
from .models import StripeSubscription

logger = logging.getLogger(__name__)
stripe.api_key = os.environ.get("STRIPE_PRIVATE")

class StripeSubscriptionCheckoutSession(APIView):
    """ API view for creating a Stripe checkout session for a subscription """

    def get(self, request):
        try:
            if "pk" not in request.GET:
                return Response({"ok": False, "message": "No package pk provided."}, status=status.HTTP_400_BAD_REQUEST)
            
            # Get the customer's stripe_customer_id
            if "customer_pk" not in request.GET:
                return Response({"ok": False, "message": "No customer pk provided."}, status=status.HTTP_400_BAD_REQUEST)
            customer = Customer.objects.get(pk=request.GET["customer_pk"])

            if "redirect_url" not in request.GET:
                return Response({"ok": False, "message": "No redirect uri provided."}, status=status.HTTP_400_BAD_REQUEST)

            redirect_url = request.GET['redirect_url']
            stripe.api_key = os.environ.get("STRIPE_PRIVATE")
            package = ServicePackageTemplate.objects.get(pk=request.GET["pk"])
            checkout_session = stripe.checkout.Session.create(
                payment_method_types=['card'],
                line_items=[{'price': package.stripe_price_id, 'quantity': 1}],
                mode='subscription',
                success_url=f'{redirect_url}?success=true',
                cancel_url=redirect_url,
                customer=customer.stripe_customer_id, 
            )
            url = checkout_session['url']
            return Response(
                {"ok": True, "message": "Successfully created checkout session.", "url": url}
            )
        except Exception as e:
            print('Failed to get subscription link: ', e)
            return Response({"ok": False, "message": "An error occurred."})

class StripePaymentPageLink(APIView):
    """ API view for getting the stripe payment page link """

    def get(self, request):
        try:
            if "pk" not in request.GET:
                return Response({"ok": False, "message": "No package pk provided."})
            
            frontend_url = os.environ.get("FRONTEND_URL")
            redirect_url = f'{frontend_url}/dashboard/integrations/'
            stripe.api_key = os.environ.get("STRIPE_PRIVATE")
            package = ServicePackageTemplate.objects.get(pk=request.GET["pk"])
            stripe_link = stripe.PaymentLink.create(
                line_items=[{"price": package.stripe_price_id, "quantity": 1}], 
                after_completion={"type": "redirect", "redirect": {"url": redirect_url}},
            )
            
            return Response(
                {"ok": True, "message": "Successfully created account link.", "url": stripe_link}
            )
        except Exception as e:
            print(e)

class GetStripeAccountLink(APIView):
    """ API view for getting the stripe account link """

    # permission_classes = [IsAuthenticated]
    # authentication_classes = [WebhookAuthentication] 

    def get(self, request):
        try:
            if "pk" not in request.GET:
                return Response({"ok": False, "message": "No customer pk provided."})
            
            customer = Customer.objects.get(pk=request.GET["pk"])
            frontend_url = os.environ.get("FRONTEND_URL")
            stripe.api_key = os.environ.get("STRIPE_PRIVATE")
            response = stripe.AccountLink.create(
                account=customer.stripe_account_id,
                refresh_url=f"{frontend_url}/dashboard/integrations/",
                return_url=f"{frontend_url}/dashboard/integrations?connected=true",
                type="account_onboarding",
            )
            
            customer.save(should_sync_pipedrive=False, should_sync_stripe=False)
            return Response(
                {"ok": True, "message": "Successfully created account link.", "url": response["url"]}
            )

        except Exception as e:
            print('\nFailed to get account link: ', e)
            return Response({"ok": False, "message": "An error occurred."})

        
    def post(self, request):
        try:

            # Check the customer's connection status in stripe
            if "pk" not in request.query_params:
                return Response({"ok": False, "message": "No customer pk provided."})

            customer = Customer.objects.get(pk=request.query_params["pk"])
            stripe.api_key = os.environ.get("STRIPE_PRIVATE")

            # Retrieve the account details
            account = stripe.Account.retrieve(customer.stripe_account_id)

            # Check if the account is fully onboarded
            if not len(account.requirements.currently_due) > 0:
                customer.has_synced_stripe = True
                customer.save(update_fields=["has_synced_stripe"], should_sync_pipedrive=False, should_sync_stripe=False)
                return Response({"ok": True, "message": "Account successfully connected."})
            else:
                return Response({"ok": False, "message": "Account not fully connected."}, status=status.HTTP_400_BAD_REQUEST)

        except Customer.DoesNotExist:
            return Response({"ok": False, "message": "Customer does not exist."}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            print('Failed with error: ', e)
            return Response({"ok": False, "message": "An unexpected error occurred."}, status=status.HTTP_400_BAD_REQUEST)



class ProductCreateWebhook(APIView):
    """API view for creating a new product in stripe"""

    # permission_classes = [IsAuthenticated]
    # authentication_classes = [WebhookAuthentication]

    def post(self, request, format=None):
        # Simetimes the webhooks come in too fast,
        # so we need to wait a second to make sure the OnGoingSync object is created
        time.sleep(1)

        # Check if we should stop processing stripe webhooks
        stop_stripe_webhooks = Toggles.objects.filter(name="Toggles").first()
        if stop_stripe_webhooks.stop_stripe_webhooks:
            return Response(
                status=status.HTTP_200_OK,
                data={"ok": True, "message": "Synced successfully."},
            )

        # # Check for any on going sync objects
        ongoing_sync = OngoingSync.objects.filter(
            type="package_template", action="create"
        ).first()
        if ongoing_sync:
            ongoing_sync.has_recieved_stripe_webhook = True
            ongoing_sync.save()
            if not ongoing_sync.stop_stripe_webhook:
                return Response(
                    status=status.HTTP_200_OK,
                    data={"ok": True, "message": "Synced successfully."},
                )
        try:
            # Create a new package template
            product_id = request.data["data"]["object"]["id"]
            product_name = request.data["data"]["object"]["name"]
            product_description = request.data["data"]["object"]["description"]
            split_related_app = product_name.split(" ")
            related_app = split_related_app[0].lower()
            type = split_related_app[1].lower()

            # Check for an existing package template
            existing_package_template = ServicePackageTemplate.objects.filter(
                stripe_product_id=product_id
            ).first()
            if existing_package_template:
                print('existing package template found...')
                existing_package_template.save(
                    should_sync_pipedrive=False, should_sync_stripe=False
                )
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

            new_package_template = ServicePackageTemplate(
                owner=owner,
                name=product_name,
                description=product_description,
                related_app=related_app,
                type=type,
                stripe_product_id=product_id,
                requires_onboarding=False,
                last_synced_from="stripe",
                original_sync_from="stripe",
            )
            new_package_template.save(
                should_sync_pipedrive=True, should_sync_stripe=False
            )
            return Response(
                status=status.HTTP_200_OK,
                data={"ok": True, "message": "Synced successfully."},
            )
        except Exception as e:
            logger.error(f"ERROR: {e}")
            return Response(
                status=status.HTTP_400_BAD_REQUEST,
                data={"ok": False, "message": "Failed to process request."},
            )


class ProductSyncWebhook(APIView):
    """API view for syncing a product in stripe"""

    # permission_classes = [IsAuthenticated]
    # authentication_classes = [WebhookAuthentication]

    def post(self, request, format=None):
        # Simetimes the webhooks come in too fast,
        # so we need to wait a second to make sure the OnGoingSync object is created
        time.sleep(1)

        # Check if we should stop processing stripe webhooks
        stop_stripe_webhooks = Toggles.objects.filter(name="Toggles").first()
        if stop_stripe_webhooks.stop_stripe_webhooks:
            return Response(
                status=status.HTTP_200_OK,
                data={"ok": True, "message": "Synced successfully."},
            )

        # # Check for any on going sync objects
        ongoing_sync = OngoingSync.objects.filter(
            type="package_template", action="update"
        ).first()
        if ongoing_sync:
            ongoing_sync.has_recieved_stripe_webhook = True
            ongoing_sync.save()
            if not ongoing_sync.stop_stripe_webhook:
                return Response(
                    status=status.HTTP_200_OK,
                    data={"ok": True, "message": "Synced successfully."},
                )

        product_id = request.data["data"]["object"]["id"]
        product = ServicePackageTemplate.objects.filter(
            stripe_product_id=product_id
        ).first()

        # Chaeck if the price has changed
        if product:
            stripe.api_key = os.environ.get("STRIPE_PRIVATE")
            price_id = request.data["data"]["object"]["default_price"]

            try:
                # Get the stripe price
                if price_id is None:
                    stripe_price_response = stripe.Price.list(product=product_id)
                    stripe_price = stripe_price_response["data"][0][
                        "unit_amount_decimal"
                    ]
                    price_id = stripe_price_response["data"][0]["id"]
                    unit_amount_decimal = stripe_price_response["data"][0][
                        "unit_amount_decimal"
                    ]
                    stripe_price_cents = Decimal(str(unit_amount_decimal))
                    stripe_price = (stripe_price_cents / 100).quantize(
                        Decimal("0.01"), rounding=ROUND_HALF_UP
                    )
                else:
                    price = stripe.Price.retrieve(price_id)
                    stripe_price_cents = Decimal(str(price["unit_amount_decimal"]))
                    stripe_price = (stripe_price_cents / 100).quantize(
                        Decimal("0.01"), rounding=ROUND_HALF_UP
                    )

                if stripe_price != product.cost:
                    product.cost = stripe_price
                    product.stripe_price_id = price_id

            except Exception as e:
                logger.error(f"ERROR: {e}")
                return Response(
                    status=status.HTTP_400_BAD_REQUEST,
                    data={"ok": False, "message": "Failed to process request."},
                )

            # Update the product
            product_name = request.data["data"]["object"]["name"]
            product_description = request.data["data"]["object"]["description"]
            product.name = product_name
            product.description = product_description
            product.last_synced_from = "stripe"
            product.original_sync_from = "stripe"
            product.save(should_sync_pipedrive=True, should_sync_stripe=False)

        return Response(
            status=status.HTTP_200_OK,
            data={"ok": True, "message": "Synced successfully."},
        )


class ProductDeleteWebhook(APIView):
    """API view for syncing a product in stripe"""

    # permission_classes = [IsAuthenticated]
    # authentication_classes = [WebhookAuthentication]

    def post(self, request, format=None):
        # Check if we should stop processing stripe webhooks
        stop_stripe_webhooks = Toggles.objects.filter(name="Toggles").first()
        if stop_stripe_webhooks.stop_stripe_webhooks:
            return Response(
                status=status.HTTP_200_OK,
                data={"ok": True, "message": "Synced successfully."},
            )

        product_id = request.data["data"]["object"]["id"]
        product = ServicePackageTemplate.objects.filter(
            stripe_product_id=product_id
        ).first()
        if product:
            product.delete(should_sync_stripe=False, should_sync_pipedrive=True)

        return Response(
            status=status.HTTP_200_OK,
            data={"ok": True, "message": "Synced successfully."},
        )


class CustomerCreateWebhook(APIView):
    """API view for syncing a customer in stripe"""

    # permission_classes = [IsAuthenticated]
    # authentication_classes = [WebhookAuthentication]

    def post(self, request, format=None):
        from apps.accounts.serializers import RegisterSerializer

        logger.info("*** Stripe CustomerCreateWebhook ***")
        # Simetimes the webhooks come in too fast,
        # so we need to wait a second to make sure the OnGoingSync object is created
        # logger.info(f'IN THE CUSTOMER CREATE WEBHOOK - {request.data}')
        time.sleep(1)

        # Check if we should stop processing stripe webhooks
        stop_stripe_webhooks = Toggles.objects.filter(name="Toggles").first()
        if stop_stripe_webhooks.stop_stripe_webhooks:
            return Response(
                status=status.HTTP_200_OK,
                data={"ok": True, "message": "Synced successfully."},
            )

        # # Check for any on going sync objects
        ongoing_sync = OngoingSync.objects.filter(
            type="customer", action="create"
        ).first()
        if ongoing_sync:
            ongoing_sync.has_recieved_stripe_webhook = True
            ongoing_sync.save()
            if not ongoing_sync.stop_stripe_webhook:
                return Response(
                    status=status.HTTP_200_OK,
                    data={"ok": True, "message": "Synced successfully."},
                )

        # Check if the customer already exists
        logger.info("Checking Customer...")
        stripe_customer = request.data["data"]["object"]
        customer_id = request.data["data"]["object"]["id"]
        logger.info(f"customer_id: {customer_id}")
        customer = Customer.objects.filter(stripe_customer_id=customer_id).first()
        logger.info(f"customer: {customer}")
        if customer:
            customer.save(should_sync_pipedrive=True, should_sync_stripe=False)
            return Response(
                status=status.HTTP_200_OK,
                data={"ok": True, "message": "Customer Already Exists...."},
            )

        # Setup the new user
        logger.warning("customer doesnt exists, create it...")
        rep = Employee.objects.all().first()
        email = stripe_customer["email"]
        phone = stripe_customer.get("phone", "")
        name_split = stripe_customer.get("name", "").split(" ")
        first_name = name_split[0] if len(name_split) > 0 else ""
        last_name = " ".join(name_split[1:]) if len(name_split) > 1 else ""
        password = "markittemppass2023"  # TODO - Set a default password or generate a random one
        logger.info(f"phone: {phone}")
        logger.info(f"email: {email}")
        try:
            serializer_data = {
                "first_name": first_name,
                "last_name": last_name,
                "email": email,
                "password": password,
            }
            serializer = RegisterSerializer(data=serializer_data)
            serializer.is_valid(raise_exception=True)
            if serializer.is_valid():
                user = serializer.save()
            else:
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(e)
            return Response(
                status=status.HTTP_400_BAD_REQUEST,
                data={"ok": False, "message": "Failed to process request."},
            )

        # Check the request url for the customer pk. If it's there, thens set the owner to that customer, otherwise set it to the representative
        # The reason for this is so that later we can check if the customer is owned by the rep or the customer, and make the correct api requests.
        # If an employee is the owner then api keys will be used, if it is a customer then oauth will be used.
        customer_pk = request.GET.get("pk")
        if customer_pk is not None:
            customer = Customer.objects.get(pk=customer_pk)
            owner = customer.user
        else:
            owner = rep.user

        # Create the customer
        customer = Customer(
            user=user,
            phone=phone,
            rep=rep,
            owner=owner,
            stripe_customer_id=customer_id,
            last_synced_from="stripe",
            original_sync_from="stripe",
        )
        customer.save(should_sync_pipedrive=True, should_sync_stripe=False)
        logger.info(f"customer: {customer}")

        return Response(
            status=status.HTTP_200_OK,
            data={"ok": True, "message": "Synced successfully."},
        )


class CustomerSyncWebhook(APIView):
    """API view for syncing a customer in stripe"""

    # permission_classes = [IsAuthenticated]
    # authentication_classes = [WebhookAuthentication]

    def post(self, request, format=None):
        logger.info("*** CustomerSyncWebhook ***")

        # Check if we should stop processing stripe webhooks
        stop_stripe_webhooks = Toggles.objects.filter(name="Toggles").first()
        if stop_stripe_webhooks.stop_stripe_webhooks:
            return Response(
                status=status.HTTP_200_OK,
                data={"ok": True, "message": "Synced successfully."},
            )

        # # Check for any on going sync objects
        ongoing_sync = OngoingSync.objects.filter(
            type="customer", action="update"
        ).first()
        if ongoing_sync:
            ongoing_sync.has_recieved_stripe_webhook = True
            ongoing_sync.save()
            if not ongoing_sync.stop_stripe_webhook:
                return Response(
                    status=status.HTTP_200_OK,
                    data={"ok": True, "message": "Synced successfully."},
                )

        # get the customer stripe id from the webhook
        customer_stripe_data = request.data["data"]["object"]
        customer_id = customer_stripe_data["id"]
        stripe_phone = customer_stripe_data.get("phone", "")
        name_split = customer_stripe_data.get("name", "").split(" ")
        stripe_fist_name = name_split[0] if len(name_split) > 0 else ""
        stripe_last_name = " ".join(name_split[1:]) if len(name_split) > 1 else ""
        stripe_email = customer_stripe_data["email"]

        # get the customer from the db
        customer = Customer.objects.filter(stripe_customer_id=customer_id).first()

        # Check if any of the fields have changed
        try:
            is_first_name_same = customer.first_name == stripe_fist_name
            is_last_name_same = customer.last_name == stripe_last_name
            is_email_same = customer.email == stripe_email
            is_phone_same = customer.phone == stripe_phone
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
            logger.error(e)
            return Response(
                status=status.HTTP_400_BAD_REQUEST,
                data={"ok": False, "message": "Failed to process request."},
            )

        # Update the customer
        customer.first_name = stripe_fist_name
        customer.last_name = stripe_last_name
        customer.email = stripe_email
        customer.phone = stripe_phone
        customer.last_synced_from = "stripe"
        customer.save(should_sync_pipedrive=True, should_sync_stripe=False)

        return Response(
            status=status.HTTP_200_OK,
            data={"ok": True, "message": "Synced successfully."},
        )


class CustomerDeleteWebhook(APIView):
    """API view for syncing a customer in stripe"""

    # permission_classes = [IsAuthenticated]
    # authentication_classes = [WebhookAuthentication]

    def post(self, request, format=None):
        logger.info("*** CustomerDeleteWebhook ***")

        # Check if we should stop processing stripe webhooks
        stop_stripe_webhooks = Toggles.objects.filter(name="Toggles").first()
        if stop_stripe_webhooks.stop_stripe_webhooks:
            return Response(
                status=status.HTTP_200_OK,
                data={"ok": True, "message": "Synced successfully."},
            )

        customer_id = request.data["data"]["object"]["id"]
        customer = Customer.objects.filter(stripe_customer_id=customer_id).first()
        if customer:
            customer.delete()

        return Response(
            status=status.HTTP_200_OK,
            data={"ok": True, "message": "Synced successfully."},
        )


class SubscriptionCreateWebhook(APIView):
    """API view for syncing a subscription in stripe"""

    # permission_classes = [IsAuthenticated]
    # authentication_classes = [WebhookAuthentication]

    def post(self, request, format=None):
        from apps.package_manager.utils import create_service_packages

        try:
            # time.sleep(3)
            # Check if we should stop processing stripe webhooks
            stop_stripe_webhooks = Toggles.objects.filter(name="Toggles").first()
            if stop_stripe_webhooks.stop_stripe_webhooks:
                return Response(
                    status=status.HTTP_200_OK,
                    data={"ok": True, "message": "Synced successfully."},
                )

            # # Check for any on going sync objects
            ongoing_sync = OngoingSync.objects.filter(
                type="package_plan", action="create"
            ).first()
            if ongoing_sync:
                ongoing_sync.has_recieved_stripe_webhook = True
                # logger.info('* Stopped processing stripe webhook because of ongoing sync.')
                ongoing_sync.save()
                return Response(
                    status=status.HTTP_200_OK,
                    data={"ok": True, "message": "Synced successfully."},
                )

            # Get the subscription id and customer id
            subscription_id = request.data["data"]["object"]["id"]
            customer_id = request.data["data"]["object"]["customer"]
            items = request.data["data"]["object"]["items"]["data"]
            product_details = []
            subscription = request.data["data"]["object"]
            items = subscription["items"]["data"]

            for item in items:
                product_id = item["price"]["product"]
                price_id = item["price"]["id"]
                price_value = item["price"]["unit_amount"]
                product = stripe.Product.retrieve(product_id)
                product_name = product["name"]
                product_details.append((product_id, price_id, price_value, product_name))

            # Check if the customer exists
            customer = Customer.objects.filter(stripe_customer_id=customer_id).first()
            if not customer:
                customer = Customer.objects.filter(user=request.user).first()
                if not customer:
                    logger.info("*** Customer not found ***")
                    return Response(
                        status=status.HTTP_200_OK,
                        data={"ok": True, "message": "Synced successfully."},
                    )

            # Check if the package plan already exists
            package_plan = PackagePlan.objects.filter(
                stripe_subscription_id=subscription_id
            ).first()
            if package_plan:
                print('package plan already exists...')
                # logger.info('*** Package plan already exists ***')
                return Response(
                    status=status.HTTP_200_OK,
                    data={"ok": True, "message": "Synced successfully."},
                )

            package_plan = {
                "owner": request.user,
                'billing_cycle': 'monthly',
                "type": "subscription",
                "status": subscription["status"],
                "description": "New Customer Package Plan",
                "stripe_subscription_id": subscription_id,
                "packages": [],
            }

            for item in items:
                try:
                    stripe_subscription_item_id = item["id"]
                    price_id = item["price"]["id"]
                    price_value = item["price"]["unit_amount"] / 100
                    product = stripe.Product.retrieve(item["price"]["product"])
                    product_name = product["name"]
                    requires_onboarding = False
                    # split product name in 2 parts, at the first space, and use the first part as the related_app and the second as the type
                    related_app = product_name.split(" ", 1)[0]
                    type = product_name.split(" ", 1)[1]

                    package = {
                        "stripe_subscription_item_id": stripe_subscription_item_id,
                        "stripe_price_id": price_id,
                        "name": product_name,
                        "price": price_value,
                        "related_app": related_app,
                        "type": type,
                        "requires_onboarding": requires_onboarding,
                        "status": "won",
                    }
                    package_plan["packages"].append(package)

                    customer_pk = request.GET.get("pk", None)
                    if customer_pk:
                        owner = customer.user
                    else:
                        owner = customer.rep.user
                except Exception as e:
                    print('FAILE WHILE CRETING PRODUCTS: ', e)

            # Create the service packages
            create_service_packages(customer, package_plan, True, False, subscription_id, owner=owner)

            return Response(
                status=status.HTTP_200_OK,
                data={"ok": True, "message": "Synced successfully."},
            )
        except Exception as e:
            return Response(
                status=status.HTTP_400_BAD_REQUEST,
                data={"ok": False, "message": "Failed to process request."},
            )


class SubscriptionSyncWebhook(APIView):
    """API view for syncing a subscription in stripe"""

    # permission_classes = [IsAuthenticated]
    # authentication_classes = [WebhookAuthentication]

    def post(self, request, format=None):
        logger.info("*** SubscriptionSyncWebhook ***")
        # logger.info(request.data)

        # Check if we should stop processing stripe webhooks
        stop_stripe_webhooks = Toggles.objects.filter(name="Toggles").first()
        if stop_stripe_webhooks.stop_stripe_webhooks:
            return Response(
                status=status.HTTP_200_OK,
                data={"ok": True, "message": "Synced successfully."},
            )

        # Check for any on going sync objects
        ongoing_sync = OngoingSync.objects.filter(
            type="package_plan", action="update"
        ).first()
        if ongoing_sync:
            ongoing_sync.has_recieved_stripe_webhook = True
            ongoing_sync.save()
            return Response(
                status=status.HTTP_200_OK,
                data={"ok": True, "message": "Synced successfully."},
            )

        # Get the subscription items frpm the request
        request_data = request.data["data"]["object"]
        subscription_items = request_data["items"]["data"]
        try:
            customer_id = request.data["data"]["object"]["customer"]
            customer = Customer.objects.filter(stripe_customer_id=customer_id).first()

            # Delete all service packages that are not in the subscription items
            service_package = ServicePackage.objects.filter(
                stripe_subscription_item_id=subscription_items[0]["id"],
            ).first()

            service_packages = ServicePackage.objects.filter(
                package_plan=service_package.package_plan
            )
            # deleted_ids = []
            for service_package in service_packages:
                if service_package.stripe_subscription_item_id not in [
                    item["id"] for item in subscription_items
                ]:
                    service_package.delete(
                        should_sync_pipedrive=True, should_sync_stripe=False
                    )
            
            for item in subscription_items:
                stripe_subscription_item_id = item["subscription"]
                package_plan = PackagePlan.objects.filter(
                    stripe_subscription_id=stripe_subscription_item_id
                ).first()
                package_template = ServicePackageTemplate.objects.filter(
                    stripe_product_id=item["price"]["product"]
                ).first()
                service_package, created = ServicePackage.objects.get_or_create(
                    stripe_subscription_item_id=item["id"],
                    defaults={
                        'quantity': item["quantity"], 
                        'cost': float(int(item["price"]["unit_amount_decimal"]) / 100),
                        "customer": customer, 
                        "stripe_subscription_item_id": item["id"],
                        "stripe_subscription_item_price_id": item["price"]["id"],
                        "package_plan": package_plan,
                        "package_template": package_template,
                    }
                )
                if not created:
                    print(float(int(item["price"]["unit_amount_decimal"]) / 100))
                    service_package.quantity = item["quantity"]
                    service_package.cost = float(int(item["price"]["unit_amount_decimal"]) / 100)
                    service_package.save(
                        should_sync_pipedrive=True, should_sync_stripe=False
                    )

            


        except Exception as e:
            print('Failed to update the subscription items: ', e)

        return Response(
            status=status.HTTP_200_OK,
            data={"ok": True, "message": "Synced successfully."},
        )


class SubscriptionDeleteWebhook(APIView):
    """API view for deleting a subscription in stripe"""

    # permission_classes = [IsAuthenticated]
    # authentication_classes = [WebhookAuthentication]

    def post(self, request, format=None):
        from .models import StripeSubscription

        # Check if we should stop processing stripe webhooks
        stop_stripe_webhooks = Toggles.objects.filter(name="Toggles").first()
        if stop_stripe_webhooks.stop_stripe_webhooks:
            return Response(
                status=status.HTTP_200_OK,
                data={"ok": True, "message": "Synced successfully."},
            )

        # Get the incoming stripe subscription id
        subscription_id = request.data["data"]["object"]["id"]
        subscription = StripeSubscription.objects.filter(
            stripe_subscription_id=subscription_id
        ).first()
        package_plan = PackagePlan.objects.filter(
            stripe_subscription_id=subscription_id
        ).first()

        # Delete the subscription and package plan
        if subscription:
            subscription.delete()
        if package_plan:
            package_plan.delete()

        return Response(
            status=status.HTTP_200_OK,
            data={"ok": True, "message": "Synced successfully."},
        )
