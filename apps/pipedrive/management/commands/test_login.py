from django.core.management.base import BaseCommand
import os
import requests
from django.urls import get_resolver
import hashlib
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    def handle(self, *args, **options):
        try:
            requests.get("https://www.google.com")
        except Exception as error:
            logger.error(f"failed with error: {error}")
