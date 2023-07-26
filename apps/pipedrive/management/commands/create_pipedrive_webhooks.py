from django.core.management.base import BaseCommand
from apps.pipedrive.utils import create_pipedrive_webhooks

class Command(BaseCommand):
    def handle(self, *args, **options):
        create_pipedrive_webhooks()