from django.urls import path

from . import views

app_name = 'reviews'

urlpatterns = [
    path('leave/<int:listing_id>/', views.leave_review, name='leave_review'),
    path('user/<int:user_id>/', views.user_reviews, name='user_reviews'),
]
