from django.contrib.auth.models import User
from django.test import TestCase

from listings.models import Listing

from .tasks import close_auction


class CloseAuctionStubTests(TestCase):
    def test_close_auction_stub_leaves_listing_untouched(self):
        seller = User.objects.create_user(username='seller', password='pass12345')
        listing = Listing.objects.create(
            seller=seller,
            title='Vintage Clock',
            description='A small table clock.',
            starting_price='25.00',
        )

        result = close_auction(listing)

        listing.refresh_from_db()
        self.assertIsNone(result)
        self.assertTrue(listing.is_active)
