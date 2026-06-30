from django.contrib import admin

from .models import Bid


@admin.register(Bid)
class BidAdmin(admin.ModelAdmin):
    list_display = ['listing', 'bidder', 'amount', 'created_at']
    list_filter = ['created_at']
    search_fields = ['listing__title', 'bidder__username']
    readonly_fields = ['created_at']
