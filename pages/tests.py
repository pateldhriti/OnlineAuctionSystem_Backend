from django.contrib.auth.models import User
from django.core import mail
from django.test import TestCase
from django.urls import reverse


class HomePageTests(TestCase):
    def test_home_page_renders(self):
        response = self.client.get(reverse('home'))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'pages/home.html')
        self.assertTemplateUsed(response, 'base.html')
        self.assertContains(response, 'Bid live. Sell fast. Win big.')
        self.assertContains(response, 'Contact us')

    def test_home_page_prompts_anonymous_visitors_to_register(self):
        response = self.client.get(reverse('home'))

        self.assertContains(response, reverse('accounts:register'))

    def test_home_page_prompts_logged_in_users_to_create_a_listing(self):
        user = User.objects.create_user(username='seller', password='pass12345')
        self.client.force_login(user)

        response = self.client.get(reverse('home'))

        self.assertContains(response, reverse('listings:create'))


class ContactFormTests(TestCase):
    def test_valid_submission_sends_email_and_redirects(self):
        response = self.client.post(reverse('contact'), {
            'name': 'Jamie',
            'email': 'jamie@example.com',
            'message': 'How do I reset my password?',
        })

        self.assertRedirects(response, reverse('home') + '#contact', fetch_redirect_response=False)
        self.assertEqual(len(mail.outbox), 1)
        sent = mail.outbox[0]
        self.assertIn('Jamie', sent.subject)
        self.assertIn('How do I reset my password?', sent.body)
        self.assertIn('jamie@example.com', sent.body)

    def test_invalid_submission_shows_errors_and_sends_no_email(self):
        response = self.client.post(reverse('contact'), {
            'name': '',
            'email': 'not-an-email',
            'message': '',
        })

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'This field is required.')
        self.assertEqual(len(mail.outbox), 0)

    def test_get_is_not_allowed(self):
        response = self.client.get(reverse('contact'))

        self.assertEqual(response.status_code, 405)
