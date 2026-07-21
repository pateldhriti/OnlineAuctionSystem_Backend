from django.core.management.base import BaseCommand
from django.utils import timezone

from listings.models import Listing

from ...tasks import close_auction


class Command(BaseCommand):
    help = (
        'Close every active listing whose auction end time has passed. '
        'Intended to be run on a schedule (e.g. a cron entry every minute).'
    )

    def handle(self, *args, **options):
        # Mirrors Listing.status == Listing.STATUS_ENDED, expressed as a query
        # since `status` is a Python property and can't be filtered directly.
        expired = Listing.objects.filter(is_active=True, ends_at__lte=timezone.now())
        count = 0
        for listing in expired:
            try:
                close_auction(listing)
            except Exception as exc:
                # One bad listing shouldn't stop the rest of a scheduled run
                # from closing.
                self.stderr.write(self.style.ERROR(f'Failed to close listing {listing.pk}: {exc}'))
                continue
            count += 1
        self.stdout.write(self.style.SUCCESS(f'Closed {count} expired auction(s).'))
