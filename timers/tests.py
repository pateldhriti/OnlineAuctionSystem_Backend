from datetime import timedelta

from django.contrib.auth.models import User
from django.core import mail
from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone

from bids.models import Bid
from listings.models import Listing

from .tasks import close_auction


class CloseAuctionTests(TestCase):
    def setUp(self):
        self.seller = User.objects.create_user(username='seller', password='pass12345')
        self.bidder = User.objects.create_user(username='bidder', password='pass12345')
        self.listing = Listing.objects.create(
            seller=self.seller,
            title='Vintage Clock',
            description='A small table clock.',
            starting_price='25.00',
        )

    def test_close_auction_is_noop_before_end_time(self):
        self.listing.ends_at = timezone.now() + timedelta(days=1)
        self.listing.save()

        result = close_auction(self.listing)

        self.listing.refresh_from_db()
        self.assertIsNone(result)
        self.assertTrue(self.listing.is_active)

    def test_close_auction_closes_expired_listing_with_no_bids(self):
        self.listing.ends_at = timezone.now() - timedelta(minutes=1)
        self.listing.save()

        result = close_auction(self.listing)

        self.listing.refresh_from_db()
        self.assertIsNone(result)
        self.assertFalse(self.listing.is_active)

    def test_close_auction_returns_winning_bid(self):
        self.listing.ends_at = timezone.now() - timedelta(minutes=1)
        self.listing.save()
        Bid.objects.create(listing=self.listing, bidder=self.bidder, amount='30.00')
        top_bidder = User.objects.create_user(username='top', password='pass12345')
        winning_bid = Bid.objects.create(listing=self.listing, bidder=top_bidder, amount='45.00')

        result = close_auction(self.listing)

        self.listing.refresh_from_db()
        winning_bid.refresh_from_db()
        self.assertEqual(result, winning_bid)
        self.assertFalse(self.listing.is_active)
        self.assertTrue(winning_bid.is_winner)

    def test_close_auction_is_noop_when_already_inactive(self):
        self.listing.ends_at = timezone.now() - timedelta(minutes=1)
        self.listing.is_active = False
        self.listing.save()

        result = close_auction(self.listing)

        self.assertIsNone(result)

    def test_close_auction_emails_the_winner(self):
        self.listing.ends_at = timezone.now() - timedelta(minutes=1)
        self.listing.save()
        top_bidder = User.objects.create_user(
            username='top', password='pass12345', email='top@example.com',
        )
        winning_bid = Bid.objects.create(listing=self.listing, bidder=top_bidder, amount='45.00')

        close_auction(self.listing)

        self.assertEqual(len(mail.outbox), 1)
        sent = mail.outbox[0]
        self.assertIn(self.listing.title, sent.subject)
        self.assertEqual(sent.to, [top_bidder.email])
        self.assertIn(str(winning_bid.amount), sent.body)

    def test_close_auction_skips_email_when_winner_has_no_address(self):
        self.listing.ends_at = timezone.now() - timedelta(minutes=1)
        self.listing.save()
        Bid.objects.create(listing=self.listing, bidder=self.bidder, amount='45.00')

        close_auction(self.listing)

        self.assertEqual(len(mail.outbox), 0)


class CloseExpiredAuctionsCommandTests(TestCase):
    def setUp(self):
        self.seller = User.objects.create_user(username='seller', password='pass12345')

    def make_listing(self, ends_at, is_active=True):
        listing = Listing.objects.create(
            seller=self.seller,
            title='Vintage Clock',
            description='A small table clock.',
            starting_price='25.00',
            is_active=is_active,
        )
        listing.ends_at = ends_at
        listing.save()
        return listing

    def test_command_closes_only_expired_active_listings(self):
        expired = self.make_listing(timezone.now() - timedelta(minutes=1))
        not_yet_expired = self.make_listing(timezone.now() + timedelta(days=1))
        already_closed = self.make_listing(timezone.now() - timedelta(minutes=1), is_active=False)

        call_command('close_expired_auctions')

        expired.refresh_from_db()
        not_yet_expired.refresh_from_db()
        already_closed.refresh_from_db()
        self.assertFalse(expired.is_active)
        self.assertTrue(not_yet_expired.is_active)
        self.assertFalse(already_closed.is_active)
