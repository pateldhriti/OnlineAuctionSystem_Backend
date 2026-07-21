from django.contrib import admin

from bids.models import Bid

from .models import Listing


class BidInline(admin.TabularInline):
    model = Bid
    extra = 0
    fields = ['bidder', 'amount', 'is_winner', 'created_at']
    readonly_fields = ['bidder', 'amount', 'is_winner', 'created_at']
    can_delete = False
    ordering = ['-amount', 'created_at']

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Listing)
class ListingAdmin(admin.ModelAdmin):
    list_display = [
        'title', 'seller', 'category', 'starting_price', 'status_display',
        'ends_at', 'created_at',
    ]
    list_filter = ['category', 'is_active', 'created_at']
    search_fields = ['title', 'description', 'seller__username']
    readonly_fields = ['created_at', 'updated_at']
    date_hierarchy = 'created_at'
    inlines = [BidInline]

    @admin.display(description='Status')
    def status_display(self, listing):
        return listing.status
