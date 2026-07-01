"""Auction timing jobs.

Phase 1 stub — no scheduling yet. Phase 2 wires this into a real
backend job (Celery/cron/signal) that closes auctions when they end.
"""


def close_auction(listing):
    """Close the auction for ``listing``.

    TODO Phase 2: mark the listing inactive, pick the winning bid,
    and hook this into the scheduler.
    """
    return None
