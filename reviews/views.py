from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db.models import Avg
from django.shortcuts import get_object_or_404, redirect, render

from bids.models import Bid
from listings.models import Listing

from .forms import ReviewForm
from .models import Review


@login_required
def leave_review(request, listing_id):
    listing = get_object_or_404(Listing, pk=listing_id)

    if listing.is_active:
        messages.error(request, 'You can only review after the auction ends.')
        return redirect('listings:detail', pk=listing.pk)

    winning_bid = Bid.objects.filter(listing=listing, is_winner=True).first()
    if not winning_bid:
        messages.error(request, 'No winner for this auction.')
        return redirect('listings:detail', pk=listing.pk)

    is_winner = winning_bid.bidder_id == request.user.pk
    is_seller = listing.seller_id == request.user.pk
    if not is_winner and not is_seller:
        messages.error(request, 'Only the buyer and seller can leave reviews.')
        return redirect('listings:detail', pk=listing.pk)

    reviewee = listing.seller if is_winner else winning_bid.bidder

    existing = Review.objects.filter(listing=listing, reviewer=request.user).first()
    if existing:
        messages.info(request, 'You have already reviewed this transaction.')
        return redirect('reviews:user_reviews', user_id=reviewee.pk)

    if request.method == 'POST':
        form = ReviewForm(request.POST)
        if form.is_valid():
            review = form.save(commit=False)
            review.listing = listing
            review.reviewer = request.user
            review.reviewee = reviewee
            review.save()
            messages.success(request, 'Review submitted successfully.')
            return redirect('reviews:user_reviews', user_id=reviewee.pk)
    else:
        form = ReviewForm()

    return render(request, 'reviews/leave_review.html', {
        'form': form,
        'listing': listing,
        'reviewee': reviewee,
        'is_winner': is_winner,
    })


def user_reviews(request, user_id):
    reviewed_user = get_object_or_404(User, pk=user_id)
    reviews = Review.objects.filter(reviewee=reviewed_user).select_related(
        'reviewer', 'listing',
    )
    stats = reviews.aggregate(
        avg_rating=Avg('rating'),
    )
    return render(request, 'reviews/user_reviews.html', {
        'reviewed_user': reviewed_user,
        'reviews': reviews,
        'avg_rating': stats['avg_rating'],
        'review_count': reviews.count(),
    })
