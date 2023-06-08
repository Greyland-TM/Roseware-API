from django.core.management.base import BaseCommand
from apps.monday.tasks import save_to_monday


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument("customer_pk", type=int, nargs="?")

    def handle(self, *args, **options):
        customer_pk = options["customer_pk"]

        if not customer_pk:
            print("You need to provide a customer pk to create an ayrshare account...")
            return

        save_to_monday.delay(customer_pk, 'leads', is_new=True)