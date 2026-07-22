from django.contrib import admin

from .models import AutoBid, Bid


@admin.register(Bid)
class BidAdmin(admin.ModelAdmin):
    list_display = ['listing', 'bidder', 'amount', 'is_auto', 'is_winner', 'created_at']
    list_filter = ['is_winner', 'is_auto', 'created_at']
    search_fields = ['listing__title', 'bidder__username']
    readonly_fields = ['created_at']
    date_hierarchy = 'created_at'


@admin.register(AutoBid)
class AutoBidAdmin(admin.ModelAdmin):
    list_display = ['listing', 'bidder', 'max_amount', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['listing__title', 'bidder__username']
    readonly_fields = ['created_at']
