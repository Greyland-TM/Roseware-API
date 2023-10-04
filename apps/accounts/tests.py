from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from accounts.models import CustomUser

class LoginTests(APITestCase):
    def setUp(self):
        self.url = reverse('login')
        self.user = CustomUser.objects.create_user(
            username='alhoff@gmail.com',
            email='alhoff@gmail.com',
            password='greycy9391'
        )

    def test_login_success(self):
        data = {
            'email': self.user.email,
            'password': 'greycy9391'
        }

        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue('token' in response.data)

    def test_login_failure(self):
        data = {
            'email': self.user.email,
            'password': 'wrongpassword'
        }

        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse('token' in response.data)
