from django.db.models import F
from django.utils import timezone

from .models import DailyVisit

VISIT_COOKIE_NAME = 'last_visit_date'
VISIT_COOKIE_MAX_AGE = 365 * 24 * 60 * 60
SESSION_VISIT_KEY = 'visit_counted_date'


class TrackVisitMiddleware:
    """Counts one "visit" per authenticated user per calendar day.

    Uses two different mechanisms together, as requested:
    - The **session** flags "this browser session already counted today's
      visit", so repeated page views in one sitting don't inflate the count.
    - A **cookie** persists the last-visit date across sessions (e.g. after
      the browser is closed and reopened), independent of server-side state,
      so it still reflects the last visit even if the session expired.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        if request.user.is_authenticated:
            today = timezone.localdate()
            if request.session.get(SESSION_VISIT_KEY) != today.isoformat():
                request.session[SESSION_VISIT_KEY] = today.isoformat()
                visit, created = DailyVisit.objects.get_or_create(user=request.user, date=today)
                if not created:
                    visit.visit_count = F('visit_count') + 1
                    visit.save(update_fields=['visit_count'])
            response.set_cookie(VISIT_COOKIE_NAME, today.isoformat(), max_age=VISIT_COOKIE_MAX_AGE)

        return response
