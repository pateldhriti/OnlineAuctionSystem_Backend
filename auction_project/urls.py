from django.contrib import admin
from django.conf import settings
from django.conf.urls.static import static
from django.urls import path, include
from pages import views as pages_views

admin.site.site_header = 'Online Auction Administration'
admin.site.site_title = 'Online Auction Admin'
admin.site.index_title = 'Site Administration'

urlpatterns = [
    path('', pages_views.home, name='home'),
    path('contact/', pages_views.contact_submit, name='contact'),
    path('admin/', admin.site.urls),
    path('accounts/', include('accounts.urls')),
    path('listings/', include('listings.urls')),
    path('bids/', include('bids.urls')),
    path('timers/', include('timers.urls')),
    path('messages/', include('conversations.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
