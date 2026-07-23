"""Core bid-placement logic including auto-bid proxy and sniping protection."""
from datetime import timedelta
from decimal import Decimal

from django.utils import timezone

from notifications.helpers import (
    notify_auto_bid_exceeded,
    notify_auto_bid_placed,
    notify_new_bid_on_listing,
    notify_outbid,
)

from .models import AutoBid, Bid

SNIPE_WINDOW = timedelta(minutes=2)
SNIPE_EXTENSION = timedelta(minutes=3)
DEFAULT_AUTO_BID_INCREMENT = Decimal('1.00')


def _extend_if_sniping(listing):
    if listing.ends_at and listing.is_active:
        remaining = listing.ends_at - timezone.now()
        if remaining < SNIPE_WINDOW:
            listing.ends_at = timezone.now() + SNIPE_EXTENSION
            listing.save(update_fields=['ends_at'])


def process_bid(listing, bidder, amount):
    """Place a bid and trigger auto-bid responses.

    Returns the list of all Bid objects created during this call
    (the manual bid plus any auto-bids it triggered).
    """
    created_bids = []

    previous_highest = Bid.highest_for(listing)
    previous_leader = previous_highest.bidder if previous_highest else None

    bid = Bid.objects.create(listing=listing, bidder=bidder, amount=amount)
    created_bids.append(bid)

    _extend_if_sniping(listing)

    notify_new_bid_on_listing(listing.seller, listing, bidder, amount)

    if previous_leader and previous_leader.pk != bidder.pk:
        notify_outbid(previous_leader, listing, amount)

    auto_bids = (
        AutoBid.objects
        .filter(listing=listing, is_active=True)
        .exclude(bidder=bidder)
        .select_related('bidder')
        .order_by('-max_amount', 'created_at')
    )

    for ab in auto_bids:
        current_price = Bid.current_price_for(listing)
        increment = ab.increment if ab.increment else DEFAULT_AUTO_BID_INCREMENT
        needed = current_price + increment

        if needed > ab.max_amount:
            if ab.max_amount > current_price:
                needed = ab.max_amount
            else:
                notify_auto_bid_exceeded(ab.bidder, listing, current_price)
                continue

        auto_bid_obj = Bid.objects.create(
            listing=listing,
            bidder=ab.bidder,
            amount=needed,
            is_auto=True,
        )
        created_bids.append(auto_bid_obj)
        _extend_if_sniping(listing)

        notify_auto_bid_placed(ab.bidder, listing, needed)

        current_leader = Bid.highest_for(listing)
        if current_leader and current_leader.bidder_id != bidder.pk:
            notify_outbid(bidder, listing, needed)

        break

    return created_bids
