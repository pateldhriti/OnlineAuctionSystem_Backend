from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib import messages
from django.shortcuts import render, redirect
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from .forms import RegisterForm, LoginForm, UserUpdateForm, ProfileForm
from .middleware import VISIT_COOKIE_NAME
from .models import DailyVisit, UserProfile
from .utils import get_recently_viewed_ids


def register_view(request):
    if request.user.is_authenticated:
        return redirect('home')
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            UserProfile.objects.create(user=user)
            messages.success(request, 'Account created successfully. Please log in.')
            return redirect('accounts:login')
    else:
        form = RegisterForm()
    return render(request, 'accounts/register.html', {'form': form})


def login_view(request):
    if request.user.is_authenticated:
        return redirect('home')
    next_url = request.GET.get('next', '')
    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            user = authenticate(
                request,
                username=form.cleaned_data['username'],
                password=form.cleaned_data['password'],
            )
            if user:
                login(request, user)
                redirect_to = request.POST.get('next', '')
                if redirect_to and url_has_allowed_host_and_scheme(
                    redirect_to, allowed_hosts={request.get_host()}
                ):
                    return redirect(redirect_to)
                return redirect('home')
            messages.error(request, 'Invalid username or password.')
    else:
        form = LoginForm()
    return render(request, 'accounts/login.html', {'form': form, 'next': next_url})


@require_POST
def logout_view(request):
    logout(request)
    return redirect('accounts:login')


@login_required
def profile_view(request):
    from listings.models import Listing
    viewed_ids = get_recently_viewed_ids(request)
    listings_map = {l.id: l for l in Listing.objects.filter(id__in=viewed_ids)}
    recently_viewed = [listings_map[i] for i in viewed_ids if i in listings_map]
    return render(request, 'accounts/profile.html', {
        'recently_viewed': recently_viewed,
    })


@login_required
def profile_edit_view(request):
    profile, _ = UserProfile.objects.get_or_create(user=request.user)
    if request.method == 'POST':
        user_form = UserUpdateForm(request.POST, instance=request.user)
        profile_form = ProfileForm(request.POST, request.FILES, instance=profile)
        if user_form.is_valid() and profile_form.is_valid():
            user_form.save()
            profile_form.save()
            messages.success(request, 'Profile updated successfully.')
            return redirect('accounts:profile')
    else:
        user_form = UserUpdateForm(instance=request.user)
        profile_form = ProfileForm(instance=profile)
    return render(request, 'accounts/profile_edit.html', {
        'user_form': user_form,
        'profile_form': profile_form,
    })


@login_required
def history_view(request):
    from django.db.models import Sum

    from listings.models import Listing

    daily_visits = list(DailyVisit.objects.filter(user=request.user)[:14])
    total_visits = DailyVisit.objects.filter(user=request.user).aggregate(
        total=Sum('visit_count'),
    )['total'] or 0
    today_row = daily_visits[0] if daily_visits and daily_visits[0].date == timezone.localdate() else None

    viewed_ids = get_recently_viewed_ids(request)
    listings_map = {l.id: l for l in Listing.objects.filter(id__in=viewed_ids)}
    recently_viewed = [listings_map[i] for i in viewed_ids if i in listings_map]

    return render(request, 'accounts/history.html', {
        'daily_visits': daily_visits,
        'total_visits': total_visits,
        'visits_today': today_row.visit_count if today_row else 0,
        'last_visit_cookie': request.COOKIES.get(VISIT_COOKIE_NAME),
        'recently_viewed': recently_viewed,
    })


@login_required
def password_change_view(request):
    if request.method == 'POST':
        form = PasswordChangeForm(user=request.user, data=request.POST)
        if form.is_valid():
            form.save()
            update_session_auth_hash(request, form.user)
            messages.success(request, 'Password changed successfully.')
            return redirect('accounts:profile')
    else:
        form = PasswordChangeForm(user=request.user)
        for field in form.fields.values():
            field.widget.attrs['class'] = 'form-control'
    return render(request, 'accounts/password_change.html', {'form': form})


@login_required
def seller_dashboard_view(request):
    from listings.models import Listing

    listings = (
        Listing.objects
        .filter(seller=request.user)
        .prefetch_related('bids__bidder')
        .order_by('-created_at')
    )

    dashboard_data = []
    for listing in listings:
        # `listing.bids.all()` reuses the prefetch cache above (it's already
        # ordered per Bid.Meta.ordering); calling Bid.highest_for/
        # current_price_for here would issue two fresh, uncached queries per
        # listing instead.
        bids = list(listing.bids.all())
        highest_bid = bids[0] if bids else None
        dashboard_data.append({
            'listing': listing,
            'current_price': highest_bid.amount if highest_bid else listing.starting_price,
            'bid_count': len(bids),
            'winner': highest_bid.bidder if listing.has_ended and highest_bid else None,
        })

    active_count = sum(1 for d in dashboard_data if d['listing'].is_active and not d['listing'].has_ended)
    total_bids = sum(d['bid_count'] for d in dashboard_data)

    return render(request, 'accounts/seller_dashboard.html', {
        'dashboard_data': dashboard_data,
        'total_listings': len(dashboard_data),
        'active_count': active_count,
        'total_bids': total_bids,
    })
