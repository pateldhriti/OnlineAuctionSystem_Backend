from django.db import models
from django.contrib.auth.models import User


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    phone = models.CharField(max_length=20, blank=True)
    bio = models.TextField(blank=True)
    # A photo, document, or ID for identity verification - any common image
    # or PDF, validated in ProfileForm.clean_id_document.
    id_document = models.FileField(upload_to='id_documents/', blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username}'s profile"


class DailyVisit(models.Model):
    """One row per (user, calendar date) they visited the site.

    ``visit_count`` is incremented once per new browser session on that day
    (see accounts.middleware.TrackVisitMiddleware), not once per page view.
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='daily_visits')
    date = models.DateField()
    visit_count = models.PositiveIntegerField(default=1)

    class Meta:
        ordering = ['-date']
        constraints = [
            models.UniqueConstraint(fields=['user', 'date'], name='one_daily_visit_row_per_user_per_day'),
        ]

    def __str__(self):
        return f'{self.user.username} on {self.date}: {self.visit_count}'
