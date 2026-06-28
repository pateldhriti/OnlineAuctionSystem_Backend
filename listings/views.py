from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from .forms import ListingForm
from .models import Listing


def listing_list(request):
    listings = Listing.objects.select_related('seller').all()
    return render(request, 'listings/listing_list.html', {'listings': listings})


@login_required
def create_listing(request):
    if request.method == 'POST':
        form = ListingForm(request.POST)
        if form.is_valid():
            listing = form.save(commit=False)
            listing.seller = request.user
            listing.save()
            messages.success(request, 'Listing created successfully.')
            return redirect('listings:list')
    else:
        form = ListingForm()
    return render(request, 'listings/listing_form.html', {'form': form})
