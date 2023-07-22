import json
import os
import time
from decimal import ROUND_HALF_UP, Decimal

import requests
import stripe
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.custom_auth import WebhookAuthentication
from apps.accounts.models import Customer, Employee, OngoingSync, Toggles
from apps.accounts.serializers import RegisterSerializer
from apps.package_manager.models import (PackagePlan, ServicePackage,
                                         ServicePackageTemplate)
from apps.stripe.models import StripeSubscription
from apps.stripe.utils import setup_payment_details
from .utils import create_pipedrive_webhooks, create_pipedrive_type_fields, create_pipedrive_stripe_url_fields
# from aws_secrets import SECRETS

# Use this code snippet in your app.
# If you need more information about configurations
# or implementing the sample code, visit the AWS docs:
# https://aws.amazon.com/developer/language/python/

import boto3
from botocore.exceptions import ClientError
from apps.accounts.models import Customer

class PipedriveOauth(APIView):
    """
    IN PROGRESS...
    This view will recieve a code from an oauth redirect from pipedrive.
    The code will be used to get an access token, which will be stored with amazon secretcs manager.
    """
    
    def post(self, request):
        # Get the code from the request
        # print('In the requerst..')
        code = request.data.get('code')
        user = request.user
        customer = Customer.objects.get(user=user)
        customer_pk = customer.pk
        print(f'customer_pk: {customer_pk}')
        # print(f'got the code: {code}')
        # Get the pipedrive client id and secret from the environment variables
        client_id = os.environ.get('PIPEDRIVE_CLIENT_ID')
        client_secret = os.environ.get('PIPEDRIVE_CLIENT_SECRET')
        frontend_url = os.environ.get('FRONTEND_URL')
        # Define the URL
        url = 'https://oauth.pipedrive.com/oauth/token'
        # Define the payload
        payload = {
            'grant_type': 'authorization_code',
            'code': code,
            'client_id': client_id,
            'client_secret': client_secret,
            'redirect_uri': f'{frontend_url}/dashboard/'
        }
        response = requests.post(url, data=payload)
        print('Response: ', response.json())
        # print('Response status: ', response.status_code)
        # print('Response content: ', response.content)
        access_token = response.json()['access_token']
        refresh_token = response.json()['refresh_token']
        print(f'access_token: {access_token}')
        print(f'refresh_token: {refresh_token}')
        secret_name = "roseware-secrets"
        region_name = "us-east-2"
        
        # Get the user id from Pipedrive API
        url = 'https://api.pipedrive.com/v1/users/me'
        headers = {'Authorization': f'Bearer {access_token}'}
        response = requests.get(url, headers=headers)
        pipedrive_user_id = response.json()['data']['id']

        # Save the pipedrive_user_id to the customer
        customer.pipedrive_user_id = pipedrive_user_id
        customer.save()

        # Create a Secrets Manager client
        session = boto3.session.Session()
        client = session.client(
            service_name='secretsmanager',
            region_name=region_name
        )
        print(f'client: {client}')

        try:
            env = os.environ.get('DJANGO_ENV')
            get_secret_value_response = client.get_secret_value(
                SecretId=secret_name
            )
            secret_dict = json.loads(get_secret_value_response['SecretString'])
            oauth_tokens = secret_dict["roseware-secrets"][env]["oauth-tokens"]
            customer_key = str(customer_pk)
            
            if customer_key in oauth_tokens:
                print(f"Credentials for customer {customer_key} already exist. Overwriting.")
                
            oauth_tokens[customer_key] = {
                "access_token": access_token,
                "refresh_token": refresh_token,
            }
            client.update_secret(
                SecretId=secret_name,
                SecretString=json.dumps(secret_dict),
            )
            
            
            # Create The Package Plan
            package_plan, created = PackagePlan.objects.get_or_create(
                customer=customer,
                name=f'{customer.first_name} {customer.last_name} - Deal',
                defaults={'status': 'active'}
            )
            setup_payment_details(customer=customer, payment_details={
                "card_number": "4242424242424242",
                "expiry_month": "01",
                "expiry_year": "2025",
                "cvc": "123",
            }, package_plan=package_plan)
            
            package_template = ServicePackageTemplate.objects.get(name="Roseware - Pipedrive Stripe Sync")
            
            service_package = ServicePackage.objects.get_or_create(
                customer=customer, 
                package_template=package_template,
                package_plan=package_plan,
                cost=package_template.cost,
            )
                    
            if not service_package:
                return Response({"ok": False, "message": "Error creating service package."}, status=status.HTTP_400_BAD_REQUEST)

            stripe_subscription = StripeSubscription(
                customer=customer,
                package_plan=package_plan,
            )
            stripe_subscription.save()
            
            # TODO: - Once the access and refresh tokens are stored in aws sectrets manager there are
            # a few more things to set up:
            # pipedrive_stripe_urls_created = create_pipedrive_stripe_url_fields()
            # pipedrive_type_fields_created = create_pipedrive_type_fields()
            # 1. Create the pipedrive webhooks for the customer
            create_pipedrive_webhooks(access_token=access_token, customer=customer)
            # 2: Create the new pipedrieve fields and store them on the customer model
            #    - PIPEDRIVE_PERSON_STRIPE_URL_KEY
            #    - PIPEDRIVE_PRODUCT_STRIPE_URL_KEY
            #    - PIPEDRIVE_DEAL_STRIPE_URL_KEY
            #    - PIPEDRIVE_DEAL_TYPE_FIELD
            #    - PIPEDRIVE_DEAL_SUBSCRIPTION_SELECTOR
            #   -  PIPEDRIVE_DEAL_PAYOUT_SELECTOR
            return Response({"ok": True, "message": "Access token stored successfully."}, status=status.HTTP_200_OK)
            
        except ClientError as e:
            # For a list of exceptions thrown, see
            # https://docs.aws.amazon.com/secretsmanager/latest/apireference/API_GetSecretValue.html
            print('Error: ', e)
            return Response({"ok": False, "message": "Error storing access token."}, status=status.HTTP_400_BAD_REQUEST)


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
            stop_pipedrive_webhooks = Toggles.objects.filter(name='Toggles').first()
            if stop_pipedrive_webhooks.stop_pipedrive_webhooks:
                return Response(status=status.HTTP_200_OK, data={"ok": True, "message": "Synced successfully."})

            # Get the pipedrive id
            request_data = request.data['current']
            pipedrive_id = request_data['id']
            type_split = request_data['name'].split(" ")
            type = type_split[1]
            related_app = type_split[0]
            description = request_data['description']
            unit = request_data['unit']

            # Check if the webhook is being sent as a result of a sync
            ongoing_sync = OngoingSync.objects.filter(type='package_template', action='create').first()
            if ongoing_sync:
                ongoing_sync.has_recieved_pipedrive_webhook = True
                ongoing_sync.save()
                return Response(status=status.HTTP_200_OK, data={"ok": True, "message": "Synced successfully."})

            # Check if the package already exists
            existing_package = ServicePackageTemplate.objects.filter(pipedrive_id=pipedrive_id).first()
            if existing_package:
                return Response(status=status.HTTP_200_OK, data={"ok": True, "message": "Synced successfully."})

            # Create the package
            service_package = ServicePackageTemplate(
                pipedrive_id=pipedrive_id,
                name=request_data['name'],
                description=description,
                unit=int(unit),
                type=type,
                related_app=related_app,
                cost=request_data['prices'][0]['price'],
                last_synced_from="pipedrive",
                original_sync_from="pipedrive"
            )
            service_package.save(should_sync_pipedrive=False, should_sync_stripe=True)
            return Response(status=status.HTTP_200_OK, data={"ok": True})
        except Exception as e:
            print(e)
            return Response(
                status=status.HTTP_400_BAD_REQUEST,
                data={"ok": False, "message": "Failed to process request."}
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
            stop_pipedrive_webhooks = Toggles.objects.filter(name='Toggles').first()
            if stop_pipedrive_webhooks.stop_pipedrive_webhooks:
                return Response(status=status.HTTP_200_OK, data={"ok": True, "message": "Synced successfully."})

            # Get product data from the request
            request_data = request.data["current"]
            pipedrive_id = request_data["id"]
            pipedrive_price = Decimal(str(request_data["prices"][0]["price"])).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            pipedrive_name = request_data["name"]
            description = request_data['description']
            unit = request_data['unit']

            # Get the package template
            package_template = ServicePackageTemplate.objects.filter(pipedrive_id=pipedrive_id).first()

            # Convert package_template.cost to Decimal and quantize
            package_template_cost = Decimal(str(package_template.cost)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

            # Check if the webhook is being sent as a result of a sync
            ongoing_sync = OngoingSync.objects.filter(type='package_template', action='update').first()
            if ongoing_sync:
                ongoing_sync.has_recieved_pipedrive_webhook = True
                ongoing_sync.save()
                if not ongoing_sync.stop_pipedrive_webhook:
                    return Response(status=status.HTTP_200_OK, data={"ok": True, "message": "Synced successfully."})

            # check if request pipedrive_id, name, or cost are different from the existing package template
            # if they are, continue with the update
            is_same_id = int(package_template.pipedrive_id) == int(pipedrive_id)
            is_same_name = package_template.name == pipedrive_name
            is_same_cost = package_template_cost == pipedrive_price
            is_same_description = package_template.description == description
            is_same_unit = package_template.unit == unit
            is_same = is_same_id and is_same_name and is_same_cost and is_same_description and is_same_unit
            if is_same:
                return Response(status=status.HTTP_200_OK, data={"ok": True, "message": "Synced successfully."})

            # Create the package if it doesn't exist
            if not package_template:
                package_template = ServicePackageTemplate(
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
            print(e)
            return Response(status=status.HTTP_400_BAD_REQUEST, data={"ok": False, "message": "Failed to process request."})

class PackageDeleteWebhook(APIView):
    """
    This should run when a product is deleted on Pipedrive.
    It should only modify the Templates, not the actual ServicePackages.
    """
    
    permission_classes = [IsAuthenticated]
    authentication_classes = [WebhookAuthentication]

    def post(self, request):
        try:
            stop_pipedrive_webhooks = Toggles.objects.filter(name='Toggles').first()
            if stop_pipedrive_webhooks.stop_pipedrive_webhooks:
                return Response(status=status.HTTP_200_OK, data={"ok": True, "message": "Synced successfully."})

            webhook_data = request.data
            pipedrive_id = webhook_data['previous']['id']
            package = ServicePackageTemplate.objects.filter(pipedrive_id=pipedrive_id).first()
            package.delete()
            return Response(status=status.HTTP_200_OK, data={"ok": True})
        except Exception as e:
            print(e)
            return Response(status=status.HTTP_400_BAD_REQUEST, data={"ok": False, "message": "Failed to process request."})

class CustomerCreateWebhook(APIView):
    """
    This is the webhook that Pipedrive will send to when a customer is created or updated.
    It should just create, update or delete the customer in our database.
    """
    
    permission_classes = [IsAuthenticated]
    authentication_classes = [WebhookAuthentication]

    def post(self, request):
        try:

            # Simetimes the webhooks come in too fast,
            # so we need to wait a second to make sure the OnGoingSync object is created
            time.sleep(1)

            # Check if we should stop processing pipedrive webhooks
            stop_pipedrive_webhooks = Toggles.objects.filter(name='Toggles').first()
            if stop_pipedrive_webhooks.stop_pipedrive_webhooks:
                return Response(status=status.HTTP_200_OK, data={"ok": True, "message": "Synced successfully."})

            # Get the pipedrive id
            data = json.loads(request.body.decode('utf-8'))
            meta_data = data['meta']
            pipedrive_id = meta_data['id']

            # Check if the webhook is being sent as a result of a sync
            ongoing_sync = OngoingSync.objects.filter(type='customer', action='create').first()
            if ongoing_sync:
                ongoing_sync.has_recieved_pipedrive_webhook = True
                ongoing_sync.save()
                return Response(status=status.HTTP_200_OK, data={"ok": True, "message": "Synced successfully."})

            # Check if the customer already exists
            existing_customer = Customer.objects.filter(pipedrive_id=pipedrive_id).first()
            if existing_customer:
                return Response(status=status.HTTP_200_OK, data={"ok": True, "message": "Synced successfully."})

            # Extract user data from webhook payload
            email = data['current']['email'][0]['value']
            first_name = data['current']['first_name']
            last_name = data['current']['last_name']
            phone = data['current']['phone'][0]['value'] if data['current']['phone'] else None
            password = "markittemppass2023"  # TODO - Set a default password or generate a random one

            #  Create user object using the serializer
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

            # Get the representative TODO - do this better
            representative = Employee.objects.all().first()

            # Create customer object
            customer = Customer(
                user=user,
                pipedrive_id=pipedrive_id,
                rep=representative,
                phone=phone,
            )
            customer.save(should_sync_pipedrive=False, should_sync_stripe=True)
            return Response(status=status.HTTP_200_OK, data={"ok": True})
        except Exception as e:
            print(e)
            return Response(status=status.HTTP_400_BAD_REQUEST, data={"ok": False, "message": "Failed to process request."})


class CustomerSyncWebhook(APIView):
    """
    This is the webhook that Pipedrive will send to when a customer is created or updated.
    Is should just create, update or delete the customer in our database.
    """
    
    permission_classes = [IsAuthenticated]
    authentication_classes = [WebhookAuthentication]

    def post(self, request):
        try:
            print('Im the webhook...')
            # Simetimes the webhooks come in too fast,
            # so we need to wait a second to make sure the OnGoingSync object is created
            time.sleep(1)
            # Check if we should stop processing pipedrive webhooks
            print('checking toggles...')
            stop_pipedrive_webhooks = Toggles.objects.filter(name='Toggles').first()
            if stop_pipedrive_webhooks.stop_pipedrive_webhooks:
                return Response(status=status.HTTP_200_OK, data={"ok": True, "message": "Synced successfully."})

            print('getting data...')
            request_data = request.data
            pipedrive_id = request_data["current"]["id"]
            customer = Customer.objects.filter(pipedrive_id=pipedrive_id).first()

            print('checking for ongoing sync...')
            # Check if the webhook is being sent as a result of a sync
            ongoing_sync = OngoingSync.objects.filter(type='customer', action='update').first()
            if ongoing_sync:
                ongoing_sync.has_recieved_pipedrive_webhook = True
                ongoing_sync.save()
                return Response(status=status.HTTP_200_OK, data={"ok": True, "message": "Synced successfully."})

            print('Setting customer data...')
            pipedrive_email = request_data['current']['email'][0]['value']
            pipedrive_first_name = request_data['current']['first_name']
            pipedrive_last_name = request_data['current']['last_name']
            pipedrive_phone = request_data['current']['phone'][0]['value'] if request_data['current']['phone'] else None

            # Check if the customer data is the same as the data in the webhook
            # If it is, then we don't need to update the customer
            print('checking if customer data is the same...')
            try:
                is_first_name_same = customer.first_name == pipedrive_first_name
                is_last_name_same = customer.last_name == pipedrive_last_name
                is_email_same = customer.email == pipedrive_email
                if customer.phone is None and pipedrive_phone == 'None':
                    is_phone_same = True
                else:
                    is_phone_same = customer.phone == pipedrive_phone
                is_same = is_first_name_same and is_last_name_same and is_email_same and is_phone_same
                if is_same:
                    return Response(status=status.HTTP_200_OK, data={"ok": True, "message": "Synced successfully."})
            except Exception as e:
                print(e)
                return Response(status=status.HTTP_400_BAD_REQUEST, data={"ok": False, "message": "Failed to process request."})

            # Update customer data
            print('updating customer data...')
            customer.first_name = request_data["current"]["first_name"]
            customer.last_name = request_data["current"]["last_name"]
            customer.email = request_data["current"]["email"][0]["value"]
            customer.phone = request_data["current"]["phone"][0]["value"]
            print('saving customer...')
            customer.save(should_sync_pipedrive=False)

            return Response(status=status.HTTP_200_OK, data={"ok": True})
        except Exception as e:
            print(e)
            return Response(status=status.HTTP_400_BAD_REQUEST, data={"ok": False, "message": "Failed to process request."})

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
            stop_pipedrive_webhooks = Toggles.objects.filter(name='Toggles').first()
            if stop_pipedrive_webhooks.stop_pipedrive_webhooks:
                return Response(status=status.HTTP_200_OK, data={"ok": True, "message": "Synced successfully."})

            meta_data = request.data['meta']
            pipedrive_id = meta_data['id']
            customer = Customer.objects.filter(pipedrive_id=pipedrive_id).first()
            customer.delete()
            return Response(status=status.HTTP_200_OK, data={"ok": True})
        except Exception as e:
            print(e)
            return Response(status=status.HTTP_400_BAD_REQUEST, data={"ok": False, "message": "Failed to process request."})

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
            stop_pipedrive_webhooks = Toggles.objects.filter(name='Toggles').first()
            if stop_pipedrive_webhooks.stop_pipedrive_webhooks:
                return Response(status=status.HTTP_200_OK, data={"ok": True, "message": "Synced successfully."})

            # Get the pipedrive id
            request_data = request.data['current']
            pipedrive_id = request_data['id']

            # Get the customer associated with this deal
            customer_pipedrive_id = request_data['person_id']
            customer = Customer.objects.filter(pipedrive_id=customer_pipedrive_id).first()
            if not customer:
                return Response(status=status.HTTP_400_BAD_REQUEST, data={"ok": False, "message": "No customer found with this pipedrive id."})

            # Check if the webhook is being sent as a result of a sync
            ongoing_sync = OngoingSync.objects.filter(type='package_plan', action='create').first()
            # print('\nChecking pipedrive webhook sync: ')
            if ongoing_sync:
                # print(f'\nSTOPPING PIPEDRIVE DEAL CREATE WEBHOOK: {ongoing_sync}')
                ongoing_sync.has_recieved_pipedrive_webhook = True
                ongoing_sync.save()
                return Response(status=status.HTTP_200_OK, data={"ok": True, "message": "Synced successfully."})

            # Check if the package already exists
            # print('Checking if package already exists in the database')
            existing_package = PackagePlan.objects.filter(pipedrive_id=pipedrive_id).first()
            if existing_package:
                print('Package already exists in the database: ', existing_package)
                return Response(status=status.HTTP_200_OK, data={"ok": True})

            # Create the package
            service_package = PackagePlan(
                pipedrive_id=pipedrive_id,
                customer=customer,
                name=request_data['title'],
                # status=deal_status,
                # type=type_value.lower() if type_value is not None else None,
            )

            service_package.save(should_sync_pipedrive=False, should_sync_stripe=False)

            return Response(status=status.HTTP_200_OK, data={"ok": True})
        except Exception as e:
            print(e)
            return Response(status=status.HTTP_400_BAD_REQUEST, data={"ok": False, "message": "Failed to process request."})

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

        # **** BUG - There is an initial sync race condition where this webhook is called before subscription_item_ids are saved on new packages
        # This is a grat reason to start the Sync-object next...

        def is_data_same(package_plan, request_data, deal_products):

            # Compare the name and status fields
            if package_plan.name != request_data['title']:
                return False

            # Compare the products
            service_package_products = ServicePackage.objects.filter(package_plan=package_plan)
            if len(service_package_products) != len(deal_products):
                return False

            # Compare the products
            service_package_list = list(service_package_products.values())
            for deal_product in deal_products:
                # Check if the product exists in the service_package_list
                matching_service_package = None
                for service_package in service_package_list:
                    if str(deal_product['id']) == service_package['pipedrive_product_attachment_id']:
                        matching_service_package = service_package
                        break

                if matching_service_package is None:
                    return False

                if float(deal_product['item_price']) != float(matching_service_package['cost']):
                    return False

                if deal_product['quantity'] != matching_service_package['quantity']:
                    return False

            return True

        try:
            # Simetimes the webhooks come in too fast,
            # so we need to wait a second to make sure the OnGoingSync object is created
            time.sleep(1)

            # Check if we should stop processing pipedrive webhooks
            stop_pipedrive_webhooks = Toggles.objects.filter(name='Toggles').first()
            if stop_pipedrive_webhooks.stop_pipedrive_webhooks:
                return Response(status=status.HTTP_200_OK, data={"ok": True, "message": "Synced successfully."})
            
            # Check if the webhook is being sent as a result of a sync
            ongoing_sync = OngoingSync.objects.filter(type='package_plan', action='update').first()
            if ongoing_sync:
                ongoing_sync.has_recieved_pipedrive_webhook = True
                ongoing_sync.save()
                return Response(status=status.HTTP_200_OK, data={"ok": True, "message": "Synced successfully."})

            # Get the pipedrive data
            pipedrive_key = os.environ.get('PIPEDRIVE_API_KEY')
            pipedrive_domain = os.environ.get('PIPEDRIVE_DOMAIN')
            request_data = request.data['current']
            pipedrive_id = request_data['id']

            # Check if the PackagePlan exists
            package_plan = PackagePlan.objects.filter(pipedrive_id=pipedrive_id).first()
            if not package_plan:
                return Response(status=status.HTTP_400_BAD_REQUEST, data={"ok": False, "message": "No service package found with this pipedrive id."})
            
            # Update package plan details
            package_plan.name = request_data['title']
            field_key = os.environ.get("PIPEDRIVE_DEAL_TYPE_FIELD")
            type_value = request_data[f'{field_key}']
            print('type_value: ', type_value)
            if type_value == None:
                package_plan.status = 'lost'
            else:
                package_plan.status = request_data['status']
            package_plan.type = type_value.lower() if type_value is not None else None

            # Get the products from the deal and return if there are no changes
            url = f'https://{pipedrive_domain}.pipedrive.com/v1/deals/{package_plan.pipedrive_id}/products?api_token={pipedrive_key}'
            response = requests.get(url)
            deal_products = response.json()['data']
            if is_data_same(package_plan, request_data, deal_products):
                return Response(status=status.HTTP_200_OK, data={"ok": True, "message": "Data is the same, no need to update."})
            
            # Delete all ServicePackage objects that are not in the products list
            service_package_products = ServicePackage.objects.filter(package_plan=package_plan)
            if service_package_products:
                products_ids = [product['id'] for product in deal_products]
                for service_package_product in service_package_products:
                    if service_package_product.pipedrive_product_attachment_id not in str(products_ids):
                        service_package_product.delete(should_sync_pipedrive=False)

            # Add all products to the ServicePackage
            for product in deal_products:
                pipedrive_product_attachment_id = product['id']
                service_package = ServicePackage.objects.filter(pipedrive_product_attachment_id=pipedrive_product_attachment_id).first()
                if not service_package:
                    product_id = product['product_id']
                    package_template = ServicePackageTemplate.objects.filter(pipedrive_id=product_id).first()
                    service_package = ServicePackage(
                        pipedrive_product_attachment_id=pipedrive_product_attachment_id,
                        package_plan=package_plan,
                        customer=package_plan.customer,
                        package_template=package_template,
                        cost=product['item_price'],
                        quantity=product['quantity'],
                    )
                    service_package.save(should_sync_pipedrive=False, should_sync_stripe=True)

            # Check if the customer has a payment method setup in Stripe
            stripe.api_key = os.environ.get('STRIPE_PRIVATE')
            customer_id = package_plan.customer.stripe_customer_id
            try:
                customer = stripe.Customer.retrieve(customer_id)
                payment_methods = customer["default_source"]
                if len(deal_products) > 0 and not payment_methods:
                    package_plan.status = 'lost'
                    package_plan.save(should_sync_pipedrive=True, should_sync_stripe=False)
                    return Response(status=status.HTTP_400_OK, data={"ok": True, "message": "No payment method found for this customer."})
            except stripe.error.StripeError as e:
                return Response(status=status.HTTP_500_INTERNAL_SERVER_ERROR, data={"ok": False, "message": "Failed to retrieve customer payment methods."})

            # Set up the Stripe Subscription or Payout
            subscription_selector = os.environ.get("PIPEDRIVE_DEAL_SUBSCRIPTION_SELECTOR")
            payout_selector = os.environ.get("PIPEDRIVE_DEAL_PAYOUT_SELECTOR")
            print('type_value: ', type_value)
            print('subscription_selector: ', subscription_selector)
            if type_value == str(subscription_selector):
                stripe_subscription = StripeSubscription.objects.filter(customer=package_plan.customer).first()
                if stripe_subscription:
                    subscription_pk = stripe_subscription.pk
                    sync_stripe.delay(subscription_pk, 'update', 'subscription')
                    return Response(status=status.HTTP_200_OK, data={"ok": True})
                else:
                    stripe_subscription = StripeSubscription(
                        customer=package_plan.customer,
                        package_plan=package_plan,
                    )
                    stripe_subscription.save()
                    return Response(status=status.HTTP_200_OK, data={"ok": True})
            elif type_value == str(payout_selector):
                print('** Creating Stripe Payout...')
                return Response(status=status.HTTP_200_OK, data={"ok": True})
            else:
                package_plan.status = 'lost'
                package_plan.save(should_sync_pipedrive=True, should_sync_stripe=False)
                return Response(status=status.HTTP_400_OK, data={"ok": False, "message": "Unknown deal type."})

        except Exception as e:
            print(e)
            return Response(status=status.HTTP_400_BAD_REQUEST, data={"ok": False, "message": "Failed to process request."})

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
            stop_pipedrive_webhooks = Toggles.objects.filter(name='Toggles').first()
            if stop_pipedrive_webhooks.stop_pipedrive_webhooks:
                return Response(status=status.HTTP_200_OK, data={"ok": True, "message": "Synced successfully."})

            webhook_data = request.data
            pipedrive_id = webhook_data['previous']['id']
            service_package = PackagePlan.objects.filter(pipedrive_id=pipedrive_id).first()
            service_package.delete()
            return Response(status=status.HTTP_200_OK, data={"ok": True})
        except Exception as e:
            print(e)
            return Response(status=status.HTTP_400_BAD_REQUEST, data={"ok": False, "message": "Failed to process request."})
