from django.conf import settings
from django.db import models


class Notification(models.Model):
    class Type(models.TextChoices):
        OUTBID = 'outbid', 'You have been outbid'
        AUCTION_WON = 'auction_won', 'You won an auction'
        AUCTION_LOST = 'auction_lost', 'You lost an auction'
        AUCTION_ENDING = 'auction_ending', 'Auction ending soon'
        AUCTION_SOLD = 'auction_sold', 'Your item was sold'
        NEW_BID = 'new_bid', 'New bid on your listing'
        NEW_MESSAGE = 'new_message', 'New message'
        AUTO_BID_PLACED = 'auto_bid_placed', 'Auto-bid placed on your behalf'
        AUTO_BID_EXCEEDED = 'auto_bid_exceeded', 'Your auto-bid limit was exceeded'

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notifications',
    )
    notification_type = models.CharField(max_length=30, choices=Type.choices)
    title = models.CharField(max_length=200)
    message = models.TextField()
    link = models.CharField(max_length=500, blank=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', '-created_at'], name='notif_user_created_idx'),
            models.Index(fields=['user', 'is_read'], name='notif_user_read_idx'),
        ]

    def __str__(self):
        return f'{self.user}: {self.title}'
