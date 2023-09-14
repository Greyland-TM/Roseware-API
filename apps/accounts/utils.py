""" This file contains all the utility functions for the accounts app """

from django.contrib.auth import authenticate
from django.db import IntegrityError
from apps.pipedrive.tasks import sync_pipedrive
from apps.stripe.tasks import sync_stripe
from django.contrib.auth.models import User
from .models import OngoingSync
from roseware.utils import make_logger

logger = make_logger(__name__, stream=True)

def update_or_create_ongoing_sync(type, action, should_sync_stripe, should_sync_pipedrive, sync_platform, owner):
    owner = User.objects.get(pk=owner)
    # check for an ongoing roseware sync
    ongoing_sync = OngoingSync.objects.filter(type=type, action=action, owner=owner).first()
    if ongoing_sync:
        if sync_platform == 'pipedrive':
            ongoing_sync.has_recieved_pipedrive_webhook = True
            ongoing_sync.save()
        if sync_platform == 'stripe':
            ongoing_sync.has_recieved_stripe_webhook = True
            ongoing_sync.save()
        return

    # If there is no ongoing sync, create one
    if not ongoing_sync:
        try:
            new_sync_object = OngoingSync(
                key_or_id="",
                type=type,
                action=action,
                stop_pipedrive_webhook=not should_sync_pipedrive,
                stop_stripe_webhook=not should_sync_stripe,
                owner=owner
            )
            new_sync_object.save()
        except IntegrityError:
            logger.error("An object with this owner_id already exists.")
        return

def create_customer_sync(customer, should_sync_stripe, should_sync_pipedrive):

    # If both are false, return and do nothing
    if not should_sync_pipedrive and not should_sync_stripe:
        return

    # Get the sync platform
    sync_platform = customer.last_synced_from

    # Check for an ongoing sync
    update_or_create_ongoing_sync('customer', 'create', should_sync_stripe, should_sync_pipedrive, sync_platform, customer.owner.pk)

    # Create the customer
    if should_sync_pipedrive:
        logger.info('Creating customer in pipedrive... (Check celery terminal)')
        sync_pipedrive.apply(kwargs={
            'pk': customer.pk,
            'action': 'create',
            'type': "customer",
            "owner_pk": customer.owner.pk,
        })

    if should_sync_stripe:
        logger.info('Creating customer in stripe... (Check celery terminal)')
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
    logger.info('Updating or creating ongoing sync...')
    update_or_create_ongoing_sync('customer', 'update', should_sync_stripe, should_sync_pipedrive, sync_platform, customer.owner.pk)
    # Update the customer
    if should_sync_pipedrive:
        logger.info('Updating customer in pipedrive... (Check celery terminal)')
        sync_pipedrive.delay(customer.pk, 'update', "customer", customer.owner.pk)

    if should_sync_stripe:
        logger.info('Updating customer in stripe... (Check celery terminal)')
        sync_stripe.delay(customer.pk, 'update', "customer")

def delete_customer_sync(pipedrive_id, stripe_id, should_sync_stripe, should_sync_pipedrive, owner_pk):
    # Delete the customer
    if should_sync_pipedrive:
        logger.info('Deleting customer in pipedrive... (Check celery terminal)')
        sync_pipedrive.delay(pipedrive_id, 'delete', "customer", owner_pk)

    if should_sync_stripe:
        logger.info('Deleting customer in stripe... (Check celery terminal)')
        sync_stripe.delay(stripe_id, 'delete', "customer")
