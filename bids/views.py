from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from listings.models import Listing

from .forms import BidForm
from .models import Bid


def bid_history(request, listing_id):
    listing = get_object_or_404(Listing, pk=listing_id)
    bids = Bid.objects.filter(listing=listing).select_related('bidder')
    current_price = Bid.current_price_for(listing)
    can_bid = (
        request.user.is_authenticated
        and listing.is_active
        and listing.seller_id != request.user.pk
    )
    form = BidForm(listing=listing, bidder=request.user) if can_bid else None
    return render(
        request,
        'bids/bid_history.html',
        {
            'listing': listing,
            'bids': bids,
            'current_price': current_price,
            'can_bid': can_bid,
            'form': form,
        },
    )


@login_required
@require_POST
def place_bid(request, listing_id):
    listing = get_object_or_404(Listing, pk=listing_id)
    form = BidForm(request.POST, listing=listing, bidder=request.user)
    if form.is_valid():
        form.save()
        messages.success(request, 'Your bid was placed successfully.')
    else:
        for errors in form.errors.values():
            for error in errors:
                messages.error(request, error)
    return redirect('bids:history', listing_id=listing.pk)
