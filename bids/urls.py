from django.urls import path

from . import views

app_name = 'bids'

urlpatterns = [
    path('place/<int:listing_id>/', views.place_bid, name='place'),
    path('<int:listing_id>/history/', views.bid_history, name='history'),
    path('<int:listing_id>/auto-bid/', views.set_auto_bid, name='set_auto_bid'),
    path('<int:listing_id>/auto-bid/cancel/', views.cancel_auto_bid, name='cancel_auto_bid'),
    path('edit/<int:bid_id>/', views.edit_bid, name='edit_bid'),
    path('delete/<int:bid_id>/', views.delete_bid, name='delete_bid'),
]
