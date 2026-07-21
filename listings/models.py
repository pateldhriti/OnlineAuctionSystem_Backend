from datetime import timedelta

from django.conf import settings
from django.db import models
from django.utils import timezone

DEFAULT_AUCTION_DURATION = timedelta(days=7)


class Listing(models.Model):
    STATUS_ACTIVE = 'active'
    STATUS_ENDED = 'ended'
    STATUS_CLOSED = 'closed'

    class Category(models.TextChoices):
        ELECTRONICS = 'electronics', 'Electronics'
        FASHION = 'fashion', 'Fashion'
        HOME = 'home', 'Home'
        BOOKS = 'books', 'Books'
        SPORTS = 'sports', 'Sports'
        TOYS = 'toys', 'Toys'
        VEHICLES = 'vehicles', 'Vehicles'
        OTHER = 'other', 'Other'

    seller = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='listings',
    )
    title = models.CharField(max_length=150)
    description = models.TextField()
    category = models.CharField(
        max_length=30,
        choices=Category.choices,
        default=Category.OTHER,
    )
    starting_price = models.DecimalField(max_digits=10, decimal_places=2)
    image = models.ImageField(upload_to='listing_images/', blank=True)
    watchers = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name='watchlist',
        blank=True,
    )
    is_active = models.BooleanField(default=True)
    ends_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            # Matches the query in close_expired_auctions, which is intended
            # to run on a recurring schedule (e.g. every minute).
            models.Index(fields=['is_active', 'ends_at'], name='listing_active_ends_idx'),
        ]

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if self.ends_at is None:
            self.ends_at = timezone.now() + DEFAULT_AUCTION_DURATION
        super().save(*args, **kwargs)

    @property
    def has_ended(self):
        return self.ends_at is not None and timezone.now() >= self.ends_at

    @property
    def status(self):
        """Single source of truth for auction state.

        ``active`` -> still open for bids. ``ended`` -> the end time has
        passed but ``close_auction`` hasn't processed it yet (bidding is
        already blocked, but no winner has been picked). ``closed`` ->
        ``close_auction`` has run and, if there were any bids, a winner has
        been picked.
        """
        if not self.is_active:
            return self.STATUS_CLOSED
        if self.has_ended:
            return self.STATUS_ENDED
        return self.STATUS_ACTIVE
