RECENTLY_VIEWED_KEY = 'recently_viewed'
RECENTLY_VIEWED_MAX = 5


def add_to_recently_viewed(request, listing_id):
    """Add a listing ID to the session-based recently viewed list (max 5, most recent first)."""
    viewed = request.session.get(RECENTLY_VIEWED_KEY, [])
    listing_id = int(listing_id)
    if listing_id in viewed:
        viewed.remove(listing_id)
    viewed.insert(0, listing_id)
    request.session[RECENTLY_VIEWED_KEY] = viewed[:RECENTLY_VIEWED_MAX]


def get_recently_viewed_ids(request):
    """Return the list of recently viewed listing IDs from the session."""
    return request.session.get(RECENTLY_VIEWED_KEY, [])
