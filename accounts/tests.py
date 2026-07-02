from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse


class AuthPageTests(TestCase):
    def test_register_page_renders(self):
        response = self.client.get(reverse('accounts:register'))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'accounts/register.html')
        self.assertTemplateUsed(response, 'base.html')

    def test_login_page_renders(self):
        response = self.client.get(reverse('accounts:login'))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'accounts/login.html')
        self.assertTemplateUsed(response, 'base.html')

    def test_nav_shows_logout_for_logged_in_user(self):
        user = User.objects.create_user(username='bidder', password='pass12345')
        self.client.force_login(user)

        response = self.client.get(reverse('home'))

        self.assertContains(response, 'Logout (bidder)')
