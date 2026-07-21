from django.conf import settings
from django.db import models

from listings.models import Listing


class Bid(models.Model):
    listing = models.ForeignKey(
        Listing,
        on_delete=models.CASCADE,
        related_name='bids',
    )
    bidder = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='bids',
    )
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    is_winner = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        # Tie-break: among equal amounts, the earliest bid wins (first bidder
        # to reach that price), so ``highest_for`` can just take ``.first()``.
        ordering = ['-amount', 'created_at']
        indexes = [
            # Matches highest_for's filter+order, called on every bid-history
            # page view and every auction close.
            models.Index(fields=['listing', '-amount', 'created_at'], name='bid_listing_amount_idx'),
        ]

    def __str__(self):
        return f'{self.bidder} bid {self.amount} on {self.listing}'

    @classmethod
    def highest_for(cls, listing):
        return cls.objects.filter(listing=listing).first()

    @classmethod
    def current_price_for(cls, listing):
        highest = cls.highest_for(listing)
        return highest.amount if highest else listing.starting_price
