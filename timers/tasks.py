"""Auction timing jobs.

Closes auctions once their end time has passed. Intended to be triggered by
a scheduled backend job (e.g. a cron entry running the
``close_expired_auctions`` management command).
"""
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone

from bids.models import Bid


def notify_winner(listing, winning_bid):
    """Email the winning bidder that they won ``listing``."""
    if not winning_bid.bidder.email:
        return
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


def close_auction(listing):
    """Close ``listing`` if its auction window has ended.

    Marks the listing inactive, marks the highest bid as the winner, and
    emails the winner. Returns the winning ``Bid`` (or ``None`` if there
    were no bids). Returns ``None`` without any effect if the listing is
    already inactive or hasn't reached its end time yet.
    """
    if not listing.is_active:
        return None
    if listing.ends_at is not None and timezone.now() < listing.ends_at:
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
