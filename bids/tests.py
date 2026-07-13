from datetime import timedelta
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from listings.models import Listing

from .models import Bid


class BidModelTests(TestCase):
    def setUp(self):
        self.seller = User.objects.create_user(username='seller', password='pass12345')
        self.bidder = User.objects.create_user(username='bidder', password='pass12345')
        self.listing = Listing.objects.create(
            seller=self.seller,
            title='Vintage Clock',
            description='A small table clock.',
            starting_price='25.00',
        )

    def test_bid_string_names_bidder_and_listing(self):
        bid = Bid.objects.create(listing=self.listing, bidder=self.bidder, amount='30.00')

        self.assertEqual(str(bid), 'bidder bid 30.00 on Vintage Clock')

    def test_current_price_for_falls_back_to_starting_price(self):
        self.assertEqual(Bid.current_price_for(self.listing), self.listing.starting_price)
        self.assertIsNone(Bid.highest_for(self.listing))

    def test_current_price_for_tracks_highest_bid(self):
        Bid.objects.create(listing=self.listing, bidder=self.bidder, amount='30.00')
        other_bidder = User.objects.create_user(username='bidder2', password='pass12345')
        Bid.objects.create(listing=self.listing, bidder=other_bidder, amount='45.00')

        self.assertEqual(Bid.current_price_for(self.listing), Decimal('45.00'))
        self.assertEqual(Bid.highest_for(self.listing).bidder, other_bidder)


class PlaceBidViewTests(TestCase):
    def setUp(self):
        self.seller = User.objects.create_user(username='seller', password='pass12345')
        self.bidder = User.objects.create_user(username='bidder', password='pass12345')
        self.listing = Listing.objects.create(
            seller=self.seller,
            title='Vintage Clock',
            description='A small table clock.',
            starting_price='25.00',
        )

    def test_place_bid_requires_login(self):
        response = self.client.post(reverse('bids:place', args=[self.listing.pk]))

        self.assertEqual(response.status_code, 302)
        self.assertIn('/accounts/login/', response.url)

    def test_place_bid_above_starting_price_is_saved(self):
        self.client.force_login(self.bidder)

        response = self.client.post(
            reverse('bids:place', args=[self.listing.pk]),
            {'amount': '30.00'},
        )

        self.assertRedirects(response, reverse('bids:history', args=[self.listing.pk]))
        self.assertEqual(Bid.objects.count(), 1)
        bid = Bid.objects.get()
        self.assertEqual(bid.bidder, self.bidder)
        self.assertEqual(bid.amount, Decimal('30.00'))

    def test_place_bid_at_or_below_current_price_is_rejected(self):
        Bid.objects.create(listing=self.listing, bidder=self.bidder, amount='30.00')
        other_bidder = User.objects.create_user(username='bidder2', password='pass12345')
        self.client.force_login(other_bidder)

        response = self.client.post(
            reverse('bids:place', args=[self.listing.pk]),
            {'amount': '30.00'},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Your bid must be higher than the current price')
        self.assertEqual(Bid.objects.count(), 1)

    def test_invalid_amount_reshows_form_with_field_error(self):
        self.client.force_login(self.bidder)

        response = self.client.post(
            reverse('bids:place', args=[self.listing.pk]),
            {'amount': '-5.00'},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Bid amount must be greater than zero.')
        self.assertEqual(Bid.objects.count(), 0)

    def test_seller_cannot_bid_on_own_listing(self):
        self.client.force_login(self.seller)

        response = self.client.post(
            reverse('bids:place', args=[self.listing.pk]),
            {'amount': '30.00'},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "You can't bid on your own listing.")
        self.assertEqual(Bid.objects.count(), 0)

    def test_cannot_bid_on_inactive_listing(self):
        self.listing.is_active = False
        self.listing.save()
        self.client.force_login(self.bidder)

        response = self.client.post(
            reverse('bids:place', args=[self.listing.pk]),
            {'amount': '30.00'},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'This listing is closed for bidding.')
        self.assertEqual(Bid.objects.count(), 0)

    def test_cannot_bid_after_end_time_even_if_still_marked_active(self):
        self.listing.ends_at = timezone.now() - timedelta(minutes=1)
        self.listing.save()
        self.client.force_login(self.bidder)

        response = self.client.post(
            reverse('bids:place', args=[self.listing.pk]),
            {'amount': '30.00'},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'This listing is closed for bidding.')
        self.assertEqual(Bid.objects.count(), 0)


class BidHistoryViewTests(TestCase):
    def setUp(self):
        self.seller = User.objects.create_user(username='seller', password='pass12345')
        self.bidder = User.objects.create_user(username='bidder', password='pass12345')
        self.listing = Listing.objects.create(
            seller=self.seller,
            title='Vintage Clock',
            description='A small table clock.',
            starting_price='25.00',
        )

    def test_history_page_lists_bids_highest_first(self):
        Bid.objects.create(listing=self.listing, bidder=self.bidder, amount='30.00')
        other_bidder = User.objects.create_user(username='bidder2', password='pass12345')
        Bid.objects.create(listing=self.listing, bidder=other_bidder, amount='45.00')

        response = self.client.get(reverse('bids:history', args=[self.listing.pk]))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['current_price'], Decimal('45.00'))
        bids = list(response.context['bids'])
        self.assertEqual([bid.amount for bid in bids], [Decimal('45.00'), Decimal('30.00')])

    def test_history_page_shows_starting_price_with_no_bids(self):
        response = self.client.get(reverse('bids:history', args=[self.listing.pk]))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['current_price'], Decimal('25.00'))

    def test_bid_form_hidden_for_seller(self):
        self.client.force_login(self.seller)

        response = self.client.get(reverse('bids:history', args=[self.listing.pk]))

        self.assertFalse(response.context['can_bid'])
