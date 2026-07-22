from django.conf import settings
from django.db import models

from listings.models import Listing


class Conversation(models.Model):
    """A private thread between one bidder and a listing's seller.

    Created the first time that bidder places a bid on the listing; the
    seller is derived from ``listing.seller`` rather than stored separately,
    since a listing only ever has one seller.
    """
    listing = models.ForeignKey(Listing, on_delete=models.CASCADE, related_name='conversations')
    bidder = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='bidder_conversations',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        constraints = [
            models.UniqueConstraint(fields=['listing', 'bidder'], name='one_conversation_per_bidder_per_listing'),
        ]

    def __str__(self):
        return f'{self.bidder} <-> {self.listing.seller} about {self.listing}'

    def is_participant(self, user):
        return user.pk == self.bidder_id or user.pk == self.listing.seller_id


class Message(models.Model):
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='sent_messages')
    body = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f'{self.sender}: {self.body[:30]}'
