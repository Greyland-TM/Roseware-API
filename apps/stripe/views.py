import os
import time
from decimal import ROUND_HALF_UP, Decimal

# import requests
import stripe
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.custom_auth import WebhookAuthentication
from apps.accounts.models import Customer, Employee, OngoingSync, Toggles
from apps.package_manager.models import (PackagePlan, ServicePackage,
                                         ServicePackageTemplate)

stripe.api_key = os.environ.get('STRIPE_PRIVATE')

class ProductCreateWebhook(APIView):
    """ API view for creating a new product in stripe """

    # permission_classes = [IsAuthenticated]
    # authentication_classes = [WebhookAuthentication]

    def post(self, request, format=None):
        # Simetimes the webhooks come in too fast,
        # so we need to wait a second to make sure the OnGoingSync object is created
        time.sleep(1)

        # Check if we should stop processing stripe webhooks
        stop_stripe_webhooks = Toggles.objects.filter(name='Toggles').first()
        if stop_stripe_webhooks.stop_stripe_webhooks:
            return Response(status=status.HTTP_200_OK, data={"ok": True, "message": "Synced successfully."})

        # # Check for any on going sync objects
        ongoing_sync = OngoingSync.objects.filter(type='package_template', action='create').first()
        if ongoing_sync:
            ongoing_sync.has_recieved_stripe_webhook = True
            ongoing_sync.save()
            if not ongoing_sync.stop_stripe_webhook:
                return Response(status=status.HTTP_200_OK, data={"ok": True, "message": "Synced successfully."})
        try:
            # Create a new package template
            product_id = request.data['data']['object']['id']
            product_name = request.data['data']['object']['name']
            product_description = request.data['data']['object']['description']
            split_related_app = product_name.split(' ')
            related_app = split_related_app[0].lower()
            type = split_related_app[1].lower()

            # Check for an existing package template
            existing_package_template = ServicePackageTemplate.objects.filter(stripe_product_id=product_id).first()
            if existing_package_template:
                existing_package_template.save(should_sync_pipedrive=False, should_sync_stripe=False)
                return Response(status=status.HTTP_200_OK, data={"ok": True, "message": "Synced successfully."})

            new_package_template = ServicePackageTemplate(
                name=product_name,
                description=product_description,
                related_app=related_app,
                type=type,
                stripe_product_id=product_id,
                requires_onboarding=False,
                last_synced_from='stripe',
                original_sync_from='stripe'
            )
            new_package_template.save(should_sync_pipedrive=True, should_sync_stripe=False)
            return Response(status=status.HTTP_200_OK, data={"ok": True, "message": "Synced successfully."})
        except Exception as e:
            print(f'ERROR: {e}')
            return Response(status=status.HTTP_400_BAD_REQUEST, data={"ok": False, "message": "Failed to process request."})

class ProductSyncWebhook(APIView):
    """ API view for syncing a product in stripe """

    # permission_classes = [IsAuthenticated]
    # authentication_classes = [WebhookAuthentication]

    def post(self, request, format=None):
        # Simetimes the webhooks come in too fast,
        # so we need to wait a second to make sure the OnGoingSync object is created
        time.sleep(1)

        # Check if we should stop processing stripe webhooks
        stop_stripe_webhooks = Toggles.objects.filter(name='Toggles').first()
        if stop_stripe_webhooks.stop_stripe_webhooks:
            return Response(status=status.HTTP_200_OK, data={"ok": True, "message": "Synced successfully."})

        # # Check for any on going sync objects
        ongoing_sync = OngoingSync.objects.filter(type='package_template', action='update').first()
        if ongoing_sync:
            ongoing_sync.has_recieved_stripe_webhook = True
            ongoing_sync.save()
            if not ongoing_sync.stop_stripe_webhook:
                return Response(status=status.HTTP_200_OK, data={"ok": True, "message": "Synced successfully."})

        product_id = request.data['data']['object']['id']
        product = ServicePackageTemplate.objects.filter(stripe_product_id=product_id).first()

        # Chaeck if the price has changed
        if product:

            stripe.api_key = os.environ.get('STRIPE_PRIVATE')
            price_id = request.data['data']['object']['default_price']

            try:
                # Get the stripe price
                if price_id is None:
                    stripe_price_response = stripe.Price.list(product=product_id)
                    stripe_price = stripe_price_response['data'][0]['unit_amount_decimal']
                    price_id = stripe_price_response['data'][0]['id']
                    unit_amount_decimal = stripe_price_response['data'][0]['unit_amount_decimal']
                    stripe_price_cents = Decimal(str(unit_amount_decimal))
                    stripe_price = (stripe_price_cents / 100).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
                else:
                    price = stripe.Price.retrieve(price_id)
                    stripe_price_cents = Decimal(str(price["unit_amount_decimal"]))
                    stripe_price = (stripe_price_cents / 100).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

                if stripe_price != product.cost:
                    product.cost = stripe_price
                    product.stripe_price_id = price_id

            except Exception as e:
                print(f'ERROR: {e}')
                return Response(status=status.HTTP_400_BAD_REQUEST, data={"ok": False, "message": "Failed to process request."})

            # Update the product
            product_name = request.data['data']['object']['name']
            product_description = request.data['data']['object']['description']
            product.name = product_name
            product.description = product_description
            product.last_synced_from = 'stripe'
            product.original_sync_from = 'stripe'
            product.save(should_sync_pipedrive=True, should_sync_stripe=False)

        return Response(status=status.HTTP_200_OK, data={"ok": True, "message": "Synced successfully."})

class ProductDeleteWebhook(APIView):
    """ API view for syncing a product in stripe """

    # permission_classes = [IsAuthenticated]
    # authentication_classes = [WebhookAuthentication]

    def post(self, request, format=None):

        # Check if we should stop processing stripe webhooks
        stop_stripe_webhooks = Toggles.objects.filter(name='Toggles').first()
        if stop_stripe_webhooks.stop_stripe_webhooks:
            return Response(status=status.HTTP_200_OK, data={"ok": True, "message": "Synced successfully."})

        product_id = request.data['data']['object']['id']
        product = ServicePackageTemplate.objects.filter(stripe_product_id=product_id).first()
        if product:
            product.delete(should_sync_stripe=False, should_sync_pipedrive=True)

        return Response(status=status.HTTP_200_OK, data={"ok": True, "message": "Synced successfully."})

class CustomerCreateWebhook(APIView):
    """ API view for syncing a customer in stripe """

    # permission_classes = [IsAuthenticated]
    # authentication_classes = [WebhookAuthentication]

    def post(self, request, format=None):
        from apps.accounts.serializers import RegisterSerializer

        print('*** Stripe CustomerCreateWebhook ***')
        # Simetimes the webhooks come in too fast,
        # so we need to wait a second to make sure the OnGoingSync object is created
        print(f'IN THE CUSTOMER CREATE WEBHOOK - {request.data}')
        time.sleep(1)

        # Check if we should stop processing stripe webhooks
        stop_stripe_webhooks = Toggles.objects.filter(name='Toggles').first()
        if stop_stripe_webhooks.stop_stripe_webhooks:
            return Response(status=status.HTTP_200_OK, data={"ok": True, "message": "Synced successfully."})

        # # Check for any on going sync objects
        ongoing_sync = OngoingSync.objects.filter(type='customer', action='create').first()
        if ongoing_sync:
            ongoing_sync.has_recieved_stripe_webhook = True
            ongoing_sync.save()
            if not ongoing_sync.stop_stripe_webhook:
                return Response(status=status.HTTP_200_OK, data={"ok": True, "message": "Synced successfully."})

        # Check if the customer already exists
        print('Checking Customer...')
        stripe_customer = request.data['data']['object']
        customer_id = request.data['data']['object']['id']
        print(f'customer_id: {customer_id}')
        customer = Customer.objects.filter(stripe_customer_id=customer_id).first()
        print(f'customer: {customer}')
        if customer:
            return Response(status=status.HTTP_200_OK, data={"ok": True, "message": "Customer Already Exists...."})

        # Setup the new user
        print("customer doesnt exists, create it...")
        rep = Employee.objects.all().first()
        email = stripe_customer['email']
        phone = stripe_customer.get('phone', '')
        name_split = stripe_customer.get('name', '').split(' ')
        first_name = name_split[0] if len(name_split) > 0 else ''
        last_name = ' '.join(name_split[1:]) if len(name_split) > 1 else ''
        password = "markittemppass2023"  # TODO - Set a default password or generate a random one
        print(f'phone: {phone}')
        print(f'email: {email}')
        try:
            serializer_data = {"first_name": first_name, "last_name": last_name, "username": email, "email": email, "password": password}
            serializer = RegisterSerializer(data=serializer_data)
            serializer.is_valid(raise_exception=True)
            if serializer.is_valid():
                user = serializer.save()
            else:
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            print(e)
            return Response(status=status.HTTP_400_BAD_REQUEST, data={"ok": False, "message": "Failed to process request."})

        # Create the customer
        customer = Customer(
            user=user,
            phone=phone,
            rep=rep,
            stripe_customer_id=customer_id,
            last_synced_from='stripe',
            original_sync_from='stripe',
        )
        customer.save(should_sync_pipedrive=True, should_sync_stripe=False)
        print(f'customer: {customer}')

        return Response(status=status.HTTP_200_OK, data={"ok": True, "message": "Synced successfully."})

class CustomerSyncWebhook(APIView):
    """ API view for syncing a customer in stripe """

    # permission_classes = [IsAuthenticated]
    # authentication_classes = [WebhookAuthentication]

    def post(self, request, format=None):
        print('*** CustomerSyncWebhook ***')
        print(request.data)

        # Check if we should stop processing stripe webhooks
        stop_stripe_webhooks = Toggles.objects.filter(name='Toggles').first()
        if stop_stripe_webhooks.stop_stripe_webhooks:
            return Response(status=status.HTTP_200_OK, data={"ok": True, "message": "Synced successfully."})

        # # Check for any on going sync objects
        ongoing_sync = OngoingSync.objects.filter(type='customer', action='update').first()
        if ongoing_sync:
            ongoing_sync.has_recieved_stripe_webhook = True
            ongoing_sync.save()
            if not ongoing_sync.stop_stripe_webhook:
                return Response(status=status.HTTP_200_OK, data={"ok": True, "message": "Synced successfully."})

        # get the customer stripe id from the webhook
        print('Getting the suctomers stripe id...')
        customer_stripe_data = request.data['data']['object']
        print('customer_stripe_data: ', customer_stripe_data)
        customer_id = customer_stripe_data['id']
        stripe_phone = customer_stripe_data.get('phone', '')
        name_split = customer_stripe_data.get('name', '').split(' ')
        stripe_fist_name = name_split[0] if len(name_split) > 0 else ''
        stripe_last_name = ' '.join(name_split[1:]) if len(name_split) > 1 else ''
        stripe_email = customer_stripe_data['email']

        # get the customer from the db
        customer = Customer.objects.filter(stripe_customer_id=customer_id).first()

        # Check if any of the fields have changed
        try:
            is_first_name_same = customer.first_name == stripe_fist_name
            is_last_name_same = customer.last_name == stripe_last_name
            is_email_same = customer.email == stripe_email
            is_phone_same = customer.phone == stripe_phone
            is_same = is_first_name_same and is_last_name_same and is_email_same and is_phone_same
            if is_same:
                return Response(status=status.HTTP_200_OK, data={"ok": True, "message": "Synced successfully."})
        except Exception as e:
            print(e)
            return Response(status=status.HTTP_400_BAD_REQUEST, data={"ok": False, "message": "Failed to process request."})

        # Update the customer
        customer.first_name = stripe_fist_name
        customer.last_name = stripe_last_name
        customer.email = stripe_email
        customer.phone = stripe_phone
        customer.last_synced_from = 'stripe'
        customer.save(should_sync_pipedrive=True, should_sync_stripe=False)

        return Response(status=status.HTTP_200_OK, data={"ok": True, "message": "Synced successfully."})

class CustomerDeleteWebhook(APIView):
    """ API view for syncing a customer in stripe """
    
    # permission_classes = [IsAuthenticated]
    # authentication_classes = [WebhookAuthentication]

    def post(self, request, format=None):
        print('*** CustomerDeleteWebhook ***')
        # print(request.data)

        # Check if we should stop processing stripe webhooks
        stop_stripe_webhooks = Toggles.objects.filter(name='Toggles').first()
        if stop_stripe_webhooks.stop_stripe_webhooks:
            return Response(status=status.HTTP_200_OK, data={"ok": True, "message": "Synced successfully."})

        customer_id = request.data['data']['object']['id']
        customer = Customer.objects.filter(stripe_customer_id=customer_id).first()
        if customer:
            customer.delete()

        return Response(status=status.HTTP_200_OK, data={"ok": True, "message": "Synced successfully."})


class SubscriptionCreateWebhook(APIView):
    """ API view for syncing a subscription in stripe """

    # permission_classes = [IsAuthenticated]
    # authentication_classes = [WebhookAuthentication]

    def post(self, request, format=None):
        from apps.package_manager.utils import create_service_packages
        print('*** SubscriptionCreateWebhook ***')
        # print(request.data)

        # Check if we should stop processing stripe webhooks
        stop_stripe_webhooks = Toggles.objects.filter(name='Toggles').first()
        if stop_stripe_webhooks.stop_stripe_webhooks:
            return Response(status=status.HTTP_200_OK, data={"ok": True, "message": "Synced successfully."})

        # # Check for any on going sync objects
        ongoing_sync = OngoingSync.objects.filter(type='package_plan', action='create').first()
        if ongoing_sync:
            ongoing_sync.has_recieved_stripe_webhook = True
            # print('* Stopped processing stripe webhook because of ongoing sync.')
            ongoing_sync.save()
            return Response(status=status.HTTP_200_OK, data={"ok": True, "message": "Synced successfully."})

        # Get the subscription id and customer id
        subscription_id = request.data['data']['object']['id']
        customer_id = request.data['data']['object']['customer']
        items = request.data['data']['object']['items']['data']
        product_details = []
        subscription = request.data['data']['object']
        items = subscription['items']['data']

        for item in items:
            product_id = item['price']['product']
            price_id = item['price']['id']
            price_value = item['price']['unit_amount']
            product = stripe.Product.retrieve(product_id)
            product_name = product['name']
            product_details.append((product_id, price_id, price_value, product_name))

        # Check if the customer exists
        customer = Customer.objects.filter(stripe_customer_id=customer_id).first()
        if not customer:
            print('*** Customer not found ***')
            # TODO - Create a new customer
            return Response(status=status.HTTP_200_OK, data={"ok": True, "message": "Synced successfully."})

        # Check if the package plan already exists
        package_plan = PackagePlan.objects.filter(stripe_subscription_id=subscription_id).first()
        if package_plan:
            # print('*** Package plan already exists ***')
            return Response(status=status.HTTP_200_OK, data={"ok": True, "message": "Synced successfully."})

        package_plan = {
            'billing_cycle': subscription['plan']['interval'],
            'status': subscription['status'],
            'description': "New Customer Package Plan",
            'stripe_subscription_id': subscription_id,
            'packages': [],
        }

        for item in items:
            product_id = item['price']['product']
            price_id = item['price']['id']
            price_value = item['price']['unit_amount'] / 100
            product = stripe.Product.retrieve(product_id)
            product_name = product['name']
            requires_onboarding = False
            # split product name in 2 parts, at the first space, and use the first part as the related_app and the second as the type
            related_app = product_name.split(' ', 1)[0]
            type = product_name.split(' ', 1)[1]

            package = {
                'stripe_product_id': product_id,
                'stripe_price_id': price_id,
                'name': product_name,
                'price': price_value,
                'related_app': related_app,
                'type': type,
                'requires_onboarding': requires_onboarding
            }
            package_plan['packages'].append(package)

            # Create the service packages
            create_service_packages(customer, package_plan, True, False)

        return Response(status=status.HTTP_200_OK, data={"ok": True, "message": "Synced successfully."})

class SubscriptionSyncWebhook(APIView):
    """ API view for syncing a subscription in stripe """

    # permission_classes = [IsAuthenticated]
    # authentication_classes = [WebhookAuthentication]

    def post(self, request, format=None):
        print('*** SubscriptionSyncWebhook ***')
        # print(request.data)

        # Check if we should stop processing stripe webhooks
        stop_stripe_webhooks = Toggles.objects.filter(name='Toggles').first()
        if stop_stripe_webhooks.stop_stripe_webhooks:
            return Response(status=status.HTTP_200_OK, data={"ok": True, "message": "Synced successfully."})

        # Check for any on going sync objects
        ongoing_sync = OngoingSync.objects.filter(type='package_plan', action='update').first()
        if ongoing_sync:
            ongoing_sync.has_recieved_stripe_webhook = True
            ongoing_sync.save()
            return Response(status=status.HTTP_200_OK, data={"ok": True, "message": "Synced successfully."})

        # Get the subscription items frpm the request
        request_data = request.data['data']['object']
        subscription_items = request_data['items']['data']

        # Check each subscription item and update the quantity - More values can be added here later
        for item in subscription_items:
            service_package = ServicePackage.objects.filter(stripe_subscription_item_id=item['id']).first()
            if service_package:
                service_package.quantity = item['quantity']
                service_package.save(should_sync_pipedrive=True, should_sync_stripe=False)

        return Response(status=status.HTTP_200_OK, data={"ok": True, "message": "Synced successfully."})

class SubscriptionDeleteWebhook(APIView):
    """ API view for deleting a subscription in stripe """

    # permission_classes = [IsAuthenticated]
    # authentication_classes = [WebhookAuthentication]

    def post(self, request, format=None):
        from .models import StripeSubscription

        # Check if we should stop processing stripe webhooks
        stop_stripe_webhooks = Toggles.objects.filter(name='Toggles').first()
        if stop_stripe_webhooks.stop_stripe_webhooks:
            return Response(status=status.HTTP_200_OK, data={"ok": True, "message": "Synced successfully."})

        # Get the incoming stripe subscription id
        subscription_id = request.data['data']['object']['id']
        subscription = StripeSubscription.objects.filter(stripe_subscription_id=subscription_id).first()
        package_plan = PackagePlan.objects.filter(stripe_subscription_id=subscription_id).first()

        # Delete the subscription and package plan
        if subscription:
            subscription.delete()
        if package_plan:
            package_plan.delete()

        return Response(status=status.HTTP_200_OK, data={"ok": True, "message": "Synced successfully."})