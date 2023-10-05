from django.core.management.base import BaseCommand
from apps.accounts.models import CustomUser

class Command(BaseCommand):
    help = 'Create a superuser using the custom user model'

    def handle(self, *args, **options):
        email = input('Enter email: ')
        first_name = input('Enter first name: ')
        last_name = input('Enter last name: ')
        password = input('Enter password: ')

        user = CustomUser.objects.create_superuser(email, first_name, last_name, password)
        self.stdout.write(self.style.SUCCESS(f'Superuser {user.email} created successfully.'))
