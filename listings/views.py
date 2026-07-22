import base64
import io
import json

from PIL import Image as PILImage

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db.models import Max, Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST
from django.views.generic import DetailView, ListView

from accounts.utils import add_to_recently_viewed
from bids.models import Bid

from .forms import ListingForm
from .models import Listing

THUMBNAIL_SIZE = (640, 360)


def _make_thumbnail(image_field, crop_data_json):
    """Crop the uploaded image according to crop_data and save as thumbnail."""
    try:
        crop = json.loads(crop_data_json)
        x = int(crop['x'])
        y = int(crop['y'])
        w = int(crop['width'])
        h = int(crop['height'])
    except (json.JSONDecodeError, KeyError, TypeError, ValueError):
        return None

    img = PILImage.open(image_field)
    img = img.convert('RGB')
    cropped = img.crop((x, y, x + w, y + h))
    cropped.thumbnail(THUMBNAIL_SIZE, PILImage.LANCZOS)

    buf = io.BytesIO()
    cropped.save(buf, format='JPEG', quality=85)
    buf.seek(0)
    return SimpleUploadedFile(
        f'thumb_{image_field.name}',
        buf.read(),
        content_type='image/jpeg',
    )


def get_safe_redirect_url(request, fallback_url):
    next_url = request.POST.get('next')
    if next_url and url_has_allowed_host_and_scheme(
        next_url,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        return next_url
    return fallback_url


LISTINGS_PAGE_SIZE = 12


class ListingListView(ListView):
    model = Listing
    template_name = 'listings/listing_list.html'
    context_object_name = 'listings'
    paginate_by = LISTINGS_PAGE_SIZE

    def get_queryset(self):
        query = self.request.GET.get('q', '').strip()
        active_category = self.request.GET.get('category', '')
        category_values = dict(Listing.Category.choices)
        listings = Listing.objects.select_related('seller').annotate(
            highest_bid_amount=Max('bids__amount'),
        ).order_by('-created_at')

        if query:
            listings = listings.filter(Q(title__icontains=query) | Q(description__icontains=query))

        if active_category in category_values:
            listings = listings.filter(category=active_category)

        return listings

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        active_category = self.request.GET.get('category', '')
        if active_category not in dict(Listing.Category.choices):
            active_category = ''
        context['categories'] = Listing.Category.choices
        context['active_category'] = active_category
        context['query'] = self.request.GET.get('q', '').strip()
        return context


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


class ListingDetailView(DetailView):
    model = Listing
    template_name = 'listings/listing_detail.html'
    context_object_name = 'listing'

    def get_queryset(self):
        return Listing.objects.select_related('seller')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        listing = self.object
        self._is_watched = (
            self.request.user.is_authenticated
            and listing.watchers.filter(pk=self.request.user.pk).exists()
        )
        add_to_recently_viewed(self.request, listing.pk)
        self._bid_state = _listing_bid_state(listing)
        context['is_watched'] = self._is_watched
        context.update(self._bid_state)
        return context

    def render_to_response(self, context, **response_kwargs):
        if _wants_json(self.request):
            return JsonResponse(_listing_payload(self.object, self._is_watched, self._bid_state))
        return super().render_to_response(context, **response_kwargs)


@login_required
def create_listing(request):
    if request.method == 'POST':
        form = ListingForm(request.POST, request.FILES)
        if form.is_valid():
            listing = form.save(commit=False)
            listing.seller = request.user
            listing.save()
            crop_data = request.POST.get('crop_data')
            if crop_data and listing.image:
                thumb = _make_thumbnail(listing.image, crop_data)
                if thumb:
                    listing.thumbnail.save(thumb.name, thumb, save=True)
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
            listing = form.save()
            crop_data = request.POST.get('crop_data')
            if crop_data and listing.image:
                thumb = _make_thumbnail(listing.image, crop_data)
                if thumb:
                    listing.thumbnail.save(thumb.name, thumb, save=True)
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
