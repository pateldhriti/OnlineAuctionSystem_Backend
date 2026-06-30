from django.urls import path

from . import views

app_name = 'bids'

urlpatterns = [
    path('place/<int:listing_id>/', views.place_bid, name='place'),
]
