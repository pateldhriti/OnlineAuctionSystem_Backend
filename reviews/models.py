from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models

from listings.models import Listing


class Review(models.Model):
    listing = models.ForeignKey(
        Listing,
        on_delete=models.CASCADE,
        related_name='reviews',
    )
    reviewer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='reviews_given',
    )
    reviewee = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='reviews_received',
    )
    rating = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
    )
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        constraints = [
            models.UniqueConstraint(
                fields=['listing', 'reviewer'],
                name='one_review_per_reviewer_per_listing',
            ),
        ]

    def __str__(self):
        return f'{self.reviewer} -> {self.reviewee}: {self.rating}/5 on {self.listing}'
