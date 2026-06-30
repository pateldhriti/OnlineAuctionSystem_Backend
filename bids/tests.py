from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from listings.models import Listing

from .models import Bid


class BidModelTests(TestCase):
    def test_bid_string_names_bidder_and_listing(self):
        seller = User.objects.create_user(username='seller', password='pass12345')
        bidder = User.objects.create_user(username='bidder', password='pass12345')
        listing = Listing.objects.create(
            seller=seller,
            title='Vintage Clock',
            description='A small table clock.',
            starting_price='25.00',
        )
        bid = Bid.objects.create(listing=listing, bidder=bidder, amount='30.00')

        self.assertEqual(str(bid), 'bidder bid 30.00 on Vintage Clock')


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

    def test_place_bid_stub_saves_nothing_yet(self):
        self.client.force_login(self.bidder)

        response = self.client.post(
            reverse('bids:place', args=[self.listing.pk]),
            {'amount': '30.00'},
        )

        self.assertRedirects(response, reverse('listings:list'))
        self.assertEqual(Bid.objects.count(), 0)
