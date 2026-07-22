from django.urls import reverse

from .models import Notification


def notify(user, notification_type, title, message, link=''):
    return Notification.objects.create(
        user=user,
        notification_type=notification_type,
        title=title,
        message=message,
        link=link,
    )


def notify_outbid(outbid_user, listing, new_amount):
    notify(
        user=outbid_user,
        notification_type=Notification.Type.OUTBID,
        title=f'Outbid on "{listing.title}"',
        message=f'Someone placed a bid of ${new_amount} on "{listing.title}". Place a higher bid to stay in the race!',
        link=reverse('bids:history', args=[listing.pk]),
    )


def notify_new_bid_on_listing(seller, listing, bidder, amount):
    notify(
        user=seller,
        notification_type=Notification.Type.NEW_BID,
        title=f'New bid on "{listing.title}"',
        message=f'{bidder.username} placed a bid of ${amount} on your listing "{listing.title}".',
        link=reverse('bids:history', args=[listing.pk]),
    )


def notify_auction_won(winner, listing, amount):
    notify(
        user=winner,
        notification_type=Notification.Type.AUCTION_WON,
        title=f'You won "{listing.title}"!',
        message=f'Congratulations! Your bid of ${amount} won the auction for "{listing.title}". Check the seller\'s contact details.',
        link=reverse('accounts:my_bids') + '?tab=won',
    )


def notify_auction_lost(loser, listing):
    notify(
        user=loser,
        notification_type=Notification.Type.AUCTION_LOST,
        title=f'Auction ended: "{listing.title}"',
        message=f'The auction for "{listing.title}" has ended and another bidder won. Better luck next time!',
        link=reverse('accounts:my_bids') + '?tab=lost',
    )


def notify_auction_sold(seller, listing, amount, winner):
    notify(
        user=seller,
        notification_type=Notification.Type.AUCTION_SOLD,
        title=f'Your item sold: "{listing.title}"',
        message=f'Your listing "{listing.title}" sold for ${amount} to {winner.username}. Check the buyer\'s contact details.',
        link=reverse('accounts:dashboard'),
    )


def notify_auto_bid_placed(bidder, listing, amount):
    notify(
        user=bidder,
        notification_type=Notification.Type.AUTO_BID_PLACED,
        title=f'Auto-bid placed on "{listing.title}"',
        message=f'Your auto-bid placed a bid of ${amount} on "{listing.title}" to keep you in the lead.',
        link=reverse('bids:history', args=[listing.pk]),
    )


def notify_auto_bid_exceeded(bidder, listing, new_amount):
    notify(
        user=bidder,
        notification_type=Notification.Type.AUTO_BID_EXCEEDED,
        title=f'Auto-bid limit exceeded on "{listing.title}"',
        message=f'A bid of ${new_amount} was placed on "{listing.title}" which exceeds your auto-bid limit. Increase your limit or place a manual bid.',
        link=reverse('bids:history', args=[listing.pk]),
    )


def notify_new_message(recipient, sender, conversation):
    notify(
        user=recipient,
        notification_type=Notification.Type.NEW_MESSAGE,
        title=f'New message from {sender.username}',
        message=f'{sender.username} sent you a message about "{conversation.listing.title}".',
        link=reverse('conversations:detail', args=[conversation.pk]),
    )
