from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Max
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from accounts.utils import add_to_recently_viewed
from bids.models import Bid

from .forms import ListingForm
from .models import Listing


def get_safe_redirect_url(request, fallback_url):
    next_url = request.POST.get('next')
    if next_url and url_has_allowed_host_and_scheme(
        next_url,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        return next_url
    return fallback_url


def listing_list(request):
    active_category = request.GET.get('category', '')
    listings = Listing.objects.select_related('seller').annotate(
        highest_bid_amount=Max('bids__amount'),
    )
    category_values = dict(Listing.Category.choices)
    watched_listing_ids = set()

    if active_category in category_values:
        listings = listings.filter(category=active_category)
    else:
        active_category = ''

    if request.user.is_authenticated:
        watched_listing_ids = set(request.user.watchlist.values_list('pk', flat=True))

    return render(
        request,
        'listings/listing_list.html',
        {
            'listings': listings,
            'categories': Listing.Category.choices,
            'active_category': active_category,
            'watched_listing_ids': watched_listing_ids,
        },
    )


def _wants_json(request):
    accept_header = request.headers.get('Accept', '')
    return (
        request.GET.get('format') == 'json'
        or 'application/json' in accept_header
        or not accept_header
    )


def _listing_bid_state(listing):
    highest_bid = (
        Bid.objects
        .filter(listing=listing)
        .select_related('bidder')
        .first()
    )
    return {
        'highest_bid': highest_bid,
        'current_price': highest_bid.amount if highest_bid else listing.starting_price,
        'bid_count': listing.bids.count(),
        'is_open': listing.is_active and not listing.has_ended,
    }


def _listing_payload(listing, is_watched, bid_state):
    highest_bid = bid_state['highest_bid']
    return {
        'id': listing.pk,
        'title': listing.title,
        'description': listing.description,
        'category': listing.category,
        'category_display': listing.get_category_display(),
        'starting_price': str(listing.starting_price),
        'current_price': str(bid_state['current_price']),
        'highest_bid_amount': str(highest_bid.amount) if highest_bid else '',
        'highest_bidder': highest_bid.bidder.username if highest_bid else '',
        'bid_count': bid_state['bid_count'],
        'image_url': listing.image.url if listing.image else '',
        'seller': listing.seller.username,
        'is_active': listing.is_active,
        'has_ended': listing.has_ended,
        'is_open': bid_state['is_open'],
        'is_watched': is_watched,
        'ends_at': listing.ends_at.isoformat() if listing.ends_at else None,
        'created_at': listing.created_at.isoformat(),
        'updated_at': listing.updated_at.isoformat(),
    }


def listing_detail(request, pk):
    listing = get_object_or_404(
        Listing.objects.select_related('seller').prefetch_related('watchers'),
        pk=pk,
    )
    is_watched = (
        request.user.is_authenticated
        and listing.watchers.filter(pk=request.user.pk).exists()
    )
    add_to_recently_viewed(request, listing.pk)
    bid_state = _listing_bid_state(listing)

    if _wants_json(request):
        return JsonResponse(_listing_payload(listing, is_watched, bid_state))

    return render(
        request,
        'listings/listing_detail.html',
        {
            'listing': listing,
            'is_watched': is_watched,
            **bid_state,
        },
    )


@login_required
def create_listing(request):
    if request.method == 'POST':
        form = ListingForm(request.POST, request.FILES)
        if form.is_valid():
            listing = form.save(commit=False)
            listing.seller = request.user
            listing.save()
            messages.success(request, 'Listing created successfully.')
            return redirect('listings:detail', pk=listing.pk)
    else:
        form = ListingForm()
    return render(
        request,
        'listings/listing_form.html',
        {
            'form': form,
            'page_title': 'Create Listing',
            'button_text': 'Create listing',
        },
    )


@login_required
def update_listing(request, pk):
    listing = get_object_or_404(Listing, pk=pk, seller=request.user)
    if request.method == 'POST':
        form = ListingForm(request.POST, request.FILES, instance=listing)
        if form.is_valid():
            form.save()
            messages.success(request, 'Listing updated successfully.')
            return redirect('listings:detail', pk=listing.pk)
    else:
        form = ListingForm(instance=listing)
    return render(
        request,
        'listings/listing_form.html',
        {
            'form': form,
            'listing': listing,
            'page_title': 'Edit Listing',
            'button_text': 'Save changes',
        },
    )


@login_required
@require_POST
def delete_listing(request, pk):
    listing = get_object_or_404(Listing, pk=pk, seller=request.user)
    listing.delete()
    messages.success(request, 'Listing deleted successfully.')
    return redirect('listings:list')


@login_required
@require_POST
def toggle_watchlist(request, pk):
    listing = get_object_or_404(Listing, pk=pk)
    if listing.watchers.filter(pk=request.user.pk).exists():
        listing.watchers.remove(request.user)
        messages.success(request, 'Listing removed from your watchlist.')
    else:
        listing.watchers.add(request.user)
        messages.success(request, 'Listing added to your watchlist.')
    fallback_url = reverse('listings:detail', kwargs={'pk': listing.pk})
    return redirect(get_safe_redirect_url(request, fallback_url))


@login_required
def watchlist(request):
    listings = request.user.watchlist.select_related('seller').all()
    return JsonResponse(
        {
            'listings': [
                {
                    'id': listing.pk,
                    'title': listing.title,
                    'category': listing.category,
                    'category_display': listing.get_category_display(),
                    'starting_price': str(listing.starting_price),
                    'image_url': listing.image.url if listing.image else '',
                    'seller': listing.seller.username,
                }
                for listing in listings
            ]
        }
    )
