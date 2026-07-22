from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from conversations.models import Conversation
from listings.models import Listing

from .forms import AutoBidForm, BidForm
from .models import AutoBid, Bid
from .services import process_bid

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

    auto_bid_form = None
    existing_auto_bid = None
    if can_bid:
        existing_auto_bid = AutoBid.objects.filter(
            listing=listing, bidder=request.user, is_active=True,
        ).first()
        auto_bid_form = AutoBidForm(listing=listing, bidder=request.user)

    bids = Bid.objects.filter(listing=listing).select_related('bidder')
    paginator = Paginator(bids, BIDS_PAGE_SIZE)
    page_obj = paginator.get_page(request.GET.get('page'))
    conversation = None
    if request.user.is_authenticated and listing.seller_id != request.user.pk:
        if Bid.objects.filter(listing=listing, bidder=request.user).exists():
            conversation, _ = Conversation.objects.get_or_create(listing=listing, bidder=request.user)
    return {
        'listing': listing,
        'bids': page_obj,
        'page_obj': page_obj,
        'current_price': Bid.current_price_for(listing),
        'can_bid': can_bid,
        'form': form,
        'auto_bid_form': auto_bid_form,
        'existing_auto_bid': existing_auto_bid,
        'conversation': conversation,
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
        process_bid(listing, request.user, form.cleaned_data['amount'])
        Conversation.objects.get_or_create(listing=listing, bidder=request.user)
        messages.success(request, 'Your bid was placed successfully.')
        return redirect('bids:history', listing_id=listing.pk)
    return render(request, 'bids/bid_history.html', _bid_history_context(request, listing, form=form))


@login_required
@require_POST
def set_auto_bid(request, listing_id):
    listing = get_object_or_404(Listing, pk=listing_id)
    form = AutoBidForm(request.POST, listing=listing, bidder=request.user)
    if form.is_valid():
        form.save()
        messages.success(request, f'Auto-bid set up to ${form.cleaned_data["max_amount"]}.')
        return redirect('bids:history', listing_id=listing.pk)
    ctx = _bid_history_context(request, listing)
    ctx['auto_bid_form'] = form
    return render(request, 'bids/bid_history.html', ctx)


@login_required
@require_POST
def cancel_auto_bid(request, listing_id):
    AutoBid.objects.filter(
        listing_id=listing_id, bidder=request.user, is_active=True,
    ).update(is_active=False)
    messages.success(request, 'Auto-bid cancelled.')
    return redirect('bids:history', listing_id=listing_id)


@login_required
def edit_bid(request, bid_id):
    bid = get_object_or_404(Bid, pk=bid_id, bidder=request.user)
    listing = bid.listing

    if not listing.is_active or listing.has_ended:
        messages.error(request, 'This auction is closed — bids can no longer be changed.')
        return redirect('bids:history', listing_id=listing.pk)

    highest = Bid.highest_for(listing)
    if highest and highest.pk == bid.pk:
        messages.error(request, 'You cannot edit the current highest bid.')
        return redirect('bids:history', listing_id=listing.pk)

    if request.method == 'POST':
        new_amount = request.POST.get('amount')
        try:
            from decimal import Decimal, InvalidOperation
            new_amount = Decimal(new_amount)
            if new_amount <= 0:
                raise ValueError
        except (InvalidOperation, ValueError, TypeError):
            messages.error(request, 'Please enter a valid bid amount.')
            return redirect('bids:history', listing_id=listing.pk)

        current_price = Bid.current_price_for(listing)
        if new_amount > current_price:
            messages.error(request, 'Use "Place a Bid" for amounts above the current price.')
            return redirect('bids:history', listing_id=listing.pk)

        bid.amount = new_amount
        bid.save()
        messages.success(request, f'Bid updated to ${new_amount}.')
        return redirect('bids:history', listing_id=listing.pk)

    return render(request, 'bids/edit_bid.html', {
        'bid': bid,
        'listing': listing,
    })


@login_required
@require_POST
def delete_bid(request, bid_id):
    bid = get_object_or_404(Bid, pk=bid_id, bidder=request.user)
    listing = bid.listing

    if not listing.is_active or listing.has_ended:
        messages.error(request, 'This auction is closed — bids can no longer be removed.')
        return redirect('bids:history', listing_id=listing.pk)

    highest = Bid.highest_for(listing)
    if highest and highest.pk == bid.pk:
        messages.error(request, 'You cannot delete the current highest bid.')
        return redirect('bids:history', listing_id=listing.pk)

    bid.delete()
    messages.success(request, 'Bid deleted.')
    return redirect('bids:history', listing_id=listing.pk)
