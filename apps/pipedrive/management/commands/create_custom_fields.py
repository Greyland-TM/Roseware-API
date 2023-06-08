import hashlib
import os

import requests
from django.core.management.base import BaseCommand
from django.urls import get_resolver


class Command(BaseCommand):
    """ This command creates custom fields in Pipedrive. """
    def handle(self, *args, **options):
        try:
            """ THIS CODE CREATES THE "TYPE" FIELD """
            pipedrive_api_key = os.environ.get('PIPEDRIVE_API_KEY')
            pipedrive_domain = os.environ.get('PIPEDRIVE_DOMAIN')

            # Define the choices for the "Type" field
            choices = ['Subscription', 'Payout']

            # Create the options dictionary for the "Type" field
            options = [{'label': choice, 'active': True} for choice in choices]

            # Define the data for creating the field
            data = {
                'name': 'Type',
                'field_type': 'enum',
                'options': options
            }

            # Add the "Type" field to dealFields
            url = f'https://{pipedrive_domain}.pipedrive.com/v1/dealFields?api_token={pipedrive_api_key}'
            response = requests.post(url, json=data)
            print(response.json())
            print(response.status_code)

            # Check the response status
            field_id = response.json().get('data', {}).get('id')
            if field_id:
                # Update field settings to pin it to the deal creation form
                update_url = f'https://{pipedrive_domain}.pipedrive.com/v1/dealFields/{field_id}?api_token={pipedrive_api_key}'
                update_data = {
                    'add_visible_flag': True,
                    'visible_to': [1],  # 1 represents the Deals section
                    'is_required': True
                }
                requests.put(update_url, json=update_data)
                print('Created the "Type" field successfully!')
    
            """ THIS CODE WORKS FOR SETTING ALL THE STRIPE URL FIELDS """
            # pipedrive_api_key = os.environ.get('PIPEDRIVE_API_KEY')
            # pipedrive_domain = os.environ.get('PIPEDRIVE_DOMAIN')
            # pipedrive_api_key = os.environ.get('PIPEDRIVE_STAGING_API_KEY')
            # pipedrive_domain = os.environ.get('PIPEDRIVE_STAGING_DOMAIN')
            # data = {
            #     'name': 'stripe url',
            #     'field_type': 'varchar'
            # }
            
            # # Add stripe_url field to personFields
            # url = f'https://{pipedrive_domain}.pipedrive.com/v1/personFields?api_token={pipedrive_api_key}'
            # response = requests.post(url, data=data)
            # print(response.json())
            # person_key = response.json()['data']['key']
            
            # # Add stripe_url field to dealFields
            # url = f'https://{pipedrive_domain}.pipedrive.com/v1/dealFields?api_token={pipedrive_api_key}'
            # response = requests.post(url, data=data)
            # print(response.json())
            # deal_key = response.json()['data']['key']
            
            # # Add stripe_url field to productFields
            # url = f'https://{pipedrive_domain}.pipedrive.com/v1/productFields?api_token={pipedrive_api_key}'
            # response = requests.post(url, data=data)
            # print(response.json())
            # product_key = response.json()['data']['key']
            
            # # Print the keys
            # print(f"\n\nPerson Field Key: {person_key}")
            # print(f"Deal Field Key: {deal_key}")
            # print(f"Product Field Key: {product_key}")
            
        except Exception as error:
            print(f"Failed to create custom fields: {error}")
            return
