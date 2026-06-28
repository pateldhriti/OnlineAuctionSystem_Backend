from django.urls import path

from . import views

app_name = 'listings'

urlpatterns = [
    path('', views.listing_list, name='list'),
    path('create/', views.create_listing, name='create'),
]
