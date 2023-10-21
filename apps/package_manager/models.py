from django.db import models
from django.db.models import (
    BooleanField,
    CharField,
    DateTimeField,
    DecimalField,
    IntegerField,
)
import os
import logging
from apps.accounts.models import CustomUser, Customer

logger = logging.getLogger(__name__)


# Create your models here.


class ServicePackageTemplate(models.Model):
    """This model will be used to store the templates for posts."""

    # TYPE_CHOICES = (
    #     ("webpage", "Webpage"),
    #     ("social", "Social"),
    #     ("blog", "Blog"),
    #     ("ads", "Ads"), # TODO - Add this later - Probably just a part of the Duda app
    # )
    # RELATED_APP_CHOICES = (
    #     ("duda", "Duda"),
    #     ("markit", "Markit"),
    #     ("ayrshare", "Ayrshare"),
    # )
    ACTION_CHOICES = (("create", "Create"),)

    owner = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name="package_template_owner",
        null=True,
        blank=True,
    )
    related_app = CharField(max_length=100, default="integrations")
    description = CharField(max_length=100, default="", null=True, blank=True)
    name = CharField(max_length=100, default="")
    type = CharField(max_length=100, default="")
    cost = DecimalField(max_digits=6, decimal_places=2, default=0.0)
    unit = IntegerField(default=1)
    requires_onboarding = BooleanField(default=False)
    action = CharField(max_length=100, default="create")
    error = CharField(max_length=100, null=True, blank=True, default="")
    original_sync_from = CharField(
        max_length=100, null=True, blank=True, default="roseware"
    )
    last_synced_from = CharField(
        max_length=100, null=True, blank=True, default="roseware"
    )
    pipedrive_id = CharField(max_length=100, null=True, blank=True, default="")
    stripe_product_id = CharField(max_length=100, null=True, blank=True)
    stripe_price_id = CharField(max_length=100, null=True, blank=True)

    def save(
        self, should_sync_pipedrive=True, should_sync_stripe=True, *args, **kwargs
    ):
        from .utils import create_package_template_sync, update_package_template_sync

        if self.pk and self.last_synced_from == "":
            # If the object already exists and last_synced_from is not empty, keep the old value
            old_obj = ServicePackageTemplate.objects.get(pk=self.pk)
            self.last_synced_from = old_obj.last_synced_from

        is_new = self._state.adding

        super(ServicePackageTemplate, self).save(*args, **kwargs)

        if is_new:
            create_package_template_sync(
                self, should_sync_pipedrive, should_sync_stripe, self.owner.pk
            )
        else:
            update_package_template_sync(
                self, should_sync_pipedrive, should_sync_stripe, self.owner.pk
            )

    def delete(
        self, should_sync_pipedrive=True, should_sync_stripe=True, *args, **kwargs
    ):
        from .utils import delete_package_template_sync

        pipedrive_id = self.pipedrive_id
        stripe_id = self.stripe_product_id
        owner = self.owner
        super(ServicePackageTemplate, self).delete(*args, **kwargs)
        delete_package_template_sync(
            stripe_id, pipedrive_id, should_sync_pipedrive, should_sync_stripe, owner.pk
        )


class PackagePlan(models.Model):


    owner = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name="package_plan_owner",
        null=True,
        blank=True,
    )
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE)
    name = CharField(max_length=100, default="")
    status = CharField(max_length=100)
    type = CharField(
        max_length=100,
        default="subscription",
        null=True,
        blank=True,
    )
    description = CharField(max_length=100, default="")
    billing_cycle = CharField(max_length=100, default="subscription")
    original_sync_from = CharField(
        max_length=100, null=True, blank=True, default="roseware"
    )
    last_synced_from = CharField(
        max_length=100, null=True, blank=True, default="roseware"
    )
    pipedrive_id = CharField(max_length=100, null=True, blank=True)
    stripe_subscription_id = CharField(max_length=100, null=True, blank=True)

    def save(
        self, should_sync_pipedrive=True, should_sync_stripe=False, *args, **kwargs
    ):
        from .utils import create_package_plan_sync, update_package_plan_sync

        is_new = self._state.adding
        print(f'\n\nSAVING PACKAGE PLAN is_new: {is_new}, pk: {self.pk}')
        print('stripe_subscription_id: ', self.stripe_subscription_id, ', pipedrive_id: , ', self.pipedrive_id, '\n\n')

        # There are situations where a pipedrive or stripe id is being overwritten with None
        # So here I want to only set the pipedrive_id and stripe_subscription_id if they are not None
        pipedrive_id = self.pipedrive_id
        stripe_subscription_id = self.stripe_subscription_id

        super(PackagePlan, self).save(*args, **kwargs)

        if self.pipedrive_id is None:
            print('pipedrive  id is none, setting to ', pipedrive_id)
            self.pipedrive_id = pipedrive_id

        if self.stripe_subscription_id is None:
            self.stripe_subscription_id = stripe_subscription_id

        if is_new:
            create_package_plan_sync(
                self, should_sync_pipedrive, should_sync_stripe, self.owner.pk
            )
        else:
            update_package_plan_sync(
                self, should_sync_pipedrive, should_sync_stripe, self.owner.pk
            )

    def delete(
        self, should_sync_pipedrive=True, should_sync_stripe=True, *args, **kwargs
    ):
        from .utils import delete_package_plan_sync
        print(f'\n\nDELETING PACKAGE PLAN pk: {self.pk}')

        # Before deleting the PackagePlan instance, delete each related ServicePackage instance
        for service_package in self.servicepackage_set.all():
            service_package.delete(
                should_sync_pipedrive=should_sync_pipedrive,
                should_sync_stripe=should_sync_stripe,
            )

        pk = self.pipedrive_id
        stripe_subscription_id = self.stripe_subscription_id
        owner = self.owner
        logger.info("Deleted package plan:  ")
        super(PackagePlan, self).delete(*args, **kwargs)

        print('calling delete_package_plan_sync. pk: ', pk, 'stripe_subscription_id: ', stripe_subscription_id, 'owner.pk: ', owner.pk)
        delete_package_plan_sync(
            pk,
            stripe_subscription_id,
            should_sync_pipedrive,
            should_sync_stripe,
            owner.pk,
        )


class ServicePackage(models.Model):
    """This model will be used to store the templates for posts."""

    TYPE_CHOICES = (
        ("Webpage", "Webpage"),
        ("Social", "Social"),
        ("Blog", "Blog"),
        ("Ads", "Ads"),
    )
    RELATED_APP_CHOICES = (
        ("Duda", "Duda"),
        ("Roseware", "Roseware"),
        ("Ayrshare", "Ayrshare"),
    )
    ACTION_CHOICES = (("create", "Create"),)

    customer = models.ForeignKey(Customer, on_delete=models.CASCADE)
    package_template = models.ForeignKey(
        ServicePackageTemplate,
        on_delete=models.CASCADE,
        default=None,
        null=True,
        blank=True,
    )
    package_plan = models.ForeignKey(
        PackagePlan, on_delete=models.SET_NULL, default=None, null=True, blank=True
    )
    related_app = CharField(max_length=100, default="", choices=RELATED_APP_CHOICES)
    type = CharField(max_length=100, default="", choices=TYPE_CHOICES)
    is_active = BooleanField(default=True)
    cost = DecimalField(max_digits=6, decimal_places=2, default=0.0)
    quantity = IntegerField(default=1)
    last_completed = DateTimeField(max_length=100, default=None, null=True, blank=True)
    date_started = DateTimeField(max_length=100, default=None, null=True, blank=True)
    next_scheduled = DateTimeField(
        max_length=100, default=None, null=True, blank=True
    )  # datetime
    requires_onboarding = BooleanField(default=False)
    action = CharField(max_length=100, default="create", choices=ACTION_CHOICES)
    error = CharField(max_length=100, default=None, null=True, blank=True)
    original_sync_from = CharField(
        max_length=100, null=True, blank=True, default="roseware"
    )
    last_synced_from = CharField(
        max_length=100, null=True, blank=True, default="roseware"
    )
    pipedrive_product_attachment_id = CharField(max_length=100, null=True, blank=True)
    stripe_subscription_item_id = CharField(max_length=100, null=True, blank=True)
    stripe_subscription_item_price_id = CharField(max_length=100, null=True, blank=True)

    def save(
        self, should_sync_pipedrive=True, should_sync_stripe=True, *args, **kwargs
    ):
        from .utils import create_service_package_sync, update_service_package_sync

        is_new = self._state.adding

        super(ServicePackage, self).save(*args, **kwargs)

        if is_new:
            create_service_package_sync(
                self,
                should_sync_pipedrive,
                should_sync_stripe,
                self.package_plan.owner.pk,
            )
        else:
            update_service_package_sync(
                self,
                should_sync_pipedrive,
                should_sync_stripe,
                self.package_plan.owner.pk,
            )

    def delete(
        self, should_sync_pipedrive=True, should_sync_stripe=True, *args, **kwargs
    ):
        from .utils import delete_service_package_sync
        

        piperive_id = self.pipedrive_product_attachment_id
        stripe_subscription_item_id = self.package_plan.stripe_subscription_id
        owner = self.package_plan.owner
        customer = self.customer
        title = self.package_template.name
        super(ServicePackage, self).delete(*args, **kwargs)
        delete_service_package_sync(
            piperive_id,
            stripe_subscription_item_id,
            should_sync_pipedrive,
            should_sync_stripe,
            owner.pk,
        )

        # If the pipedrive-stripe sync was deleted set the customer's sync status to false
        template_title = os.environ.get("PIPEDRIVE_DEAL_TITLE")
        if title == template_title:
            customer.has_synced_pipedrive = False
            customer.has_synced_stripe = False
            customer.save(should_sync_pipedrive=False, should_sync_stripe=False)
