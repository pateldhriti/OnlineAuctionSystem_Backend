# AuctionHub - Functionality to File Map

Every functionality in the system mapped to the exact files where the code lives.

---

## Project Configuration

| Functionality | File Path |
|---|---|
| Django settings (DB, email, apps, middleware) | `auction_project/settings.py` |
| Root URL routing | `auction_project/urls.py` |
| WSGI entry point | `auction_project/wsgi.py` |
| ASGI entry point | `auction_project/asgi.py` |
| Environment variables | `.env` |
| Environment template | `.env.example` |
| Python dependencies | `requirements.txt` |
| Render deployment config | `render.yaml` |
| Heroku/Gunicorn config | `Procfile` |
| Django management | `manage.py` |

---

## Base Template & Design System

| Functionality | File Path |
|---|---|
| Master layout (navbar, footer, CSS, JS) | `templates/base.html` |
| Navbar links, user dropdown, notification bell | `templates/base.html` (lines ~400-490) |
| CSS design system (colors, gradients, animations) | `templates/base.html` (lines ~10-390) |
| Countdown timer script | `timers/static/timers/countdown.js` |

---

## 1. User Authentication & Registration

| Functionality | File Path |
|---|---|
| User registration (view) | `accounts/views.py` → `register_view()` |
| User login (view) | `accounts/views.py` → `login_view()` |
| User logout (view) | `accounts/views.py` → `logout_view()` |
| Registration form | `accounts/forms.py` → `RegisterForm` |
| Login form | `accounts/forms.py` → `LoginForm` |
| URL routing | `accounts/urls.py` |
| Login template | `accounts/templates/accounts/login.html` |
| Registration template | `accounts/templates/accounts/register.html` |

---

## 2. User Profiles & Identity Verification

| Functionality | File Path |
|---|---|
| UserProfile model (phone, bio, id_document) | `accounts/models.py` → `UserProfile` |
| Profile view | `accounts/views.py` → `profile_view()` |
| Profile edit view | `accounts/views.py` → `profile_edit_view()` |
| User update form | `accounts/forms.py` → `UserUpdateForm` |
| Profile form (phone, bio, document) | `accounts/forms.py` → `ProfileForm` |
| Profile template | `accounts/templates/accounts/profile.html` |
| Profile edit template | `accounts/templates/accounts/profile_edit.html` |

---

## 3. Auction Listings

| Functionality | File Path |
|---|---|
| Listing model (title, description, category, price, image, ends_at) | `listings/models.py` → `Listing` |
| Listing list view (search, filter, paginate) | `listings/views.py` → `ListingListView` |
| Listing detail view | `listings/views.py` → `ListingDetailView` |
| Create listing view | `listings/views.py` → `create_listing()` |
| Edit listing view | `listings/views.py` → `update_listing()` |
| Delete listing view | `listings/views.py` → `delete_listing()` |
| Listing form (validation, image handling) | `listings/forms.py` → `ListingForm` |
| URL routing | `listings/urls.py` |
| Listing list template | `listings/templates/listings/listing_list.html` |
| Listing detail template | `listings/templates/listings/listing_detail.html` |
| Create/edit form template | `listings/templates/listings/listing_form.html` |
| Demo data seeder | `listings/management/commands/seed_demo.py` |
| Admin registration | `listings/admin.py` |

---

## 4. Image Upload & Thumbnail Cropping

| Functionality | File Path |
|---|---|
| Image & thumbnail fields | `listings/models.py` → `Listing.image`, `Listing.thumbnail` |
| Image processing (crop, resize with Pillow) | `listings/views.py` → `create_listing()`, `update_listing()` |
| Crop data JSON in form | `listings/forms.py` → `ListingForm` |
| Client-side crop UI | `listings/templates/listings/listing_form.html` |

---

## 5. Search & Category Filtering

| Functionality | File Path |
|---|---|
| Search + category filter logic | `listings/views.py` → `ListingListView.get_queryset()` |
| Category choices definition | `listings/models.py` → `Listing.CATEGORY_CHOICES` |
| Search bar + filter UI | `listings/templates/listings/listing_list.html` (lines 18-41) |

---

## 6. Manual Bidding

| Functionality | File Path |
|---|---|
| Bid model | `bids/models.py` → `Bid` |
| Place bid view | `bids/views.py` → `place_bid()` |
| Bid form (amount validation) | `bids/forms.py` → `BidForm` |
| Bid processing service | `bids/services.py` → `process_bid()` |
| Current price calculation | `bids/models.py` → `Bid.current_price_for()` |
| Highest bid lookup | `bids/models.py` → `Bid.highest_for()` |
| URL routing | `bids/urls.py` |
| Bid form UI (in bid history page) | `bids/templates/bids/bid_history.html` (lines 163-187) |

---

## 7. Auto-Bidding (Proxy Bidding)

| Functionality | File Path |
|---|---|
| AutoBid model (max_amount, increment) | `bids/models.py` → `AutoBid` |
| Auto-bid form | `bids/forms.py` → `AutoBidForm` |
| Set auto-bid view | `bids/views.py` → `set_auto_bid()` |
| Cancel auto-bid view | `bids/views.py` → `cancel_auto_bid()` |
| Auto-bid processing logic | `bids/services.py` → `process_bid()` (lines 50-86) |
| Edge case: bid max when increment exceeds budget | `bids/services.py` (lines 63-68) |
| Default increment fallback | `bids/services.py` → `DEFAULT_AUTO_BID_INCREMENT` |
| Auto-bid UI (set, update, cancel) | `bids/templates/bids/bid_history.html` (lines 189-252) |
| Increment migration | `bids/migrations/0005_add_increment_to_autobid.py` |

---

## 8. Anti-Sniping Timer Extension

| Functionality | File Path |
|---|---|
| Snipe detection & extension logic | `bids/services.py` → `_extend_if_sniping()` |
| Snipe window constant (2 min) | `bids/services.py` → `SNIPE_WINDOW` |
| Extension duration constant (3 min) | `bids/services.py` → `SNIPE_EXTENSION` |
| Called after manual bid | `bids/services.py` → `process_bid()` (line 43) |
| Called after auto-bid | `bids/services.py` → `process_bid()` (line 77) |

---

## 9. Live Countdown Timer with Server Sync

| Functionality | File Path |
|---|---|
| Client-side countdown (1s tick) | `timers/static/timers/countdown.js` → `tick()` |
| Server polling (10s interval) | `timers/static/timers/countdown.js` → `refreshTimers()` |
| Timer API endpoint | `listings/views.py` → `listing_timer()` |
| Timer API URL | `listings/urls.py` → `<int:pk>/timer/` |
| Timer display (listing detail) | `listings/templates/listings/listing_detail.html` (line 83) |
| Timer display (bid history) | `bids/templates/bids/bid_history.html` (line 43) |
| Timer display (listing list) | `listings/templates/listings/listing_list.html` (line 79) |
| data-listing-id attribute (listing detail) | `listings/templates/listings/listing_detail.html` (line 75) |
| data-listing-id attribute (bid history) | `bids/templates/bids/bid_history.html` (line 40) |
| data-listing-id attribute (listing list) | `listings/templates/listings/listing_list.html` (line 76) |
| Script inclusion | `templates/base.html` (line 539) |

---

## 10. Real-Time Listing Updates (AJAX)

| Functionality | File Path |
|---|---|
| AJAX polling script (5s interval) | `listings/static/listings/live_listing.js` |
| JSON response from detail view | `listings/views.py` → `ListingDetailView` |
| Script inclusion | `listings/templates/listings/listing_detail.html` |

---

## 11. Auction Closing & Winner Determination

| Functionality | File Path |
|---|---|
| Close auction logic | `timers/tasks.py` → `close_auction()` |
| Management command (cron job) | `timers/management/commands/close_expired_auctions.py` |
| Winner determination | `timers/tasks.py` → `close_auction()` (line 139) |
| Deactivate auto-bids on close | `timers/tasks.py` → `close_auction()` (line 146) |
| Notify losing bidders | `timers/tasks.py` → `close_auction()` (lines 153-167) |

---

## 12. Email Notifications (SMTP)

| Functionality | File Path |
|---|---|
| SMTP configuration | `auction_project/settings.py` (EMAIL_* settings) |
| Email credentials | `.env` → `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD` |
| dotenv loading | `auction_project/settings.py` (line 16) |
| Winner email | `timers/tasks.py` → `notify_winner()` |
| Seller email | `timers/tasks.py` → `notify_seller()` |
| Product details block | `timers/tasks.py` → `_product_block()` |
| Bid history summary | `timers/tasks.py` → `_bid_summary()` |
| Contact info block | `timers/tasks.py` → `_contact_block()` |
| Password reset email | Django built-in (configured in `accounts/urls.py`) |
| Contact form email | `pages/views.py` → `contact_submit()` |

---

## 13. In-App Notifications

| Functionality | File Path |
|---|---|
| Notification model | `notifications/models.py` → `Notification` |
| Notification list view | `notifications/views.py` → `notification_list()` |
| Mark as read | `notifications/views.py` → `mark_read()` |
| Mark all as read | `notifications/views.py` → `mark_all_read()` |
| Unread count API (AJAX) | `notifications/views.py` → `unread_count()` |
| Unread count context processor | `notifications/context_processors.py` |
| Notification helper functions | `notifications/helpers.py` |
| `notify_outbid()` | `notifications/helpers.py` |
| `notify_new_bid_on_listing()` | `notifications/helpers.py` |
| `notify_auction_won()` | `notifications/helpers.py` |
| `notify_auction_lost()` | `notifications/helpers.py` |
| `notify_auction_sold()` | `notifications/helpers.py` |
| `notify_auto_bid_placed()` | `notifications/helpers.py` |
| `notify_auto_bid_exceeded()` | `notifications/helpers.py` |
| `notify_new_message()` | `notifications/helpers.py` |
| URL routing | `notifications/urls.py` |
| Notification list template | `notifications/templates/notifications/notification_list.html` |
| Navbar bell badge | `templates/base.html` |

---

## 14. Private Messaging (Conversations)

| Functionality | File Path |
|---|---|
| Conversation model | `conversations/models.py` → `Conversation` |
| Message model | `conversations/models.py` → `Message` |
| Conversation list view | `conversations/views.py` → `conversation_list()` |
| Conversation detail view | `conversations/views.py` → `conversation_detail()` |
| Send message view | `conversations/views.py` → `send_message()` |
| Message form | `conversations/forms.py` → `MessageForm` |
| URL routing | `conversations/urls.py` |
| Conversation list template | `conversations/templates/conversations/conversation_list.html` |
| Conversation detail template | `conversations/templates/conversations/conversation_detail.html` |
| Auto-create on first bid | `bids/views.py` → `place_bid()` (line 67) |
| Auto-create on auction close | `timers/tasks.py` → `close_auction()` (line 145) |

---

## 15. Reviews & Ratings

| Functionality | File Path |
|---|---|
| Review model (rating 1-5, comment) | `reviews/models.py` → `Review` |
| Leave review view | `reviews/views.py` → `leave_review()` |
| User reviews view (avg rating) | `reviews/views.py` → `user_reviews()` |
| Review form | `reviews/forms.py` → `ReviewForm` |
| URL routing | `reviews/urls.py` |
| Leave review template (star UI) | `reviews/templates/reviews/leave_review.html` |
| Star rating JavaScript | `reviews/templates/reviews/leave_review.html` (lines 77-102) |
| User reviews template | `reviews/templates/reviews/user_reviews.html` |
| Rate button on bid history | `bids/templates/bids/bid_history.html` (lines 69-73) |
| Duplicate review prevention | `reviews/views.py` → `leave_review()` |

---

## 16. Watchlist

| Functionality | File Path |
|---|---|
| Watchers M2M field | `listings/models.py` → `Listing.watchers` |
| Toggle watchlist view | `listings/views.py` → `toggle_watchlist()` |
| Watchlist page view | `listings/views.py` → `watchlist()` |
| Watch button UI | `listings/templates/listings/listing_detail.html` |

---

## 17. Seller Dashboard

| Functionality | File Path |
|---|---|
| Dashboard view | `accounts/views.py` → `seller_dashboard_view()` |
| Dashboard template | `accounts/templates/accounts/seller_dashboard.html` |
| Navbar link ("My Listings") | `templates/base.html` (line ~443) |

---

## 18. Bid History & Management

| Functionality | File Path |
|---|---|
| Bid history view | `bids/views.py` → `bid_history()` |
| Edit bid view | `bids/views.py` → `edit_bid()` |
| Delete bid view | `bids/views.py` → `delete_bid()` |
| Bid history template | `bids/templates/bids/bid_history.html` |
| Edit bid template | `bids/templates/bids/edit_bid.html` |

---

## 19. Daily Visit Tracking

| Functionality | File Path |
|---|---|
| DailyVisit model | `accounts/models.py` → `DailyVisit` |
| Visit tracking middleware | `accounts/middleware.py` → `TrackVisitMiddleware` |
| History view (last 14 days) | `accounts/views.py` → `history_view()` |
| Recently viewed utility | `accounts/utils.py` |
| History template | `accounts/templates/accounts/history.html` |

---

## 20. Password Reset

| Functionality | File Path |
|---|---|
| Password change view | `accounts/views.py` → `password_change_view()` |
| Password reset URLs | `accounts/urls.py` (lines for reset flow) |
| Reset form styling | `accounts/forms.py` → `AuctionPasswordResetForm` |
| Set password form styling | `accounts/forms.py` → `AuctionSetPasswordForm` |
| Reset form template | `accounts/templates/accounts/password_reset_form.html` |
| Reset done template | `accounts/templates/accounts/password_reset_done.html` |
| Reset confirm template | `accounts/templates/accounts/password_reset_confirm.html` |
| Reset complete template | `accounts/templates/accounts/password_reset_complete.html` |
| Password change template | `accounts/templates/accounts/password_change.html` |

---

## 21. Contact Form

| Functionality | File Path |
|---|---|
| Contact form class | `pages/forms.py` → `ContactForm` |
| Contact submit view | `pages/views.py` → `contact_submit()` |
| Contact form UI | `pages/templates/pages/home.html` |

---

## 22. Static Pages

| Functionality | File Path |
|---|---|
| Home page view | `pages/views.py` → `home()` |
| About page view | `pages/views.py` → `about()` |
| Team page view | `pages/views.py` → `team()` |
| Privacy page view | `pages/views.py` → `privacy()` |
| Terms page view | `pages/views.py` → `terms()` |
| Home template | `pages/templates/pages/home.html` |
| About template | `pages/templates/pages/about.html` |
| Team template | `pages/templates/pages/team.html` |
| Privacy template | `pages/templates/pages/privacy.html` |
| Terms template | `pages/templates/pages/terms.html` |

---

## 23. Admin Interface

| Functionality | File Path |
|---|---|
| Listing admin | `listings/admin.py` |
| Bid & AutoBid admin | `bids/admin.py` |
| UserProfile & DailyVisit admin | `accounts/admin.py` |
| Conversation & Message admin | `conversations/admin.py` |
| Notification admin | `notifications/admin.py` |
| Review admin | `reviews/admin.py` |

---

## Database Migrations

| App | Migration Files |
|---|---|
| accounts | `accounts/migrations/0001_initial.py`, `0002_dailyvisit.py`, `0003_userprofile_id_document.py` |
| listings | `listings/migrations/0001_initial.py`, `0002_listing_category_image_watchers.py`, `0003_listing_ends_at.py`, `0004_listing_active_ends_idx.py`, `0005_listing_thumbnail.py` |
| bids | `bids/migrations/0001_initial.py`, `0002_bid_is_winner.py`, `0003_alter_bid_options_bid_listing_amount_idx.py`, `0004_bid_is_auto_autobid.py`, `0005_add_increment_to_autobid.py` |
| conversations | `conversations/migrations/0001_initial.py` |
| notifications | `notifications/migrations/0001_initial.py` |
| reviews | `reviews/migrations/0001_initial.py` |

---

## Template Hierarchy

```
templates/base.html
├── accounts/templates/accounts/
│   ├── login.html
│   ├── register.html
│   ├── profile.html
│   ├── profile_edit.html
│   ├── history.html
│   ├── my_bids.html
│   ├── seller_dashboard.html
│   ├── password_change.html
│   ├── password_reset_form.html
│   ├── password_reset_done.html
│   ├── password_reset_confirm.html
│   └── password_reset_complete.html
├── listings/templates/listings/
│   ├── listing_list.html
│   ├── listing_detail.html
│   └── listing_form.html
├── bids/templates/bids/
│   ├── bid_history.html
│   └── edit_bid.html
├── conversations/templates/conversations/
│   ├── conversation_list.html
│   └── conversation_detail.html
├── notifications/templates/notifications/
│   └── notification_list.html
├── reviews/templates/reviews/
│   ├── leave_review.html
│   └── user_reviews.html
└── pages/templates/pages/
    ├── home.html
    ├── about.html
    ├── team.html
    ├── privacy.html
    └── terms.html
```
