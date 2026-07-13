from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from listings.models import Listing

from .models import UserProfile
from .utils import add_to_recently_viewed, get_recently_viewed_ids


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

        self.assertContains(response, 'Signed in as <strong>bidder</strong>')
        self.assertContains(response, 'Logout')


class RegisterViewTests(TestCase):
    def test_register_creates_user_and_profile(self):
        response = self.client.post(reverse('accounts:register'), {
            'username': 'newuser',
            'first_name': 'New',
            'last_name': 'User',
            'email': 'newuser@example.com',
            'password1': 'a-strong-pass123',
            'password2': 'a-strong-pass123',
        })

        self.assertRedirects(response, reverse('accounts:login'))
        user = User.objects.get(username='newuser')
        self.assertEqual(user.email, 'newuser@example.com')
        self.assertTrue(UserProfile.objects.filter(user=user).exists())

    def test_register_rejects_mismatched_passwords(self):
        response = self.client.post(reverse('accounts:register'), {
            'username': 'newuser',
            'first_name': 'New',
            'last_name': 'User',
            'email': 'newuser@example.com',
            'password1': 'a-strong-pass123',
            'password2': 'does-not-match',
        })

        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.filter(username='newuser').exists())

    def test_authenticated_user_is_redirected_away_from_register(self):
        user = User.objects.create_user(username='bidder', password='pass12345')
        self.client.force_login(user)

        response = self.client.get(reverse('accounts:register'))

        self.assertRedirects(response, reverse('home'))


class LoginViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='bidder', password='pass12345')

    def test_login_with_valid_credentials_redirects_home(self):
        response = self.client.post(reverse('accounts:login'), {
            'username': 'bidder',
            'password': 'pass12345',
        })

        self.assertRedirects(response, reverse('home'))
        self.assertIn('_auth_user_id', self.client.session)

    def test_login_redirects_to_safe_next_url(self):
        next_url = reverse('accounts:profile')

        response = self.client.post(reverse('accounts:login'), {
            'username': 'bidder',
            'password': 'pass12345',
            'next': next_url,
        })

        self.assertRedirects(response, next_url)

    def test_login_ignores_unsafe_next_url(self):
        response = self.client.post(reverse('accounts:login'), {
            'username': 'bidder',
            'password': 'pass12345',
            'next': 'https://evil.example.com/',
        })

        self.assertRedirects(response, reverse('home'))

    def test_login_with_invalid_credentials_shows_error(self):
        response = self.client.post(reverse('accounts:login'), {
            'username': 'bidder',
            'password': 'wrong-password',
        })

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Invalid username or password.')

    def test_authenticated_user_is_redirected_away_from_login(self):
        self.client.force_login(self.user)

        response = self.client.get(reverse('accounts:login'))

        self.assertRedirects(response, reverse('home'))


class LogoutViewTests(TestCase):
    def test_logout_redirects_to_login_and_ends_session(self):
        user = User.objects.create_user(username='bidder', password='pass12345')
        self.client.force_login(user)

        response = self.client.get(reverse('accounts:logout'))

        self.assertRedirects(response, reverse('accounts:login'))
        self.assertNotIn('_auth_user_id', self.client.session)


class ProfileViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='bidder', password='pass12345')
        UserProfile.objects.create(user=self.user)
        self.seller = User.objects.create_user(username='seller', password='pass12345')
        self.listing = Listing.objects.create(
            seller=self.seller,
            title='Vintage Clock',
            description='A small table clock.',
            starting_price='25.00',
        )

    def test_profile_requires_login(self):
        response = self.client.get(reverse('accounts:profile'))

        self.assertEqual(response.status_code, 302)
        self.assertIn('/accounts/login/', response.url)

    def test_profile_shows_recently_viewed_listings(self):
        self.client.force_login(self.user)
        self.client.get(reverse('listings:detail', args=[self.listing.pk]))

        response = self.client.get(reverse('accounts:profile'))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(list(response.context['recently_viewed']), [self.listing])


class ProfileEditViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='bidder', password='pass12345', email='old@example.com'
        )
        UserProfile.objects.create(user=self.user)

    def test_profile_edit_requires_login(self):
        response = self.client.get(reverse('accounts:profile_edit'))

        self.assertEqual(response.status_code, 302)
        self.assertIn('/accounts/login/', response.url)

    def test_profile_edit_updates_user_and_profile(self):
        self.client.force_login(self.user)

        response = self.client.post(reverse('accounts:profile_edit'), {
            'first_name': 'Updated',
            'last_name': 'Name',
            'email': 'updated@example.com',
            'phone': '555-1234',
            'bio': 'Collector of vintage clocks.',
        })

        self.assertRedirects(response, reverse('accounts:profile'))
        self.user.refresh_from_db()
        self.assertEqual(self.user.email, 'updated@example.com')
        self.assertEqual(self.user.profile.phone, '555-1234')
        self.assertEqual(self.user.profile.bio, 'Collector of vintage clocks.')


class PasswordChangeViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='bidder', password='old-pass123')

    def test_password_change_requires_login(self):
        response = self.client.get(reverse('accounts:password_change'))

        self.assertEqual(response.status_code, 302)
        self.assertIn('/accounts/login/', response.url)

    def test_password_change_updates_password_and_keeps_session(self):
        self.client.force_login(self.user)

        response = self.client.post(reverse('accounts:password_change'), {
            'old_password': 'old-pass123',
            'new_password1': 'a-new-strong-pass456',
            'new_password2': 'a-new-strong-pass456',
        })

        self.assertRedirects(response, reverse('accounts:profile'))
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('a-new-strong-pass456'))
        # Session should still be authenticated after the password change.
        response = self.client.get(reverse('accounts:profile'))
        self.assertEqual(response.status_code, 200)

    def test_password_change_rejects_wrong_old_password(self):
        self.client.force_login(self.user)

        response = self.client.post(reverse('accounts:password_change'), {
            'old_password': 'not-the-old-password',
            'new_password1': 'a-new-strong-pass456',
            'new_password2': 'a-new-strong-pass456',
        })

        self.assertEqual(response.status_code, 200)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('old-pass123'))


class RecentlyViewedUtilsTests(TestCase):
    def setUp(self):
        self.seller = User.objects.create_user(username='seller', password='pass12345')
        self.listings = [
            Listing.objects.create(
                seller=self.seller,
                title=f'Listing {i}',
                description='Description.',
                starting_price='10.00',
            )
            for i in range(3)
        ]

    def test_add_to_recently_viewed_orders_most_recent_first(self):
        session = self.client.session
        request = type('R', (), {'session': session})()

        add_to_recently_viewed(request, self.listings[0].pk)
        add_to_recently_viewed(request, self.listings[1].pk)
        request.session.save()
        self.client.session.save()

        self.assertEqual(
            get_recently_viewed_ids(request),
            [self.listings[1].pk, self.listings[0].pk],
        )

    def test_add_to_recently_viewed_moves_repeat_view_to_front(self):
        session = self.client.session
        request = type('R', (), {'session': session})()

        add_to_recently_viewed(request, self.listings[0].pk)
        add_to_recently_viewed(request, self.listings[1].pk)
        add_to_recently_viewed(request, self.listings[0].pk)

        self.assertEqual(
            get_recently_viewed_ids(request),
            [self.listings[0].pk, self.listings[1].pk],
        )

    def test_add_to_recently_viewed_caps_at_five(self):
        session = self.client.session
        request = type('R', (), {'session': session})()
        extra = Listing.objects.create(
            seller=self.seller,
            title='Listing 3',
            description='Description.',
            starting_price='10.00',
        )
        all_listings = self.listings + [extra]

        for listing in all_listings:
            add_to_recently_viewed(request, listing.pk)
        add_to_recently_viewed(request, 999999)

        self.assertEqual(len(get_recently_viewed_ids(request)), 5)

    def test_viewing_a_listing_records_it_as_recently_viewed(self):
        user = User.objects.create_user(username='bidder', password='pass12345')
        self.client.force_login(user)

        self.client.get(reverse('listings:detail', args=[self.listings[0].pk]))

        self.assertEqual(
            get_recently_viewed_ids(self.client),
            [self.listings[0].pk],
        )
