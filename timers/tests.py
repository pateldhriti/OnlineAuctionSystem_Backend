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

    def test_close_auction_breaks_tied_highest_bids_by_earliest(self):
        self.listing.ends_at = timezone.now() - timedelta(minutes=1)
        self.listing.save()
        earlier_bid = Bid.objects.create(listing=self.listing, bidder=self.bidder, amount='45.00')
        later_bidder = User.objects.create_user(username='later', password='pass12345')
        later_bid = Bid.objects.create(listing=self.listing, bidder=later_bidder, amount='45.00')
        Bid.objects.filter(pk=earlier_bid.pk).update(created_at=timezone.now() - timedelta(minutes=5))
        Bid.objects.filter(pk=later_bid.pk).update(created_at=timezone.now())

        result = close_auction(self.listing)

        earlier_bid.refresh_from_db()
        later_bid.refresh_from_db()
        self.assertEqual(result, earlier_bid)
        self.assertTrue(earlier_bid.is_winner)
        self.assertFalse(later_bid.is_winner)

    def test_close_auction_is_idempotent(self):
        self.listing.ends_at = timezone.now() - timedelta(minutes=1)
        self.listing.save()
        emailed_bidder = User.objects.create_user(
            username='emailed', password='pass12345', email='emailed@example.com',
        )
        winning_bid = Bid.objects.create(listing=self.listing, bidder=emailed_bidder, amount='45.00')

        first_result = close_auction(self.listing)
        self.listing.refresh_from_db()
        second_result = close_auction(self.listing)

        self.assertEqual(first_result, winning_bid)
        self.assertIsNone(second_result)
        self.assertEqual(len(mail.outbox), 1)

    def test_close_auction_moves_listing_status_from_ended_to_closed(self):
        self.listing.ends_at = timezone.now() - timedelta(minutes=1)
        self.listing.save()
        self.assertEqual(self.listing.status, Listing.STATUS_ENDED)

        close_auction(self.listing)

        self.listing.refresh_from_db()
        self.assertEqual(self.listing.status, Listing.STATUS_CLOSED)

    def test_close_auction_survives_a_broken_notification_email(self):
        """A send_mail failure (e.g. a header-validation error from a listing
        title containing newlines) must not stop the listing from being
        closed and the winner from being marked - it should just skip the
        notification.
        """
        from unittest.mock import patch

        self.listing.ends_at = timezone.now() - timedelta(minutes=1)
        self.listing.save()
        emailed_bidder = User.objects.create_user(
            username='emailed', password='pass12345', email='emailed@example.com',
        )
        Bid.objects.create(listing=self.listing, bidder=emailed_bidder, amount='45.00')

        with patch('timers.tasks.send_mail', side_effect=ValueError('Header values cannot contain newlines')):
            result = close_auction(self.listing)

        self.listing.refresh_from_db()
        self.assertIsNotNone(result)
        self.assertTrue(result.is_winner)
        self.assertEqual(self.listing.status, Listing.STATUS_CLOSED)


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

    def test_command_keeps_processing_after_one_listing_raises(self):
        from io import StringIO
        from unittest.mock import patch

        broken = self.make_listing(timezone.now() - timedelta(minutes=1))
        healthy = self.make_listing(timezone.now() - timedelta(minutes=1))

        def side_effect(listing):
            if listing.pk == broken.pk:
                raise RuntimeError('boom')
            listing.is_active = False
            listing.save(update_fields=['is_active'])

        with patch('timers.management.commands.close_expired_auctions.close_auction', side_effect=side_effect):
            call_command('close_expired_auctions', stderr=StringIO())

        broken.refresh_from_db()
        healthy.refresh_from_db()
        self.assertTrue(broken.is_active)
        self.assertFalse(healthy.is_active)
