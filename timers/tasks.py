"""Auction timing jobs.

Closes auctions once their end time has passed. Intended to be triggered by
a scheduled backend job (e.g. a cron entry running the
``close_expired_auctions`` management command).
"""
from django.core.mail import send_mail
from django.conf import settings

from bids.models import Bid


def notify_winner(listing, winning_bid):
    """Email the winning bidder that they won ``listing``.

    Never raises: a listing title crafted to break header encoding (or any
    other mail-sending failure) must not stop the caller from finishing the
    rest of a batch close. ``fail_silently=True`` covers most backends, but
    header-validation errors from some backends (e.g. smtp) can surface
    before that guard applies, so this also catches explicitly.
    """
    if not winning_bid.bidder.email:
        return
    try:
        send_mail(
            subject=f'You won the auction for "{listing.title}"!',
            message=(
                f'Congratulations, {winning_bid.bidder.username}!\n\n'
                f'Your bid of {winning_bid.amount} won the auction for '
                f'"{listing.title}".'
            ),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[winning_bid.bidder.email],
            fail_silently=True,
        )
    except Exception:
        pass


def close_auction(listing):
    """Close ``listing`` if its auction window has ended.

    Only acts on listings whose ``status`` is ``Listing.STATUS_ENDED``
    (end time passed, not yet processed) - this is a no-op for listings
    that are still ``active`` or already ``closed``, which also makes it
    safe to call repeatedly on the same listing.

    Marks the listing ``closed``, marks the highest bid as the winner
    (breaking any tie by earliest bid, per ``Bid.Meta.ordering``), and
    emails the winner. Returns the winning ``Bid``, or ``None`` if the
    listing had no bids or didn't need closing.
    """
    if listing.status != listing.STATUS_ENDED:
        return None

    listing.is_active = False
    listing.save(update_fields=['is_active'])

    winning_bid = Bid.highest_for(listing)
    if winning_bid is None:
        return None

    winning_bid.is_winner = True
    winning_bid.save(update_fields=['is_winner'])
    notify_winner(listing, winning_bid)
    return winning_bid
