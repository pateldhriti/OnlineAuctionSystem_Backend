from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect

from listings.models import Listing


@login_required
def place_bid(request, listing_id):
    listing = get_object_or_404(Listing, pk=listing_id)
    # TODO Phase 2: validate amount against highest bid and save the Bid.
    messages.info(request, 'Bidding is not available yet.')
    return redirect('listings:list')
