""" This file contains all the utility functions for the accounts app """

from django.contrib.auth import authenticate

from apps.pipedrive.tasks import sync_pipedrive
from apps.stripe.tasks import sync_stripe

from .models import OngoingSync


def update_or_create_ongoing_sync(type, action, should_sync_stripe, should_sync_pipedrive, sync_platform):
    # check for an ongoing roseware sync
    roseware_ongoing_sync = OngoingSync.objects.filter(type=type, action=action).first()
    if roseware_ongoing_sync:
        if sync_platform == 'pipedrive':
            roseware_ongoing_sync.has_recieved_pipedrive_webhook = True
            roseware_ongoing_sync.save()
        if sync_platform == 'stripe':
            roseware_ongoing_sync.has_recieved_stripe_webhook = True
            roseware_ongoing_sync.save()
        return

    # Check for an ongoing Stripe sync
    stripe_ongoing_sync = OngoingSync.objects.filter(type=type, action=action).first()
    if stripe_ongoing_sync:
        if sync_platform == 'pipedrive':
            stripe_ongoing_sync.has_recieved_pipedrive_webhook = True
            stripe_ongoing_sync.save()
        if sync_platform == 'stripe':
            stripe_ongoing_sync.has_recieved_stripe_webhook = True
            stripe_ongoing_sync.save()
        return

    # Check for an ongoing Pipedrive sync
    pipedrive_ongoing_sync = OngoingSync.objects.filter(type=type, action=action).first()
    if pipedrive_ongoing_sync:
        if sync_platform == 'pipedrive':
            pipedrive_ongoing_sync.has_recieved_pipedrive_webhook = True
            pipedrive_ongoing_sync.save()
        if sync_platform == 'stripe':
            pipedrive_ongoing_sync.has_recieved_stripe_webhook = True
            pipedrive_ongoing_sync.save()
        return

    # If there is no ongoing sync, create one
    if not pipedrive_ongoing_sync and not stripe_ongoing_sync:

        new_sync_object = OngoingSync(
            key_or_id="",
            type=type,
            action=action,
            stop_pipedrive_webhook=not should_sync_pipedrive,
            stop_stripe_webhook=not should_sync_stripe,
        )
        new_sync_object.save()
        return

def create_customer_sync(customer, should_sync_stripe, should_sync_pipedrive):

    # If both are false, return and do nothing
    if not should_sync_pipedrive and not should_sync_stripe:
        return

    # Get the sync platform
    sync_platform = customer.last_synced_from

    # Check for an ongoing sync
    update_or_create_ongoing_sync('customer', 'create', should_sync_stripe, should_sync_pipedrive, sync_platform)

    # Create the customer
    if should_sync_pipedrive:
        print('Creating customer in pipedrive... (Check celery terminal)')
        sync_pipedrive.apply(kwargs={
            'pk': customer.pk,
            'action': 'create',
            'type': "customer"
        })

    if should_sync_stripe:
        print('Creating customer to stripe... (Check celery terminal)')
        sync_stripe.apply(kwargs={
            'pk': customer.pk,
            'action': 'create',
            'type': "customer"
        })

def update_customer_sync(customer, should_sync_stripe, should_sync_pipedrive):
    # ongoing_sync = OngoingSync.objects.filter()
    sync_platform = customer.last_synced_from

    if not should_sync_pipedrive and not should_sync_stripe:
        return

    # Check for an ongoing sync
    print('Updating or creating ongoing sync...')
    update_or_create_ongoing_sync('customer', 'update', should_sync_stripe, should_sync_pipedrive, sync_platform)
    print('Done updating or creating ongoing sync...')
    print(f'should_sync_pipedrive: {should_sync_pipedrive}')
    print(f'should_sync_stripe: {should_sync_stripe}')
    # Update the customer
    if should_sync_pipedrive:
        print('Updating customer to pipedrive... (Check celery terminal)')
        sync_pipedrive.delay(customer.pk, 'update', "customer")

    if should_sync_stripe:
        print('Updating customer to stripe... (Check celery terminal)')
        sync_stripe.delay(customer.pk, 'update', "customer")

def delete_customer_sync(pipedrive_id, stripe_id, should_sync_stripe, should_sync_pipedrive):
    # Delete the customer
    if should_sync_pipedrive:
        print('Deleting customer to pipedrive... (Check celery terminal)')
        sync_pipedrive.delay(pipedrive_id, 'delete', "customer")

    if should_sync_stripe:
        print('Deleting customer to stripe... (Check celery terminal)')
        sync_stripe.delay(stripe_id, 'delete', "customer")
