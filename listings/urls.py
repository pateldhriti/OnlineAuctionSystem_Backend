from django.urls import path

from . import views

app_name = 'listings'

urlpatterns = [
    path('', views.ListingListView.as_view(), name='list'),
    path('create/', views.create_listing, name='create'),
    path('watchlist/', views.watchlist, name='watchlist'),
    path('<int:pk>/', views.ListingDetailView.as_view(), name='detail'),
    path('<int:pk>/edit/', views.update_listing, name='update'),
    path('<int:pk>/delete/', views.delete_listing, name='delete'),
    path('<int:pk>/watch/', views.toggle_watchlist, name='toggle_watchlist'),
    path('<int:pk>/timer/', views.listing_timer, name='listing_timer'),
]
