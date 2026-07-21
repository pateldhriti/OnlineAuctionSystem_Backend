from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from listings.models import Listing

from .forms import BidForm
from .models import Bid

BIDS_PAGE_SIZE = 20


def _bid_history_context(request, listing, form=None):
    can_bid = (
        request.user.is_authenticated
        and listing.is_active
        and not listing.has_ended
        and listing.seller_id != request.user.pk
    )
    if form is None:
        form = BidForm(listing=listing, bidder=request.user) if can_bid else None
    bids = Bid.objects.filter(listing=listing).select_related('bidder')
    paginator = Paginator(bids, BIDS_PAGE_SIZE)
    page_obj = paginator.get_page(request.GET.get('page'))
    return {
        'listing': listing,
        'bids': page_obj,
        'page_obj': page_obj,
        'current_price': Bid.current_price_for(listing),
        'can_bid': can_bid,
        'form': form,
    }


def bid_history(request, listing_id):
    listing = get_object_or_404(Listing, pk=listing_id)
    return render(request, 'bids/bid_history.html', _bid_history_context(request, listing))


@login_required
@require_POST
def place_bid(request, listing_id):
    listing = get_object_or_404(Listing, pk=listing_id)
    form = BidForm(request.POST, listing=listing, bidder=request.user)
    if form.is_valid():
        form.save()
        messages.success(request, 'Your bid was placed successfully.')
        return redirect('bids:history', listing_id=listing.pk)
    return render(request, 'bids/bid_history.html', _bid_history_context(request, listing, form=form))
