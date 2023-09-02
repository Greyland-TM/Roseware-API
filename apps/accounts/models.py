from django.apps import apps
from django.contrib.auth.models import User
from django.db import models
from django.db.models import CharField, DateTimeField
from phonenumber_field.modelfields import PhoneNumberField


class Employee(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    first_name = CharField(default="Joe", max_length=100)
    last_name = CharField(default="Dierte", max_length=100)
    role = CharField(default="sales", max_length=100)
    profile_picture = models.ImageField(upload_to='profile_picture/', null=True, blank=True)
    bio = CharField(default="", max_length=1000, null=True, blank=True)
    linkedin = CharField(default="", max_length=100, null=True, blank=True)
    github = CharField(default="", max_length=100, null=True, blank=True)
    display_on_website = models.BooleanField(default=False, null=True, blank=True)

    def __str__(self):
        return self.first_name

class Customer(models.Model):
    """ This model represents a single customer """

    # Choices
    STATUS_CHOICE_FIELDS = (('lead', 'Lead'), ('customer', 'Customer'))

    # Fields
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    rep = models.ForeignKey(Employee, on_delete=models.CASCADE)
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name="customer_owner", null=True, blank=True)
    first_name = CharField(default="", max_length=100, null=False, blank=False)
    last_name = CharField(default="", max_length=100, null=False, blank=False)
    email = CharField(default="", max_length=100, null=False, blank=False)
    phone = CharField(null=True, blank=True)
    profile_picture = models.ImageField(upload_to='profilte_picture/', null=True, blank=True)
    status = CharField(default="lead", max_length=100, choices=STATUS_CHOICE_FIELDS)
    onboarding_date = DateTimeField(null=True, blank=True)
    monday_id = CharField(default="", max_length=100, null=True, blank=True)
    pipedrive_id = CharField(default="", max_length=100, null=True, blank=True)
    pipedrive_user_id = CharField(default="", max_length=100, null=True, blank=True)
    piprdrive_api_url = CharField(max_length=100, null=True, blank=True, default="")
    stripe_customer_id = CharField(default="", max_length=100, null=True, blank=True)
    stripe_account_id = CharField(default="", max_length=100, null=True, blank=True)
    original_sync_from = CharField(max_length=100, null=True, blank=True, default="roseware")
    last_synced_from = CharField(max_length=100, null=True, blank=True, default="roseware")
    has_synced_pipedrive = models.BooleanField(default=False)
    has_synced_stripe = models.BooleanField(default=False)
    beta_feature_flag = models.BooleanField(default=False)
    
    # Pipedrive api key / oauth token. Depends on the user making the request. Employee's should use the api keys.
    PIPEDRIVE_PERSON_STRIPE_URL_KEY = CharField(max_length=100, null=True, blank=True, default="")
    PIPEDRIVE_PRODUCT_STRIPE_URL_KEY = CharField(max_length=100, null=True, blank=True, default="")
    PIPEDRIVE_DEAL_STRIPE_URL_KEY = CharField(max_length=100, null=True, blank=True, default="")
    PIPEDRIVE_DEAL_TYPE_FIELD = CharField(max_length=100, null=True, blank=True, default="")
    PIPEDRIVE_DEAL_SUBSCRIPTION_SELECTOR = CharField(max_length=100, null=True, blank=True, default="")
    PIPEDRIVE_DEAL_PAYOUT_SELECTOR = CharField(max_length=100, null=True, blank=True, default="")
    PIPEDRIVE_DEAL_PROCESSING_FIELD = CharField(max_length=100, null=True, blank=True, default="")
    PIPEDRIVE_DEAL_INVOICE_SELECTOR = CharField(max_length=100, null=True, blank=True, default="")
    PIPEDRIVE_DEAL_PROCESS_NOW_SELECTOR = CharField(max_length=100, null=True, blank=True, default="")

    def save(self, should_sync_stripe=True, should_sync_pipedrive=True, *args, **kwargs):
        from .utils import create_customer_sync, update_customer_sync

        is_new = self._state.adding

        # If it's a new customer, set the first name, last name, and email to the user's
        if is_new:
            self.first_name = self.user.first_name
            self.last_name = self.user.last_name
            self.email = self.user.email
        super(Customer, self).save(*args, **kwargs)

        if is_new:
            create_customer_sync(self, should_sync_stripe, should_sync_pipedrive)
        else:
            if self.user:
                self.user.first_name = self.first_name
                self.user.last_name = self.last_name
                self.user.email = self.email
                self.user.save()
            update_customer_sync(self, should_sync_stripe, should_sync_pipedrive)

    def delete(self, should_sync_stripe=True, should_sync_pipedrive=True, *args, **kwargs):
        from .utils import delete_customer_sync

        # Get the pipedrive id before deleting the object
        pipedrive_id = self.pipedrive_id
        stripe_id = self.stripe_customer_id
        user = self.user
        
        super(Customer, self).delete(*args, **kwargs)
        user.delete()
        
        delete_customer_sync(pipedrive_id, stripe_id, should_sync_stripe, should_sync_pipedrive)

    def __str__(self):
        return self.first_name
    
class Organization(models.Model):
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name="organization_owner", null=True, blank=True)
    name = CharField(default="", max_length=100, null=False, blank=False)
    address = CharField(default="", max_length=100, null=False, blank=False)
    
    def __str__(self):
        return self.name

class OngoingSync(models.Model):
    """
    This object is here to fix one problem: If you think about triggering a sync to pipedrive,
    When the object is saved, pipedrive will sent a webhook to the server, and the server will then update and save the object in our db.
    There are some cases where this can trigger an infinate loop of webhooks, creating or modifying the same object over and over again.
    So this object is here to keep track of the state of the sync, and to make sure that the sync is only triggered once.
    It is created and deleted as the sync loop progresses, and is deleted when its done.
    If you ever find an OngoingSyng object in the database, then something went wrong with either the code or the environment.
    """
    type = CharField(default="", max_length=100, null=False, blank=False)
    created_at = DateTimeField(auto_now_add=True, null=True, blank=True)
    action = CharField(default="", max_length=100, null=False, blank=False)
    key_or_id = CharField(default="", max_length=100, null=False, blank=False)
    stop_pipedrive_webhook = models.BooleanField(default=False)
    has_recieved_pipedrive_webhook = models.BooleanField(default=False)
    stop_stripe_webhook = models.BooleanField(default=False)
    has_recieved_stripe_webhook = models.BooleanField(default=False)
    owner = models.OneToOneField(User, on_delete=models.CASCADE, null=True, blank=True)

    def save(self, *args, **kwargs):

        is_new = self._state.adding
        if is_new:
            self.has_recieved_pipedrive_webhook = self.stop_pipedrive_webhook
            self.has_recieved_stripe_webhook = self.stop_stripe_webhook
        super(OngoingSync, self).save(*args, **kwargs)

        # If both webhooks have been received, delete the object and return True
        if self.has_recieved_pipedrive_webhook and self.has_recieved_stripe_webhook:
            self.delete()
            return True

        return False

class Toggles(models.Model):
    name = CharField(default="Toggles", max_length=100, null=False, blank=False)
    stop_pipedrive_webhooks = models.BooleanField(default=False)
    stop_stripe_webhooks = models.BooleanField(default=False)

    def __str__(self):
        return self.name
