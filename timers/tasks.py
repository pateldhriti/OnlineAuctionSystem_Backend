"""Auction timing jobs.

Closes auctions once their end time has passed. Intended to be triggered by
a scheduled backend job (e.g. a cron entry running the
``close_expired_auctions`` management command).
"""
from django.core.mail import send_mail
from django.conf import settings

from bids.models import AutoBid, Bid
from conversations.models import Conversation
from notifications.helpers import notify_auction_lost, notify_auction_sold, notify_auction_won


def _contact_block(user):
    lines = [f'  Name: {user.get_full_name() or user.username}']
    if user.email:
        lines.append(f'  Email: {user.email}')
    profile = getattr(user, 'profile', None)
    if profile and profile.phone:
        lines.append(f'  Phone: {profile.phone}')
    return '\n'.join(lines)


def _bid_summary(listing):
    bids = Bid.objects.filter(listing=listing).select_related('bidder')[:10]
    if not bids:
        return '  No bids placed.'
    lines = []
    for i, bid in enumerate(bids, 1):
        auto = ' (auto)' if bid.is_auto else ''
        winner = ' ★ WINNER' if bid.is_winner else ''
        lines.append(
            f'  {i}. {bid.bidder.username} — ${bid.amount}{auto}{winner}'
            f'  ({bid.created_at.strftime("%b %d, %Y %H:%M")})'
        )
    total = Bid.objects.filter(listing=listing).count()
    if total > 10:
        lines.append(f'  ... and {total - 10} more bids')
    return '\n'.join(lines)


def _product_block(listing):
    lines = [
        f'  Title: {listing.title}',
        f'  Category: {listing.get_category_display()}',
        f'  Starting Price: ${listing.starting_price}',
        f'  Description: {listing.description}',
    ]
    return '\n'.join(lines)


def notify_winner(listing, winning_bid):
    """Email the winning bidder with full auction details and seller contact."""
    if not winning_bid.bidder.email:
        return
    seller = listing.seller
    try:
        send_mail(
            subject=f'🎉 You won the auction for "{listing.title}"!',
            message=(
                f'Congratulations, {winning_bid.bidder.get_full_name() or winning_bid.bidder.username}!\n\n'
                f'Your bid of ${winning_bid.amount} won the auction for '
                f'"{listing.title}".\n\n'
                f'--- Product Details ---\n'
                f'{_product_block(listing)}\n\n'
                f'--- Winning Bid ---\n'
                f'  Amount: ${winning_bid.amount}\n'
                f'  Placed: {winning_bid.created_at.strftime("%b %d, %Y %H:%M")}\n\n'
                f'--- Bid History ---\n'
                f'{_bid_summary(listing)}\n\n'
                f'--- Seller Contact ---\n'
                f'{_contact_block(seller)}\n\n'
                f'Please reach out to the seller to arrange payment and delivery.\n\n'
                f'Thank you for using AuctionHub!'
            ),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[winning_bid.bidder.email],
            fail_silently=True,
        )
    except Exception:
        pass


def notify_seller(listing, winning_bid):
    """Email the seller with full auction details and buyer contact."""
    if not listing.seller.email:
        return
    winner = winning_bid.bidder
    total_bids = Bid.objects.filter(listing=listing).count()
    try:
        send_mail(
            subject=f'🎉 Your item "{listing.title}" has been sold!',
            message=(
                f'Hello {listing.seller.get_full_name() or listing.seller.username},\n\n'
                f'Great news! Your auction for "{listing.title}" has ended '
                f'with a winning bid.\n\n'
                f'--- Product Details ---\n'
                f'{_product_block(listing)}\n\n'
                f'--- Sale Summary ---\n'
                f'  Winning Bid: ${winning_bid.amount}\n'
                f'  Starting Price: ${listing.starting_price}\n'
                f'  Total Bids: {total_bids}\n\n'
                f'--- Winner Details ---\n'
                f'{_contact_block(winner)}\n\n'
                f'--- Bid History ---\n'
                f'{_bid_summary(listing)}\n\n'
                f'Please reach out to the buyer to arrange payment and delivery.\n\n'
                f'Thank you for selling on AuctionHub!'
            ),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[listing.seller.email],
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
    emails both the winner and the seller with each other's contact
    details. Returns the winning ``Bid``, or ``None`` if the listing had
    no bids or didn't need closing.
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
    Conversation.objects.get_or_create(listing=listing, bidder=winning_bid.bidder)
    AutoBid.objects.filter(listing=listing).update(is_active=False)

    notify_winner(listing, winning_bid)
    notify_seller(listing, winning_bid)
    notify_auction_won(winning_bid.bidder, listing, winning_bid.amount)
    notify_auction_sold(listing.seller, listing, winning_bid.amount, winning_bid.bidder)

    losing_bidder_ids = (
        Bid.objects
        .filter(listing=listing)
        .exclude(bidder=winning_bid.bidder)
        .values_list('bidder_id', flat=True)
        .distinct()
    )
    for bidder_id in losing_bidder_ids:
        from django.contrib.auth import get_user_model
        User = get_user_model()
        try:
            loser = User.objects.get(pk=bidder_id)
            notify_auction_lost(loser, listing)
        except User.DoesNotExist:
            pass

    return winning_bid
