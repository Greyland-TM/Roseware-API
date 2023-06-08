from django.core.management.base import BaseCommand
import os
import requests
from django.urls import get_resolver
import hashlib

class Command(BaseCommand):
    def handle(self, *args, **options):
        try:
            requests.get('https://www.google.com')
        except Exception as error:
            print(f'failed with error: {error}')
