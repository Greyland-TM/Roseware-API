import json
import os
import boto3
import requests
import base64
from apps.accounts.models import Customer

def set_pipedrive_keys(customer_pk, access_token, refresh_token):
    # Create a Secrets Manager client
    secret_name = "roseware-secrets"
    region_name = "us-east-2"
    session = boto3.session.Session()
    client = session.client(
        service_name='secretsmanager',
        region_name=region_name
    )
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

def refresh_pipedrive_tokens(customer_pk, refresh_token):
    try:
        client_id = os.environ.get('PIPEDRIVE_CLIENT_ID')
        client_secret = os.environ.get('PIPEDRIVE_CLIENT_SECRET')
        authorization_string = f'{client_id}:{client_secret}'
        base64_bytes = base64.b64encode(authorization_string.encode())
        url = 'https://oauth.pipedrive.com/oauth/token'
        body = {
            "grant_type": "refresh_token",
            "refresh_token": refresh_token
        }
        headers = {
            "Authorization": "Basic " + base64_bytes.decode(),
        }
        response = requests.post(url, data=body, headers=headers)
        data = response.json()
        set_pipedrive_keys(customer_pk, data['access_token'], data['refresh_token'])
        print('Refreshed tokens successfully!')
        return data
    except Exception as error:
        print(error)
        return False

def create_pipedrive_stripe_url_fields(customer_pk):
    """ THIS CODE WORKS FOR SETTING ALL THE STRIPE URL FIELDS """
    try:
        customer = Customer.objects.get(pk=customer_pk)
        pipedrive_domain = customer.piprdrive_api_url
        data = {
            'name': 'stripe url',
            'field_type': 'varchar'
        }

        # Initialize the AWS Secrets Manager client
        secret_name = "roseware-secrets"
        region_name = "us-east-2"
        session = boto3.session.Session()
        client = session.client(
            service_name='secretsmanager',
            region_name=region_name
        )

        # Get the access and refresh tokens
        try:
            response = client.get_secret_value(
                SecretId=secret_name
            )
        except Exception as e:
            print("Error retrieving tokens: ", e)
            return False

        env = os.environ.get('DJANGO_ENV')
        secrets = json.loads(response['SecretString'])
        access_token = secrets["roseware-secrets"][env]["oauth-tokens"][str(customer_pk)]['access_token']
        refresh_token = secrets["roseware-secrets"][env]["oauth-tokens"][str(customer_pk)]['refresh_token']
        headers = {
            'Authorization': f'Bearer {access_token}',
        }

        try:
            # Add stripe_url field to dealFields
            url = f'{pipedrive_domain}/v1/dealFields'
            response = requests.post(url, data, headers=headers)
            deal_key = response.json()['data']['key']

            # Add stripe_url field to personFields
            url = f'{pipedrive_domain}/v1/personFields'
            response = requests.post(url, data=data, headers=headers)
            person_key = response.json()['data']['key']

            # Add stripe_url field to productFields
            url = f'{pipedrive_domain}/v1/productFields'
            response = requests.post(url, data=data, headers=headers)
            product_key = response.json()['data']['key']
        except Exception as error:
            new_tokens = refresh_pipedrive_tokens(customer_pk, refresh_token)
            if new_tokens:
                create_pipedrive_stripe_url_fields(customer_pk)
                return True
            else:
                return False

        # Print the keys
        customer.PIPEDRIVE_PERSON_STRIPE_URL_KEY = person_key
        customer.PIPEDRIVE_DEAL_STRIPE_URL_KEY = deal_key
        customer.PIPEDRIVE_PRODUCT_STRIPE_URL_KEY = product_key
        customer.save(should_sync_stripe=False, should_sync_pipedrive=False)
        print('Created stripe url fields in pipedrive successfully!')

    except Exception as error:
        print(f"Failed to create custom fields: {error}")
        return

def create_pipedrive_type_fields(customer_pk):
    """ THIS CODE CREATES ALL OF THE PIPEFDRIVE CUSTOM FIELDS """

    try:
        # pipedrive_api_key = os.environ.get('PIPEDRIVE_API_KEY')
        pipedrive_domain = os.environ.get('PIPEDRIVE_DOMAIN')
        customer = Customer.objects.get(pk=customer_pk)

        # Setup the pipedrive_field_data array that will be used for making the new fields
        choices = ['Subscription', 'One Time']
        statuses = ['Invoice Approval', 'Process Immediately']
        options_choices = [{'label': choice, 'active': True} for choice in choices]
        options_statuses = [{'label': status, 'active': True} for status in statuses]
        payment_label = 'Payment Selection'
        processing_label = 'Processing Selection'
        pipedrive_field_data = [
            {
                'name': payment_label,
                'field_type': 'enum',
                'options': options_choices
            },
            {
                'name': processing_label,
                'field_type': 'enum',
                'options': options_statuses
            }
        ]

        # Initialize the AWS Secrets Manager client
        secret_name = "roseware-secrets"
        region_name = "us-east-2"
        session = boto3.session.Session()
        client = session.client(
            service_name='secretsmanager',
            region_name=region_name
        )

        # Get the access and refresh tokens
        try:
            response = client.get_secret_value(
                SecretId=secret_name
            )
        except Exception as e:
            print("Error retrieving tokens: ", e)
            return False

        env = os.environ.get('DJANGO_ENV')
        secrets = json.loads(response['SecretString'])
        access_token = secrets["roseware-secrets"][env]["oauth-tokens"][str(customer_pk)]['access_token']
        headers = {
            'Authorization': f'Bearer {access_token}',
        }
        url = f'https://{pipedrive_domain}.pipedrive.com/v1/dealFields'

        # Create the new fields in pipedrive
        for field in pipedrive_field_data:
            response = requests.post(url, json=field, headers=headers)
            data = response.json()
            if not data['success'] or data['success'] == False:
                return False
            field_id = data['data']['id']
            field_name = data['data']['name']

            # Make the newly create fields visable and reauired in pipedreive
            if field_id:
                headers = {
                    'Authorization': f'Bearer {access_token}',
                }
                update_url = f'https://{pipedrive_domain}.pipedrive.com/v1/dealFields/{field_id}'
                update_data = {
                    'add_visible_flag': True,
                    'visible_to': [1],  # 1 represents the Deals section
                    'is_required': True
                }
                requests.put(update_url, json=update_data)

            # Save the customer
            options = data['data']['options']
            if field_name == payment_label:
                customer.PIPEDRIVE_DEAL_TYPE_FIELD = str(field_id)
            elif field_name == processing_label:
                customer.PIPEDRIVE_DEAL_PROCESSING_FIELD = str(field_id)
            for option in options:
                option_label = option['label']
                option_id = option['id']
                if option_label == 'Subscription':
                    subscription_option_id = option_id
                    customer.PIPEDRIVE_DEAL_SUBSCRIPTION_SELECTOR = str(subscription_option_id)
                elif option_label == 'One Time':
                    one_time_option_id = option_id
                    customer.PIPEDRIVE_DEAL_PAYOUT_SELECTOR = str(one_time_option_id)
                elif option_label == 'Invoice Approval':
                    invoice_approval_option_id = option_id
                    customer.PIPEDRIVE_DEAL_INVOICE_SELECTOR = str(invoice_approval_option_id)
                elif option_label == 'Process Immediately':
                    process_immediately_option_id = option_id
                    customer.PIPEDRIVE_DEAL_PROCESS_NOW_SELECTOR = str(process_immediately_option_id)

        customer.save(should_sync_stripe=False, should_sync_pipedrive=False)
        print('Saved the option ids to the customer successfully!')
        return True

    except Exception as error:
        print(f"Failed to create custom fields: {error}")
        return False

def create_pipedrive_webhooks(access_token=None, customer=None):
    try:
        print("*** Setting Up New Pipedrive Webhooks***")

        # Get the environment variables
        pipedrive_key = os.environ.get('PIPEDRIVE_API_KEY')
        pipedrive_domain = os.environ.get('PIPEDRIVE_DOMAIN')
        pipedrive_user_id = os.environ.get('PIPEDRIVE_USER_ID')
        backend_url = os.environ.get('BACKEND_URL')
        http_auth_user = os.environ.get('HTTP_AUTH_USER')
        http_auth_pass = os.environ.get('HTTP_AUTH_PASSWORD')
        current_webhooks = None

        print("Getting current webhooks...")
        if not access_token:
            url = f'https://{pipedrive_domain}.pipedrive.com/v1/webhooks?api_token={pipedrive_key}'
            current_webhooks_request = requests.get(url)
            current_webhooks = current_webhooks_request.json()['data']
        else:
            try:
                url = f'https://{pipedrive_domain}.pipedrive.com/v1/webhooks'
                headers = {
                    'Authorization': f'Bearer {access_token}',
                }
                current_webhooks_request = requests.get(url, headers=headers)
                current_webhooks = current_webhooks_request.json()['data']
            except Exception as e:
                print(f'\n* ERROR CREATING WEBHOOKS: {e}\n')

        # Delete all current webhooks
        print("Deleting current webhooks...")
        for webhook in current_webhooks:
            if not access_token:
                url = f'https://{pipedrive_domain}.pipedrive.com/v1/webhooks/{webhook["id"]}?api_token={pipedrive_key}'
                requests.delete(url)
            else:
                try:
                    url = f'https://{pipedrive_domain}.pipedrive.com/v1/webhooks/{webhook["id"]}'
                    headers = {
                        'Authorization': f'Bearer {access_token}',
                    }
                    requests.delete(url, headers=headers)
                except Exception as e:
                    print(f'\n* ERROR CREATING WEBHOOKS: {e}\n')

        # Get all urls from ../urls.py
        urls = [
            ("pipedrive/customer-create-webhook/", "person", "added"),
            ("pipedrive/customer-sync-webhook/", "person", "updated"),
            ("pipedrive/customer-delete-webhook/", "person", "deleted"),
            ("pipedrive/deal-create-webhook/", "deal", "added"),
            ("pipedrive/deal-sync-webhook/", "deal", "updated"),
            ("pipedrive/deal-delete-webhook/", "deal", "deleted"),
            ("pipedrive/package-create-webhook/", "product", "added"),
            ("pipedrive/package-sync-webhook/", "product", "updated"),
            ("pipedrive/package-delete-webhook/", "product", "deleted"),
        ]

        # Get the environment variables
        webhook_secret_token = os.environ.get("WEBHOOK_SECRET_TOKEN")

        # Create new webhooks
        print("Creating new webhooks...")
        for url_path, object_type, event_action in urls:
            url = f"{backend_url}/{url_path}"

            # Construct the webhook data
            data = {
                "subscription_url": url,
                "event_action": event_action,
                "event_object": object_type,
                "user_id": pipedrive_user_id,
                "http_auth_user": http_auth_user,
                "http_auth_password": http_auth_pass,
                "headers": {
                    "X-Webhook-Secret-Token": webhook_secret_token
                }
            }

            # Send the webhook creation request
            if not access_token:
                url = f'https://{pipedrive_domain}.pipedrive.com/v1/webhooks?api_token={pipedrive_key}'
                response = requests.post(url, data=data)
                data = response.json()
            else:
                try:
                    url = f'https://{pipedrive_domain}.pipedrive.com/v1/webhooks'
                    headers = {
                        'Authorization': f'Bearer {access_token}' if access_token else f'Bearer {pipedrive_key}',
                    }
                    response = requests.post(url, headers=headers, data=data)
                    data = response.json()
                    # print(f'\n\n### WEBHOOK RESPONSE: {data}\n\n')
                except Exception as e:
                    print(f'\n* ERROR CREATING WEBHOOKS: {e}\n')

            status = data['status']
            if status == 'error':
                print(f'{status}: {data}')
            else:
                print(status)

        print('done')
    except Exception as error:
        print(f'\n* WEBHOOKS FAILED WITH ERROR: {error}\n')

def get_user_tokens(customer_pk):
    try:
        secret_name = "roseware-secrets"
        region_name = "us-east-2"

        # Create a Secrets Manager client
        session = boto3.session.Session()
        client = session.client(
            service_name='secretsmanager',
            region_name=region_name
        )

        env = os.environ.get('DJANGO_ENV')
        get_secret_value_response = client.get_secret_value(
            SecretId=secret_name
        )
        secret_dict = json.loads(get_secret_value_response['SecretString'])
        oauth_tokens = secret_dict["roseware-secrets"][env]["oauth-tokens"]
        customer_key = str(customer_pk)

        if customer_key in oauth_tokens:
            user_tokens = oauth_tokens[customer_key]
            return user_tokens  # This will return a dictionary with access_token and refresh_token

        else:
            print(f"No stored tokens found for customer {customer_key}.")
            return None

    except Exception as e:
        # Handle exceptions thrown by the AWS SDK for Python
        print('Error: ', e)
        return None

""" CREATE CUSTOMER IN PIPEDRIVE """
def create_pipedrive_customer(customer):
    try:
        # Get the environment variables
        pipedrive_key = os.environ.get('PIPEDRIVE_API_KEY')
        pipedrive_domain = os.environ.get('PIPEDRIVE_DOMAIN')

        # Create the customer in Pipedrive
        url = f'https://{pipedrive_domain}.pipedrive.com/v1/persons?api_token={pipedrive_key}'
        
        pipedrive_person_stripe_url_key = os.environ.get('PIPEDRIVE_PERSON_STRIPE_URL_KEY')
        environment = os.environ.get('DJANGO_ENV')
        if environment == 'production':
            stripe_url = f'https://dashboard.stripe.com/customers/{customer.stripe_customer_id}'
        else:
            stripe_url = f'https://dashboard.stripe.com/test/customers/{customer.stripe_customer_id}'

        body = {
            'name': f'{customer.first_name} {customer.last_name}',
            'email': f'{customer.email}',
            'phone': f'{customer.phone}',
            pipedrive_person_stripe_url_key: stripe_url,
        }
        response = requests.post(url, json=body)

        # Check the response data and update the customers pipedrive id
        data = response.json()
        # print(f'** PIPEDRIVE RESPONSE: {data} **\n\n')
        customer_created = data['success']

        if not customer_created:
            print(f'\nCUSTOMER NOT CREATED IN PIPEDRIVE: {data}')
            return False
        pipedrive_customer_id = data['data']['id']
        customer.pipedrive_id = pipedrive_customer_id
        customer.save(should_sync_stripe=False, should_sync_pipedrive=False)
        return pipedrive_customer_id
    except Exception as e:
        print(e)
        return False

""" UPDATE CUSTOMER IN PIPEDRIVE """
def update_pipedrive_customer(customer):
    try:
        # Get the environment variables
        pipedrive_key = os.environ.get('PIPEDRIVE_API_KEY')
        pipedrive_domain = os.environ.get('PIPEDRIVE_DOMAIN')

        # Update Customer in Pipedrive
        url = f'https://{pipedrive_domain}.pipedrive.com/v1/persons/{customer.pipedrive_id}?api_token={pipedrive_key}'
        pipedrive_person_stripe_url_key = os.environ.get('PIPEDRIVE_PERSON_STRIPE_URL_KEY')
        environment = os.environ.get('DJANGO_ENV')
        if environment == 'production':
            stripe_url = f'https://dashboard.stripe.com/customers/{customer.stripe_customer_id}'
        else:
            stripe_url = f'https://dashboard.stripe.com/test/customers/{customer.stripe_customer_id}'
        body = {
            'name': f'{customer.first_name} {customer.last_name}',
            'email': f'{customer.email}',
            'phone': f'{customer.phone}',
            pipedrive_person_stripe_url_key: stripe_url,
        }
        print(f'Update customer in Pipedrive: {body}')
        response = requests.put(url, json=body)
        data = response.json()
        print('Pipedrive response: ', data)
        was_updated = data['success']

        if not was_updated:
            print(f'\nCUSTOMER NOT UPDATED IN PIPEDRIVE: {data}')
            return False

        return was_updated
    except Exception as e:
        print(e)
        return False

""" DELETE CUSTOMER IN PIPEDRIVE """
def delete_pipedrive_customer(pipedrive_id):
    try:
        # Get the environment variables
        pipedrive_key = os.environ.get('PIPEDRIVE_API_KEY')
        pipedrive_domain = os.environ.get('PIPEDRIVE_DOMAIN')

        # Create the customer in Pipedrive
        url = f'https://{pipedrive_domain}.pipedrive.com/v1/persons/{pipedrive_id}?api_token={pipedrive_key}'
        response = requests.delete(url)
        data = response.json()
        was_deleted = data['success']

        if not was_deleted:
            print(f'\nCUSTOMER NOT DELETED IN PIPEDRIVE: {data}')
            return False
        return was_deleted
    except Exception as e:
        print(e)
        return False


""" CREATE LEAD IN PIPEDRIVE """""
def create_pipedrive_lead(customer):
    try:
        # Get the environment variables
        pipedrive_key = os.environ.get('PIPEDRIVE_API_KEY')
        pipedrive_domain = os.environ.get('PIPEDRIVE_DOMAIN')

        # Get the pipedrive customer id
        pipedrive_customer_id = customer.pipedrive_id

        # Then create the lead in Pipedrive
        if pipedrive_customer_id:
            url = f'https://{pipedrive_domain}.pipedrive.com/v1/leads?api_token={pipedrive_key}'
            body = {
                'title': f'{customer.first_name} {customer.last_name} lead',
                'person_id': int(pipedrive_customer_id),
            }
            response = requests.post(url, json=body)
            data = response.json()
            lead_created = data['success']

            if not lead_created:
                print(f'\nLEAD NOT CREATED IN PIPEDRIVE: {data}')
                return False
            return True
        else:
            return False
    except Exception as e:
        print(e)
        return False

""" CREATE PACKAGE IN PIPEDRIVE """
def create_pipedrive_package_template(package):
    try:
        # Get the environment variables
        pipedrive_key = os.environ.get('PIPEDRIVE_API_KEY')
        pipedrive_domain = os.environ.get('PIPEDRIVE_DOMAIN')

        # Create the package in Pipedrive
        url = f'https://{pipedrive_domain}.pipedrive.com/v1/products?api_token={pipedrive_key}'
        pipedrive_product_stripe_url_key = os.environ.get('PIPEDRIVE_PRODUCT_STRIPE_URL_KEY')
        environment = os.environ.get('DJANGO_ENV')
        if environment == 'production':
            stripe_url = f'https://dashboard.stripe.com/products/{package.stripe_product_id}'
        else:
            stripe_url = f'https://dashboard.stripe.com/test/products/{package.stripe_product_id}'
        body = {
            "name": package.name,
            'code': str(package.pk),
            'unit': '1',
            "prices": [
                {'currency': 'USD', 'price': float(package.cost)}
            ],
            pipedrive_product_stripe_url_key: stripe_url
        }
        response = requests.post(url, json=body)
        data = response.json()
        package_created = data['success']

        # Check the response data and update the packages pipedrive id
        if not package_created:
            print(f'\nPACKAGE NOT CREATED IN PIPEDRIVE: {data}')
            return False

        pipedrive_package_id = data['data']['id']
        package.pipedrive_id = pipedrive_package_id
        package.save(should_sync_stripe=False, should_sync_pipedrive=False)
        return package_created
    except Exception as e:
        print(e)
        return False

""" UPDATE PACKAGE IN PIPEDRIVE """

def update_pipedrive_package_template(package_template):
    try:
        # Get the environment variables
        pipedrive_key = os.environ.get('PIPEDRIVE_API_KEY')
        pipedrive_domain = os.environ.get('PIPEDRIVE_DOMAIN')

        # Update Packeag in Pipedrive
        url = f'https://{pipedrive_domain}.pipedrive.com/v1/products/{package_template.pipedrive_id}?api_token={pipedrive_key}'
        pipedrive_product_stripe_url_key = os.environ.get('PIPEDRIVE_PRODUCT_STRIPE_URL_KEY')
        environment = os.environ.get('DJANGO_ENV')
        if environment == 'production':
            stripe_url = f'https://dashboard.stripe.com/products/{package_template.stripe_product_id}'
        else:
            stripe_url = f'https://dashboard.stripe.com/test/products/{package_template.stripe_product_id}'
        body = {
            'name': package_template.name,
            'description': package_template.description,
            'code': str(package_template.pk),
            'unit': '1',
            "prices": [
                {'currency': 'USD', 'price': float(package_template.cost)}
            ],
            pipedrive_product_stripe_url_key: stripe_url
        }
        response = requests.put(url, json=body)
        data = response.json()
        was_updated = data['success']

        if not was_updated:
            print(f'\nPACKAGE NOT UPDATED IN PIPEDRIVE: {data}')
            return False

        return was_updated
    except Exception as e:
        print(e)
        return False

""" DELETE PACKAGE IN PIPEDRIVE """
def delete_pipedrive_package_template(pipedrive_id):
    try:
        # Get the environment variables
        pipedrive_key = os.environ.get('PIPEDRIVE_API_KEY')
        pipedrive_domain = os.environ.get('PIPEDRIVE_DOMAIN')

        # Create the customer in Pipedrive
        url = f'https://{pipedrive_domain}.pipedrive.com/v1/products/{pipedrive_id}?api_token={pipedrive_key}'
        response = requests.delete(url)
        data = response.json()
        was_deleted = data['success']

        if not was_deleted:
            print(f'\nPACKAGE NOT DELETED IN PIPEDRIVE: {data}')
            return False

        return was_deleted
    except Exception as e:
        print(e)
        return False

""" CREATE DEAL IN PIPEDRIVE """
def create_pipedrive_deal(package_plan):
    try:
        # Get the environment variables
        pipedrive_key = os.environ.get('PIPEDRIVE_API_KEY')
        pipedrive_domain = os.environ.get('PIPEDRIVE_DOMAIN')

        # Check if the customer has a pipedrive id, if not return false
        if not package_plan.customer.pipedrive_id:
            return False

        # Create the deal in Pipedrive
        url = f'https://{pipedrive_domain}.pipedrive.com/v1/deals?api_token={pipedrive_key}'
        pipedrive_deal_stripe_url_key = os.environ.get('PIPEDRIVE_DEAL_STRIPE_URL_KEY')
        environment = os.environ.get('DJANGO_ENV')
        if environment == 'production':
            stripe_url = f'https://dashboard.stripe.com/subscriptions/{package_plan.stripe_subscription_id}'
        else:
            stripe_url = f'https://dashboard.stripe.com/test/subscriptions/{package_plan.stripe_subscription_id}'
        body = {
            'title': package_plan.name,
            'person_id': package_plan.customer.pipedrive_id,
            'status': package_plan.status,
            # "49051a6391f07f3175cb0984b6c3a849429d0555": package_plan.billing_cycle,
            pipedrive_deal_stripe_url_key: stripe_url
        }
        response = requests.post(url, json=body)
        data = response.json()
        deal_created = data['success']

        if not deal_created:
            print(f'\nDEAL NOT CREATED IN PIPEDRIVE: {data}')

        # Check the response data and update the packages pipedrive id
        if not deal_created:
            return False

        # Save the pipedrive id to the package plan
        pipedrive_deal_id = data['data']['id']
        package_plan.pipedrive_id = pipedrive_deal_id
        package_plan.save(should_sync_pipedrive=False)

        return deal_created
    except Exception as e:
        print(e)
        return False

""" UPDATE DEAL IN PIPEDRIVE """
def update_pipedrive_deal(package_plan):
    try:
        # print('\n\n $*$* UPDATING PIPEDRIVE DEAL *$*$ \n\n')
        # Get the environment variables
        pipedrive_key = os.environ.get('PIPEDRIVE_API_KEY')
        pipedrive_domain = os.environ.get('PIPEDRIVE_DOMAIN')
        # print('got the env vars')
        # Get the pipedrive customer id
        pipedrive_customer_id = package_plan.customer.pipedrive_id
        print(f'got the pipedrive customer id: {pipedrive_customer_id}')
        # Then update the deal
        if pipedrive_customer_id:
            print('Getting the pipedrive customer id')
            url = f'https://{pipedrive_domain}.pipedrive.com/v1/deals/{package_plan.pipedrive_id}?api_token={pipedrive_key}'

            pipedrive_deal_stripe_url_key = os.environ.get('PIPEDRIVE_DEAL_STRIPE_URL_KEY')
            environment = os.environ.get('DJANGO_ENV')
            if environment == 'production':
                stripe_url = f'https://dashboard.stripe.com/subscriptions/{package_plan.stripe_subscription_id}'
            else:
                stripe_url = f'https://dashboard.stripe.com/test/subscriptions/{package_plan.stripe_subscription_id}'
            print(f'got the stripe url: {stripe_url}')
            body = {
                'title': package_plan.name,
                'person_id': package_plan.customer.pipedrive_id,
                'status': package_plan.status,
                # "49051a6391f07f3175cb0984b6c3a849429d0555": package_plan.billing_cycle,
                pipedrive_deal_stripe_url_key: stripe_url
            }
            response = requests.put(url, json=body)
            data = response.json()
            print(f'got the response: {data}')
            deal_updated = data['success']

            # # Get custom deal fields
            # url = f'https://{pipedrive_domain}.pipedrive.com/v1/dealFields/?api_token={pipedrive_key}'
            # response = requests.get(url)
            # deal_fields = response.json()['data']
            # # print(deal_fields)

            # print('MAKING REQUEST....')
            # url = f'https://{pipedrive_domain}.pipedrive.com/v1/dealFields/49051a6391f07f3175cb0984b6c3a849429d0555?api_token={pipedrive_key}'
            # response = requests.put(url, data={"value": "test"})
            # print(response.json())

            if not deal_updated:
                print(f'\nDEAL NOT UPDATED IN PIPEDRIVE: {data}')
                return False

            return True
        else:
            return False
    except Exception as e:
        print(e)
        return False

""" DELETE DEAL IN PIPEDRIVE """
def delete_pipedrive_deal(deal_id):
    try:
        # Get the environment variables
        pipedrive_key = os.environ.get('PIPEDRIVE_API_KEY')
        pipedrive_domain = os.environ.get('PIPEDRIVE_DOMAIN')

        # Delete the deal in Pipedrive
        url = f'https://{pipedrive_domain}.pipedrive.com/v1/deals/{deal_id}?api_token={pipedrive_key}'
        response = requests.delete(url)
        data = response.json()
        was_deleted = data['success']

        if not was_deleted:
            print(f'\nDEAL NOT DELETED IN PIPEDRIVE: {data}')
            return False

        return was_deleted
    except Exception as e:
        print(e)
        return False

""" ADD PRODUCT TO PIPEDRIVE DEAL """
def create_pipedrive_service_package(service_package):

    try:
        # Get the environment variables
        pipedrive_key = os.environ.get('PIPEDRIVE_API_KEY')
        pipedrive_domain = os.environ.get('PIPEDRIVE_DOMAIN')

        # Create the product in Pipedrive
        url = f'https://{pipedrive_domain}.pipedrive.com/v1/deals/{service_package.package_plan.pipedrive_id}/products?api_token={pipedrive_key}'
        body = {
            'product_id': int(service_package.package_template.pipedrive_id),
            'item_price': float(service_package.cost),
            'quantity': int(service_package.quantity),
        }
        response = requests.post(url, json=body)
        data = response.json()
        deal_created = data['success']

        if not deal_created:
            print(f'\nPRODUCT NOT ADDED TO DEAL IN PIPEDRIVE: {data}')
            return False

        # Check the response data and update the packages pipedrive id
        pipedrive_product_attachment_id = data['data']['id']
        service_package.pipedrive_product_attachment_id = pipedrive_product_attachment_id
        service_package.save(should_sync_pipedrive=False, should_sync_stripe=False)
        return deal_created
    except Exception as e:
        print(e)
        return False

""" UPDATE PRODUCT IN PIPEDRIVE DEAL """
def update_pipedrive_service_package(service_package):
    try:
        # Get the environment variables
        pipedrive_key = os.environ.get('PIPEDRIVE_API_KEY')
        pipedrive_domain = os.environ.get('PIPEDRIVE_DOMAIN')

        # Add a product to a pipedrive deal
        url = f'https://{pipedrive_domain}.pipedrive.com/v1'
        f'/deals/{service_package.package_plan.pipedrive_id}'
        f'/products/{service_package.pipedrive_product_attachment_id}?api_token={pipedrive_key}'
        body = {
            'product_id': int(service_package.package_template.pipedrive_id),
            'item_price': float(service_package.cost),
            'quantity': int(service_package.quantity),
        }
        response = requests.put(url, json=body)
        data = response.json()
        deal_updated = data['success']

        if not deal_updated:
            print(f'\nPRODUCT NOT UPDATED IN PIPEDRIVE: {data}')
            return False

        return deal_updated
    except Exception as e:
        print(e)
        return False

""" DELETE PRODUCT IN PIPEDRIVE DEAL """""
def delete_pipedrive_service_package(service_package):
    try:
        # Get the environment variables
        pipedrive_key = os.environ.get('PIPEDRIVE_API_KEY')
        pipedrive_domain = os.environ.get('PIPEDRIVE_DOMAIN')

        # Add a product to a pipedrive deal
        url = f'https://{pipedrive_domain}.pipedrive.com/v1'
        f'/deals/{service_package.package_plan.pipedrive_id}0{service_package.pipedrive_product_attachment_id}'
        f'?api_token={pipedrive_key}'

        response = requests.delete(url)
        data = response.json()
        deal_deleted = data['success']

        if not deal_deleted:
            print(f'\nPRODUCT NOT DELETED IN PIPEDRIVE: {data}')
            return False

        return deal_deleted
    except Exception as e:
        print(e)
        return False
