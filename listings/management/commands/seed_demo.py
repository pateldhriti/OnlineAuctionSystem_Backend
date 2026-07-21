from datetime import timedelta

from django.conf import settings
from django.contrib.auth.models import User
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from bids.models import Bid
from timers.tasks import close_auction

from ...models import Listing

DEMO_PASSWORD = 'demopass123'


class Command(BaseCommand):
    help = (
        'Seed the database with demo users, listings, and bids so the app '
        'has something to look at. Safe to re-run - reuses existing demo '
        'accounts/listings instead of duplicating them.'
    )

    def handle(self, *args, **options):
        if not settings.DEBUG:
            raise CommandError(
                'seed_demo creates an admin/superuser account with a known, '
                'hardcoded password (%s) - refusing to run with DEBUG=False.'
                % DEMO_PASSWORD
            )

        admin_user, admin_created = User.objects.get_or_create(
            username='admin',
            defaults={'email': 'admin@example.com', 'is_staff': True, 'is_superuser': True},
        )
        if admin_created:
            admin_user.set_password(DEMO_PASSWORD)
            admin_user.save()

        seller = self._demo_user('seller1', 'seller1@example.com')
        bidder_alice = self._demo_user('alice', 'alice@example.com')
        bidder_bob = self._demo_user('bob', 'bob@example.com')

        camera = self._demo_listing(
            seller, 'Vintage Camera', 'Electronics',
            'A classic 35mm film camera in great condition.',
            '50.00', ends_in=timedelta(days=3),
        )
        bike = self._demo_listing(
            seller, 'Mountain Bike', 'Sports',
            'Lightly used mountain bike, 21-speed.',
            '120.00', ends_in=timedelta(hours=6),
        )
        clock = self._demo_listing(
            seller, 'Antique Wall Clock', 'Home',
            'Hand-wound wall clock from the 1950s.',
            '75.00', ends_in=timedelta(minutes=-1),
        )

        self._demo_bid(camera, bidder_alice, '60.00')
        self._demo_bid(bike, bidder_bob, '135.00')
        self._demo_bid(bike, bidder_alice, '150.00')
        self._demo_bid(clock, bidder_alice, '90.00')
        self._demo_bid(clock, bidder_bob, '110.00')

        winning_bid = close_auction(clock)

        self.stdout.write(self.style.SUCCESS('Demo data ready.'))
        self.stdout.write('')
        self.stdout.write('Log in with any of these (password: %s):' % DEMO_PASSWORD)
        self.stdout.write('  admin   - staff account, see /admin/')
        self.stdout.write('  seller1 - lists Vintage Camera, Mountain Bike, Antique Wall Clock')
        self.stdout.write('  alice   - has bid on all three listings')
        self.stdout.write('  bob     - has bid on Mountain Bike and Antique Wall Clock')
        self.stdout.write('')
        if winning_bid:
            self.stdout.write(
                'Antique Wall Clock has already ended - won by %s at $%s '
                '(see the console for the notification email).'
                % (winning_bid.bidder.username, winning_bid.amount)
            )

    def _demo_user(self, username, email):
        user, created = User.objects.get_or_create(username=username, defaults={'email': email})
        if created:
            user.set_password(DEMO_PASSWORD)
            user.save()
        return user

    def _demo_listing(self, seller, title, category, description, starting_price, ends_in):
        listing, created = Listing.objects.get_or_create(
            title=title,
            defaults={
                'seller': seller,
                'description': description,
                'category': getattr(Listing.Category, category.upper()),
                'starting_price': starting_price,
            },
        )
        if created:
            listing.ends_at = timezone.now() + ends_in
            listing.save(update_fields=['ends_at'])
        return listing

    def _demo_bid(self, listing, bidder, amount):
        Bid.objects.get_or_create(listing=listing, bidder=bidder, defaults={'amount': amount})
