from django.conf import settings
from django.db import models


class Listing(models.Model):
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
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.title
