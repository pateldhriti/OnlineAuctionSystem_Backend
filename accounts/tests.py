import shutil
import tempfile
from decimal import Decimal

from django.contrib.auth.models import User
from django.core import mail
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.test.utils import override_settings
from django.urls import reverse
from django.utils import timezone

from listings.models import Listing

from .middleware import VISIT_COOKIE_NAME
from .models import DailyVisit, UserProfile
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

        response = self.client.post(reverse('accounts:logout'))

        self.assertRedirects(response, reverse('accounts:login'))
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_logout_rejects_get_to_prevent_link_based_logout(self):
        user = User.objects.create_user(username='bidder', password='pass12345')
        self.client.force_login(user)

        response = self.client.get(reverse('accounts:logout'))

        self.assertEqual(response.status_code, 405)
        self.assertIn('_auth_user_id', self.client.session)


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


class SellerDashboardViewTests(TestCase):
    def setUp(self):
        from bids.models import Bid

        self.Bid = Bid
        self.seller = User.objects.create_user(username='seller', password='pass12345')
        self.bidder = User.objects.create_user(username='bidder', password='pass12345')

    def test_dashboard_shows_current_price_and_bid_count(self):
        listing = Listing.objects.create(
            seller=self.seller,
            title='Vintage Clock',
            description='A small table clock.',
            starting_price='25.00',
        )
        self.Bid.objects.create(listing=listing, bidder=self.bidder, amount='30.00')
        other_bidder = User.objects.create_user(username='bidder2', password='pass12345')
        self.Bid.objects.create(listing=listing, bidder=other_bidder, amount='45.00')
        self.client.force_login(self.seller)

        response = self.client.get(reverse('accounts:dashboard'))

        self.assertEqual(response.status_code, 200)
        row = response.context['dashboard_data'][0]
        self.assertEqual(row['current_price'], Decimal('45.00'))
        self.assertEqual(row['bid_count'], 2)

    def test_dashboard_query_count_does_not_scale_with_listings_or_bids(self):
        for i in range(5):
            listing = Listing.objects.create(
                seller=self.seller,
                title=f'Listing {i}',
                description='Description.',
                starting_price='10.00',
            )
            for j in range(3):
                bidder = User.objects.create_user(username=f'bidder-{i}-{j}', password='pass12345')
                self.Bid.objects.create(listing=listing, bidder=bidder, amount=str(20 + j))
        self.client.force_login(self.seller)
        # TrackVisitMiddleware does one extra write the first time a user is
        # seen on a given day; pay that one-time cost here so the query
        # count below reflects the dashboard view alone.
        self.client.get(reverse('accounts:dashboard'))

        with self.assertNumQueries(5):
            response = self.client.get(reverse('accounts:dashboard'))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['dashboard_data']), 5)


class PasswordResetFlowTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='bidder', password='OldPass123', email='bidder@example.com',
        )

    def test_request_reset_sends_email_for_known_address(self):
        response = self.client.post(reverse('accounts:password_reset'), {'email': 'bidder@example.com'})

        self.assertRedirects(response, reverse('accounts:password_reset_done'))
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('Reset your Online Auction password', mail.outbox[0].subject)
        self.assertIn('/accounts/password/reset/confirm/', mail.outbox[0].body)

    def test_request_reset_does_not_reveal_unknown_address(self):
        response = self.client.post(reverse('accounts:password_reset'), {'email': 'nobody@example.com'})

        self.assertRedirects(response, reverse('accounts:password_reset_done'))
        self.assertEqual(len(mail.outbox), 0)

    def test_full_reset_flow_changes_password(self):
        self.client.post(reverse('accounts:password_reset'), {'email': 'bidder@example.com'})
        email_body = mail.outbox[0].body
        reset_url = next(
            line.strip() for line in email_body.splitlines() if '/password/reset/confirm/' in line
        )
        reset_path = reset_url.split('localhost', 1)[-1] if 'localhost' in reset_url else reset_url
        # Strip the protocol/domain the email template includes.
        reset_path = '/' + reset_path.split('/', 3)[-1]

        confirm_response = self.client.get(reset_path)
        self.assertEqual(confirm_response.status_code, 302)

        set_password_response = self.client.post(confirm_response.url, {
            'new_password1': 'NewStrongPass456',
            'new_password2': 'NewStrongPass456',
        })

        self.assertRedirects(set_password_response, reverse('accounts:password_reset_complete'))
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('NewStrongPass456'))
        self.assertFalse(self.user.check_password('OldPass123'))

    def test_reused_reset_link_is_rejected(self):
        self.client.post(reverse('accounts:password_reset'), {'email': 'bidder@example.com'})
        email_body = mail.outbox[0].body
        reset_url = next(
            line.strip() for line in email_body.splitlines() if '/password/reset/confirm/' in line
        )
        reset_path = '/' + reset_url.split('/', 3)[-1]

        confirm_response = self.client.get(reset_path)
        self.client.post(confirm_response.url, {
            'new_password1': 'NewStrongPass456',
            'new_password2': 'NewStrongPass456',
        })

        # Following the same emailed link again (fresh client, no session
        # state) must not work a second time.
        second_client_response = self.client.get(reset_path, follow=True)
        self.assertContains(second_client_response, 'Link expired')


class VisitTrackingTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='bidder', password='pass12345')

    def test_first_visit_of_the_day_creates_a_daily_visit_row(self):
        self.client.force_login(self.user)

        self.client.get(reverse('home'))

        visit = DailyVisit.objects.get(user=self.user, date=timezone.localdate())
        self.assertEqual(visit.visit_count, 1)

    def test_repeat_requests_in_the_same_session_do_not_double_count(self):
        self.client.force_login(self.user)

        self.client.get(reverse('home'))
        self.client.get(reverse('listings:list'))
        self.client.get(reverse('accounts:profile'))

        visit = DailyVisit.objects.get(user=self.user, date=timezone.localdate())
        self.assertEqual(visit.visit_count, 1)

    def test_sets_last_visit_cookie(self):
        self.client.force_login(self.user)

        response = self.client.get(reverse('home'))

        self.assertEqual(response.cookies[VISIT_COOKIE_NAME].value, timezone.localdate().isoformat())

    def test_a_new_day_in_the_same_session_increments_the_count(self):
        self.client.force_login(self.user)
        self.client.get(reverse('home'))
        session = self.client.session
        session['visit_counted_date'] = '2000-01-01'
        session.save()

        self.client.get(reverse('home'))

        visit = DailyVisit.objects.get(user=self.user, date=timezone.localdate())
        self.assertEqual(visit.visit_count, 2)

    def test_anonymous_users_are_not_tracked(self):
        self.client.get(reverse('home'))

        self.assertEqual(DailyVisit.objects.count(), 0)


class HistoryViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='bidder', password='pass12345')

    def test_requires_login(self):
        response = self.client.get(reverse('accounts:history'))

        self.assertEqual(response.status_code, 302)
        self.assertIn('/accounts/login/', response.url)

    def test_shows_visit_stats(self):
        self.client.force_login(self.user)
        self.client.get(reverse('accounts:history'))

        response = self.client.get(reverse('accounts:history'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Total visits')
        self.assertEqual(response.context['visits_today'], 1)
        self.assertEqual(response.context['total_visits'], 1)


class ProfileDocumentUploadTests(TestCase):
    def setUp(self):
        self.media_root = tempfile.mkdtemp()
        self.settings_override = override_settings(MEDIA_ROOT=self.media_root)
        self.settings_override.enable()
        self.addCleanup(self.settings_override.disable)
        self.addCleanup(shutil.rmtree, self.media_root, ignore_errors=True)
        self.user = User.objects.create_user(
            username='bidder', password='pass12345', email='bidder@example.com',
        )

    def make_file(self, name='id.jpg', content=b'fake image bytes', content_type='image/jpeg'):
        return SimpleUploadedFile(name, content, content_type=content_type)

    def edit_profile(self, **overrides):
        data = {
            'first_name': 'Test', 'last_name': 'User', 'email': 'bidder@example.com',
            'phone': '', 'bio': '',
        }
        data.update(overrides)
        return self.client.post(reverse('accounts:profile_edit'), data)

    def test_profile_edit_form_uses_multipart_encoding(self):
        self.client.force_login(self.user)

        response = self.client.get(reverse('accounts:profile_edit'))

        self.assertContains(response, 'enctype="multipart/form-data"')

    def test_can_upload_a_valid_id_document(self):
        self.client.force_login(self.user)

        response = self.edit_profile(id_document=self.make_file())

        self.assertRedirects(response, reverse('accounts:profile'))
        self.user.profile.refresh_from_db()
        self.assertTrue(self.user.profile.id_document.name.startswith('id_documents/'))

    def test_rejects_disallowed_file_type(self):
        self.client.force_login(self.user)

        response = self.edit_profile(
            id_document=self.make_file(name='malware.exe', content_type='application/octet-stream'),
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Upload a JPG, PNG, or PDF file.')

    def test_rejects_oversized_file(self):
        from unittest.mock import patch

        self.client.force_login(self.user)

        with patch('accounts.forms.MAX_DOCUMENT_SIZE_BYTES', 10):
            response = self.edit_profile(id_document=self.make_file())

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'File must be smaller than 5MB.')

    def test_profile_page_shows_uploaded_document_link(self):
        self.client.force_login(self.user)
        self.edit_profile(id_document=self.make_file())

        response = self.client.get(reverse('accounts:profile'))

        self.assertContains(response, 'View file')
