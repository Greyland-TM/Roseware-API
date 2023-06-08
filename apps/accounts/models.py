from django.contrib.auth.models import User
from django.db import models
from django.db.models import CharField, DateTimeField
from phonenumber_field.modelfields import PhoneNumberField

# from django.contrib.postgres.fields import ArrayField
# from apps.ayrshare.models import SocialAccount

class Employee(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    first_name = CharField(default="Joe", max_length=100)
    last_name = CharField(default="Dierte", max_length=100)

    def __str__(self):
        return self.first_name


class Customer(models.Model):
    STATUS_CHOICE_FIELDS = (('lead', 'Lead'), ('customer', 'Customer'))
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    rep = models.ForeignKey(Employee, on_delete=models.CASCADE)
    first_name = CharField(default="", max_length=100, null=False, blank=False)
    last_name = CharField(default="", max_length=100, null=False, blank=False)
    email = CharField(default="", max_length=100, null=False, blank=False)
    phone = PhoneNumberField(null=True, blank=True)
    status = CharField(default="lead", max_length=100, choices=STATUS_CHOICE_FIELDS)
    onboarding_date = DateTimeField(null=True, blank=True)
    monday_id = CharField(default="", max_length=100, null=True, blank=True)
    pipedrive_id = CharField(default="", max_length=100, null=True, blank=True)
    stripe_customer_id = CharField(default="", max_length=100, null=True, blank=True)
    original_sync_from = CharField(max_length=100, null=True, blank=True, default="roseware")
    last_synced_from = CharField(max_length=100, null=True, blank=True, default="roseware")

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

class OngoingSync(models.Model):
    # customer = models.ForeignKey(Customer, on_delete=models.CASCADE, null=True)
    type = CharField(default="", max_length=100, null=False, blank=False)
    created_at = DateTimeField(auto_now_add=True, null=True, blank=True)
    action = CharField(default="", max_length=100, null=False, blank=False)
    key_or_id = CharField(default="", max_length=100, null=False, blank=False)
    stop_pipedrive_webhook = models.BooleanField(default=False)
    has_recieved_pipedrive_webhook = models.BooleanField(default=False)
    stop_stripe_webhook = models.BooleanField(default=False)
    has_recieved_stripe_webhook = models.BooleanField(default=False)

    def save(self, *args, **kwargs):
        print(
            f"* Saving OngoingSync object,"
            f" stop_pipedrive_webhook: {self.stop_pipedrive_webhook},"
            f" has_recieved_stripe_webhook: {self.has_recieved_stripe_webhook}\n"
        )

        is_new = self._state.adding
        if is_new:
            print(
                f"* Created OngoingSync object, "
                f" stop_pipedrive_webhook: {self.stop_pipedrive_webhook}, "
                f"has_recieved_stripe_webhook{self.has_recieved_stripe_webhook}\n"
            )
            self.has_recieved_pipedrive_webhook = self.stop_pipedrive_webhook
            self.has_recieved_stripe_webhook = self.stop_stripe_webhook
        super(OngoingSync, self).save(*args, **kwargs)

        # If both webhooks have been received, delete the object and return True
        if self.has_recieved_pipedrive_webhook and self.has_recieved_stripe_webhook:
            print("* Deleted OngoingSync object \n")
            self.delete()
            return True

        return False

class Toggles(models.Model):
    name = CharField(default="Toggles", max_length=100, null=False, blank=False)
    stop_pipedrive_webhooks = models.BooleanField(default=False)
    stop_stripe_webhooks = models.BooleanField(default=False)

    def __str__(self):
        return self.name
