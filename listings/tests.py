import shutil
import tempfile
from datetime import timedelta

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.test import TestCase
from django.test.utils import override_settings
from django.urls import reverse
from django.utils import timezone

from bids.models import Bid

from .models import DEFAULT_AUCTION_DURATION, Listing


class ListingModelTests(TestCase):
    def test_listing_string_returns_title(self):
        user = User.objects.create_user(username='seller', password='pass12345')
        listing = Listing.objects.create(
            seller=user,
            title='Vintage Clock',
            description='A small table clock.',
            starting_price='25.00',
        )

        self.assertEqual(str(listing), 'Vintage Clock')

    def test_listing_defaults_to_other_category(self):
        user = User.objects.create_user(username='seller', password='pass12345')
        listing = Listing.objects.create(
            seller=user,
            title='Vintage Clock',
            description='A small table clock.',
            starting_price='25.00',
        )

        self.assertEqual(listing.category, Listing.Category.OTHER)

    def test_listing_defaults_ends_at_to_one_week_out(self):
        user = User.objects.create_user(username='seller', password='pass12345')
        before = timezone.now() + DEFAULT_AUCTION_DURATION

        listing = Listing.objects.create(
            seller=user,
            title='Vintage Clock',
            description='A small table clock.',
            starting_price='25.00',
        )

        after = timezone.now() + DEFAULT_AUCTION_DURATION
        self.assertIsNotNone(listing.ends_at)
        self.assertTrue(before <= listing.ends_at <= after)
        self.assertFalse(listing.has_ended)

    def test_has_ended_true_once_end_time_passes(self):
        user = User.objects.create_user(username='seller', password='pass12345')
        listing = Listing.objects.create(
            seller=user,
            title='Vintage Clock',
            description='A small table clock.',
            starting_price='25.00',
        )
        listing.ends_at = timezone.now() - timedelta(minutes=1)
        listing.save()

        self.assertTrue(listing.has_ended)

    def test_status_is_active_before_end_time(self):
        user = User.objects.create_user(username='seller', password='pass12345')
        listing = Listing.objects.create(
            seller=user,
            title='Vintage Clock',
            description='A small table clock.',
            starting_price='25.00',
        )

        self.assertEqual(listing.status, Listing.STATUS_ACTIVE)

    def test_status_is_ended_after_end_time_but_not_yet_closed(self):
        user = User.objects.create_user(username='seller', password='pass12345')
        listing = Listing.objects.create(
            seller=user,
            title='Vintage Clock',
            description='A small table clock.',
            starting_price='25.00',
        )
        listing.ends_at = timezone.now() - timedelta(minutes=1)
        listing.save()

        self.assertEqual(listing.status, Listing.STATUS_ENDED)

    def test_status_is_closed_once_marked_inactive(self):
        user = User.objects.create_user(username='seller', password='pass12345')
        listing = Listing.objects.create(
            seller=user,
            title='Vintage Clock',
            description='A small table clock.',
            starting_price='25.00',
            is_active=False,
        )

        self.assertEqual(listing.status, Listing.STATUS_CLOSED)


class ListingViewTests(TestCase):
    def setUp(self):
        self.media_root = tempfile.mkdtemp()
        self.settings_override = override_settings(MEDIA_ROOT=self.media_root)
        self.settings_override.enable()
        self.addCleanup(self.settings_override.disable)
        self.addCleanup(shutil.rmtree, self.media_root, ignore_errors=True)
        self.user = User.objects.create_user(username='seller', password='pass12345')
        self.buyer = User.objects.create_user(username='buyer', password='pass12345')

    def make_listing(self, **kwargs):
        defaults = {
            'seller': self.user,
            'title': 'Vintage Clock',
            'description': 'A small table clock.',
            'category': Listing.Category.HOME,
            'starting_price': '25.00',
        }
        defaults.update(kwargs)
        return Listing.objects.create(**defaults)

    def make_image(self):
        return SimpleUploadedFile(
            'listing.gif',
            (
                b'GIF87a\x01\x00\x01\x00\x80\x00\x00\x00\x00\x00'
                b'\xff\xff\xff,\x00\x00\x00\x00\x01\x00\x01\x00'
                b'\x00\x02\x02D\x01\x00;'
            ),
            content_type='image/gif',
        )

    def test_list_view_shows_listings(self):
        self.make_listing()

        response = self.client.get(reverse('listings:list'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Vintage Clock')

    def test_list_view_shows_highest_bid_when_present(self):
        listing = self.make_listing()
        Bid.objects.create(listing=listing, bidder=self.buyer, amount='40.00')

        response = self.client.get(reverse('listings:list'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '$40.00')

    def test_list_view_shows_ended_badge_for_unprocessed_expired_listing(self):
        """A listing whose deadline has passed but hasn't been picked up by
        close_auction yet must not show a stale "Active" badge - that
        previously contradicted the "Auction closed" countdown text shown
        for the same listing.
        """
        listing = self.make_listing()
        listing.ends_at = timezone.now() - timedelta(minutes=1)
        listing.save()

        response = self.client.get(reverse('listings:list'))

        self.assertContains(response, 'badge-glow-warning">Ended')
        self.assertNotContains(response, 'badge-glow-success">Active')

    def test_list_view_paginates_listings(self):
        from listings.views import LISTINGS_PAGE_SIZE

        for i in range(LISTINGS_PAGE_SIZE + 1):
            self.make_listing(title=f'Listing {i}')

        first_page = self.client.get(reverse('listings:list'))
        second_page = self.client.get(reverse('listings:list'), {'page': 2})

        self.assertEqual(len(first_page.context['page_obj']), LISTINGS_PAGE_SIZE)
        self.assertEqual(len(second_page.context['page_obj']), 1)
        self.assertContains(first_page, '1 / 2')

    def test_list_view_filters_by_category(self):
        self.make_listing(title='Vintage Clock', category=Listing.Category.HOME)
        self.make_listing(title='Bluetooth Speaker', category=Listing.Category.ELECTRONICS)

        response = self.client.get(
            reverse('listings:list'),
            {'category': Listing.Category.ELECTRONICS},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Bluetooth Speaker')
        self.assertNotContains(response, 'Vintage Clock')

    def test_list_view_searches_by_title(self):
        self.make_listing(title='Vintage Clock', description='A small table clock.')
        self.make_listing(title='Bluetooth Speaker', description='Portable wireless audio.')

        response = self.client.get(reverse('listings:list'), {'q': 'clock'})

        self.assertContains(response, 'Vintage Clock')
        self.assertNotContains(response, 'Bluetooth Speaker')

    def test_list_view_searches_by_description(self):
        self.make_listing(title='Vintage Clock', description='Hand-wound antique timepiece.')
        self.make_listing(title='Bluetooth Speaker', description='Portable wireless audio.')

        response = self.client.get(reverse('listings:list'), {'q': 'antique'})

        self.assertContains(response, 'Vintage Clock')
        self.assertNotContains(response, 'Bluetooth Speaker')

    def test_list_view_combines_search_and_category(self):
        self.make_listing(title='Vintage Clock', category=Listing.Category.HOME)
        self.make_listing(title='Vintage Car', category=Listing.Category.VEHICLES)

        response = self.client.get(
            reverse('listings:list'),
            {'q': 'vintage', 'category': Listing.Category.HOME},
        )

        self.assertContains(response, 'Vintage Clock')
        self.assertNotContains(response, 'Vintage Car')

    def test_list_view_shows_no_results_message_for_unmatched_search(self):
        self.make_listing(title='Vintage Clock')

        response = self.client.get(reverse('listings:list'), {'q': 'nonexistent-item'})

        self.assertContains(response, 'No listings match your search')

    def test_detail_view_shows_listing(self):
        listing = self.make_listing()

        response = self.client.get(reverse('listings:detail', args=[listing.pk]))

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['title'], 'Vintage Clock')
        self.assertEqual(data['category'], Listing.Category.HOME)
        self.assertEqual(data['category_display'], 'Home')
        self.assertEqual(data['current_price'], '25.00')
        self.assertEqual(data['bid_count'], 0)
        self.assertIsNotNone(data['ends_at'])

    def test_detail_page_shows_live_bid_and_countdown_hooks(self):
        listing = self.make_listing()
        Bid.objects.create(listing=listing, bidder=self.buyer, amount='45.00')

        response = self.client.get(
            reverse('listings:detail', args=[listing.pk]),
            HTTP_ACCEPT='text/html',
        )

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'listings/listing_detail.html')
        self.assertContains(response, 'Current highest bid')
        self.assertContains(response, '$45.00')
        self.assertContains(response, 'buyer')
        self.assertContains(response, 'data-current-price')
        self.assertContains(response, 'data-ends-at')

    def test_logged_in_user_can_create_listing(self):
        self.client.force_login(self.user)

        response = self.client.post(
            reverse('listings:create'),
            {
                'title': 'Desk Lamp',
                'description': 'Adjustable lamp.',
                'category': Listing.Category.HOME,
                'starting_price': '15.50',
                'image': self.make_image(),
            },
        )

        listing = Listing.objects.get(title='Desk Lamp')
        self.assertRedirects(response, reverse('listings:detail', args=[listing.pk]))
        self.assertEqual(listing.seller, self.user)
        self.assertEqual(listing.category, Listing.Category.HOME)
        self.assertTrue(listing.image.name.startswith('listing_images/'))

    def test_create_listing_form_accepts_multipart_encoding(self):
        """The rendered form must be able to actually submit the image field.

        Django's test client always sends multipart/form-data regardless of
        the HTML form's own enctype, so it can't catch a missing
        enctype="multipart/form-data" attribute on the <form> tag - assert on
        the rendered markup directly instead.
        """
        self.client.force_login(self.user)

        response = self.client.get(reverse('listings:create'))

        self.assertContains(response, 'enctype="multipart/form-data"')

    def test_create_listing_rejects_oversized_image(self):
        from unittest.mock import patch

        self.client.force_login(self.user)

        with patch('listings.forms.MAX_IMAGE_SIZE_BYTES', 10):
            response = self.client.post(
                reverse('listings:create'),
                {
                    'title': 'Desk Lamp',
                    'description': 'Adjustable lamp.',
                    'category': Listing.Category.HOME,
                    'starting_price': '15.50',
                    'image': self.make_image(),
                },
            )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Image must be smaller than 5MB.')
        self.assertFalse(Listing.objects.filter(title='Desk Lamp').exists())

    def test_listing_owner_can_update_listing(self):
        listing = self.make_listing()
        self.client.force_login(self.user)

        response = self.client.post(
            reverse('listings:update', args=[listing.pk]),
            {
                'title': 'Updated Clock',
                'description': 'Updated description.',
                'category': Listing.Category.OTHER,
                'starting_price': '30.00',
            },
        )

        self.assertRedirects(response, reverse('listings:detail', args=[listing.pk]))
        listing.refresh_from_db()
        self.assertEqual(listing.title, 'Updated Clock')
        self.assertEqual(listing.category, Listing.Category.OTHER)

    def test_non_owner_cannot_update_listing(self):
        listing = self.make_listing()
        self.client.force_login(self.buyer)

        response = self.client.post(
            reverse('listings:update', args=[listing.pk]),
            {
                'title': 'Changed by buyer',
                'description': 'Should not save.',
                'category': Listing.Category.OTHER,
                'starting_price': '30.00',
            },
        )

        self.assertEqual(response.status_code, 404)
        listing.refresh_from_db()
        self.assertEqual(listing.title, 'Vintage Clock')

    def test_listing_owner_can_delete_listing(self):
        listing = self.make_listing()
        self.client.force_login(self.user)

        response = self.client.post(reverse('listings:delete', args=[listing.pk]))

        self.assertRedirects(response, reverse('listings:list'))
        self.assertFalse(Listing.objects.filter(pk=listing.pk).exists())

    def test_non_owner_cannot_delete_listing(self):
        listing = self.make_listing()
        self.client.force_login(self.buyer)

        response = self.client.post(reverse('listings:delete', args=[listing.pk]))

        self.assertEqual(response.status_code, 404)
        self.assertTrue(Listing.objects.filter(pk=listing.pk).exists())

    def test_logged_in_user_can_toggle_watchlist(self):
        listing = self.make_listing()
        self.client.force_login(self.buyer)

        add_response = self.client.post(reverse('listings:toggle_watchlist', args=[listing.pk]))
        self.assertRedirects(add_response, reverse('listings:detail', args=[listing.pk]))
        self.assertTrue(listing.watchers.filter(pk=self.buyer.pk).exists())

        remove_response = self.client.post(reverse('listings:toggle_watchlist', args=[listing.pk]))
        self.assertRedirects(remove_response, reverse('listings:detail', args=[listing.pk]))
        self.assertFalse(listing.watchers.filter(pk=self.buyer.pk).exists())

    def test_watchlist_view_shows_watched_listings(self):
        watched_listing = self.make_listing(title='Watched Clock')
        other_listing = self.make_listing(title='Ignored Lamp')
        watched_listing.watchers.add(self.buyer)
        self.client.force_login(self.buyer)

        response = self.client.get(reverse('listings:watchlist'))

        self.assertEqual(response.status_code, 200)
        titles = [listing['title'] for listing in response.json()['listings']]
        self.assertIn(watched_listing.title, titles)
        self.assertNotIn(other_listing.title, titles)


class ListingAdminTests(TestCase):
    def setUp(self):
        self.admin_user = User.objects.create_superuser(
            username='admin', password='pass12345', email='admin@example.com',
        )
        self.seller = User.objects.create_user(username='seller', password='pass12345')
        self.listing = Listing.objects.create(
            seller=self.seller,
            title='Vintage Clock',
            description='A small table clock.',
            starting_price='25.00',
        )

    def test_changelist_shows_listing_and_status(self):
        self.client.force_login(self.admin_user)

        response = self.client.get(reverse('admin:listings_listing_changelist'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Vintage Clock')
        self.assertContains(response, Listing.STATUS_ACTIVE)

    def test_change_page_shows_bid_inline(self):
        Bid.objects.create(listing=self.listing, bidder=self.seller, amount='30.00')
        self.client.force_login(self.admin_user)

        response = self.client.get(reverse('admin:listings_listing_change', args=[self.listing.pk]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '30.00')


@override_settings(DEBUG=True)
class SeedDemoCommandTests(TestCase):
    """Django's test runner forces DEBUG=False by default, which would trip
    seed_demo's production guard for every test here except the one that's
    actually testing that guard - so this class overrides DEBUG=True and
    the guard test below overrides it back to False just for that one case.
    """

    def test_seed_demo_creates_expected_data(self):
        call_command('seed_demo')

        self.assertTrue(User.objects.filter(username='admin', is_superuser=True).exists())
        self.assertEqual(Listing.objects.count(), 3)
        clock = Listing.objects.get(title='Antique Wall Clock')
        self.assertEqual(clock.status, Listing.STATUS_CLOSED)
        self.assertTrue(Bid.objects.filter(listing=clock, is_winner=True).exists())

    def test_seed_demo_is_idempotent(self):
        call_command('seed_demo')
        call_command('seed_demo')

        self.assertEqual(User.objects.filter(username='admin').count(), 1)
        self.assertEqual(Listing.objects.count(), 3)
        self.assertEqual(Bid.objects.count(), 5)

    def test_seed_demo_refuses_to_run_with_debug_false(self):
        from django.core.management import CommandError

        with override_settings(DEBUG=False):
            with self.assertRaises(CommandError):
                call_command('seed_demo')

        self.assertFalse(User.objects.filter(username='admin').exists())


class InitialDataFixtureTests(TestCase):
    """Loading fixtures/initial_data.json should produce a consistent,
    usable dataset - this is the project's other initial-data path besides
    the seed_demo management command.
    """
    fixtures = ['initial_data']

    def test_fixture_loads_expected_counts(self):
        from conversations.models import Conversation, Message

        self.assertEqual(User.objects.count(), 4)
        self.assertEqual(Listing.objects.count(), 3)
        self.assertEqual(Bid.objects.count(), 5)
        self.assertEqual(Conversation.objects.count(), 1)
        self.assertEqual(Message.objects.count(), 2)

    def test_fixture_users_can_authenticate_with_known_password(self):
        self.assertTrue(self.client.login(username='seller1', password='demopass123'))

    def test_fixture_closed_listing_has_a_winning_bid(self):
        clock = Listing.objects.get(title='Antique Wall Clock')

        self.assertEqual(clock.status, Listing.STATUS_CLOSED)
        self.assertTrue(Bid.objects.filter(listing=clock, is_winner=True).exists())
