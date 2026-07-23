# AuctionHub - Feature Guide

A comprehensive guide explaining every feature in the Online Auction System, the technologies used, and how each feature is implemented.

---

## Table of Contents

1. [User Authentication & Registration](#1-user-authentication--registration)
2. [User Profiles & Identity Verification](#2-user-profiles--identity-verification)
3. [Auction Listings (Create, Edit, Delete)](#3-auction-listings-create-edit-delete)
4. [Image Upload & Thumbnail Cropping](#4-image-upload--thumbnail-cropping)
5. [Search & Category Filtering](#5-search--category-filtering)
6. [Manual Bidding](#6-manual-bidding)
7. [Auto-Bidding (Proxy Bidding)](#7-auto-bidding-proxy-bidding)
8. [Anti-Sniping Timer Extension](#8-anti-sniping-timer-extension)
9. [Live Countdown Timer with Server Sync](#9-live-countdown-timer-with-server-sync)
10. [Real-Time Listing Updates (AJAX)](#10-real-time-listing-updates-ajax)
11. [Auction Closing & Winner Determination](#11-auction-closing--winner-determination)
12. [Email Notifications (SMTP)](#12-email-notifications-smtp)
13. [In-App Notifications](#13-in-app-notifications)
14. [Private Messaging (Conversations)](#14-private-messaging-conversations)
15. [Reviews & Ratings](#15-reviews--ratings)
16. [Watchlist](#16-watchlist)
17. [Seller Dashboard](#17-seller-dashboard)
18. [Bid History & Management](#18-bid-history--management)
19. [Daily Visit Tracking](#19-daily-visit-tracking)
20. [Password Reset via Email](#20-password-reset-via-email)
21. [Contact Form](#21-contact-form)
22. [Static Pages](#22-static-pages)
23. [Responsive UI & Design System](#23-responsive-ui--design-system)
24. [Deployment Configuration](#24-deployment-configuration)

---

## 1. User Authentication & Registration

**What it does:** Users can register with a username, email, first/last name, and password. They can log in, log out, and are redirected to their intended page after login.

**Technologies used:**
- Django's built-in `UserCreationForm` extended with custom fields
- Django's `authenticate()` and `login()` functions for session-based authentication
- CSRF token protection on all forms
- `url_has_allowed_host_and_scheme()` for safe redirect after login

**How it works:**
- Registration creates a Django `User` and an associated `UserProfile`
- Login validates credentials and creates a session cookie
- A hidden `next` field on the login form preserves the URL the user was trying to access
- All protected views use the `@login_required` decorator

---

## 2. User Profiles & Identity Verification

**What it does:** Users can edit their profile (name, email, phone, bio) and upload an identity document (JPG, PNG, or PDF up to 5MB) for verification purposes.

**Technologies used:**
- Django `ModelForm` with two forms: `UserUpdateForm` (User model) and `ProfileForm` (UserProfile model)
- Django `ImageField` / `FileField` for document uploads
- Server-side file validation (extension whitelist + size check)
- Django `MEDIA_ROOT` / `MEDIA_URL` for file storage

**How it works:**
- `UserProfile` is a OneToOneField linked to the Django `User` model
- Profile edit view handles both forms simultaneously
- Uploaded documents are stored in `media/id_documents/`
- File validation rejects files over 5MB or with disallowed extensions

---

## 3. Auction Listings (Create, Edit, Delete)

**What it does:** Authenticated users can create auction listings with a title, description, category, starting price, image, and optional end time. Sellers can edit or delete their own listings.

**Technologies used:**
- Django `ModelForm` (`ListingForm`) with custom validation
- Django `@login_required` decorator for access control
- Soft delete pattern (sets `is_active=False`)
- Auto-generated `ends_at` (defaults to 7 days from creation)

**How it works:**
- The `Listing` model stores all auction item data
- On create, `seller` is set to `request.user`
- If no `ends_at` is provided, the model's `save()` method sets it to `now + 7 days`
- Edit view prevents changing `starting_price` after bids have been placed
- Delete marks `is_active=False` rather than removing from the database

---

## 4. Image Upload & Thumbnail Cropping

**What it does:** When creating/editing a listing, users upload an image and crop it client-side. A thumbnail (640x360) is generated server-side.

**Technologies used:**
- Client-side cropping UI (JavaScript) that sends crop coordinates as JSON
- Pillow (PIL) for server-side image processing
- Django `ImageField` for storage (original in `listing_images/`, thumbnail in `listing_thumbnails/`)

**How it works:**
- The form includes a hidden `crop_data` JSON field with x, y, width, height coordinates
- On save, the view reads the crop data, crops the image with Pillow, resizes to 640x360, and saves as JPEG at 85% quality
- Both the original image and thumbnail are stored separately

---

## 5. Search & Category Filtering

**What it does:** The listings page has a search bar (searches title and description) and a category dropdown filter. Results update on form submit.

**Technologies used:**
- Django ORM `Q` objects for OR-based text search (`title__icontains | description__icontains`)
- Django `ListView` with `get_queryset()` override
- HTML `<select>` with `onchange="this.form.requestSubmit()"` for instant category filtering
- 8 predefined categories in the `Listing` model (electronics, fashion, home, books, sports, toys, vehicles, other)

**How it works:**
- `ListingListView` reads `q` and `category` from GET parameters
- Builds a filtered queryset combining text search and category filter
- Results are paginated (12 per page)

---

## 6. Manual Bidding

**What it does:** Users can place manual bids on active listings. Bids must exceed the current highest bid. The seller cannot bid on their own listing.

**Technologies used:**
- Django `ModelForm` (`BidForm`) with custom validation
- `process_bid()` service function for bid placement logic
- `@require_POST` decorator to enforce POST-only
- Django messages framework for success/error feedback

**How it works:**
- `BidForm.clean()` validates: amount > current price, listing is active, bidder is not seller
- `process_bid()` creates the Bid, triggers auto-bid responses, sends notifications
- A `Conversation` is auto-created between the bidder and seller on first bid

---

## 7. Auto-Bidding (Proxy Bidding)

**What it does:** Users can set an auto-bid with a maximum amount and a custom increment. The system automatically places bids on their behalf when outbid, up to their maximum. If the increment would exceed the remaining budget but the max is still higher than the current price, the system bids the exact max amount.

**Technologies used:**
- `AutoBid` model with `max_amount`, `increment`, and `is_active` fields
- Unique constraint: one auto-bid per user per listing
- `update_or_create()` for upsert behavior
- Service layer pattern (`bids/services.py`) to separate business logic from views

**How it works:**
- When a manual bid is placed, `process_bid()` checks for active auto-bids on the listing (excluding the current bidder)
- For each auto-bid: calculates `needed = current_price + increment`
- If `needed > max_amount` but `max_amount > current_price`, bids the exact `max_amount` (edge case handling)
- If `max_amount <= current_price`, sends an "auto-bid exceeded" notification
- Creates auto-bid with `is_auto=True` flag
- Only the highest-priority auto-bid fires per round (ordered by `-max_amount`, `created_at`)

---

## 8. Anti-Sniping Timer Extension

**What it does:** If a bid is placed within the last 2 minutes of an auction, the auction end time is automatically extended by 3 minutes. This prevents last-second sniping.

**Technologies used:**
- `_extend_if_sniping()` function in `bids/services.py`
- Django's `timezone.now()` for timezone-aware time comparison
- `timedelta` for window and extension durations
- `listing.save(update_fields=['ends_at'])` for efficient database update

**How it works:**
- After every bid (manual or auto), `_extend_if_sniping()` checks if `ends_at - now < 2 minutes`
- If yes, sets `ends_at = now + 3 minutes` and saves
- The updated `ends_at` is picked up by the live timer sync (see feature #9)

---

## 9. Live Countdown Timer with Server Sync

**What it does:** All pages with auction timers show a live countdown that ticks every second. Every 10 seconds, the timer syncs with the server to pick up any extensions (e.g., from anti-sniping). This ensures both buyers and sellers always see the correct time remaining.

**Technologies used:**
- `data-ends-at` HTML attribute with ISO 8601 timestamp
- `data-listing-id` attribute for identifying which listing to poll
- JavaScript `setInterval()` for 1-second tick and 10-second server poll
- `/listings/<id>/timer/` JSON API endpoint
- `fetch()` API for AJAX polling

**How it works:**
- `countdown.js` runs two intervals: `tick()` every 1 second updates the display, `refreshTimers()` every 10 seconds fetches the latest `ends_at` from the server
- The `listing_timer` view returns JSON with `ends_at` and `is_active`
- If the server returns a different `ends_at`, the `data-ends-at` attribute is updated and the countdown adjusts automatically

---

## 10. Real-Time Listing Updates (AJAX)

**What it does:** The listing detail page refreshes the current price, bid count, and leading bidder every 5 seconds without a full page reload.

**Technologies used:**
- `live_listing.js` with `fetch()` API
- Django view returns JSON when `Accept: application/json` header is present
- DOM manipulation to update price, bidder name, and bid count elements

**How it works:**
- JavaScript fetches the listing detail URL with an `Accept: application/json` header
- The Django view detects this and returns JSON instead of HTML
- The script updates the relevant DOM elements with the new data

---

## 11. Auction Closing & Winner Determination

**What it does:** When an auction's end time passes, the system marks the listing as closed, identifies the highest bidder as the winner, and sends notifications and emails to both parties.

**Technologies used:**
- Django management command (`close_expired_auctions`) for scheduled execution
- `close_auction()` function in `timers/tasks.py`
- `Bid.highest_for(listing)` classmethod (ordered by `-amount`, `created_at` for tie-breaking)
- Auto-creation of `Conversation` between winner and seller

**How it works:**
- A cron job runs `python manage.py close_expired_auctions` periodically
- Finds all listings where `is_active=True` and `ends_at <= now`
- For each: sets `is_active=False`, marks highest bid as `is_winner=True`
- Deactivates all auto-bids on the listing
- Sends detailed emails to winner and seller
- Creates in-app notifications for winner, seller, and all losing bidders

---

## 12. Email Notifications (SMTP)

**What it does:** Sends real emails to the winner and seller when an auction closes. Emails include full product details, bid history (top 10 bids), and contact information for both parties.

**Technologies used:**
- Django's `send_mail()` function
- Gmail SMTP (`smtp.gmail.com:587` with TLS)
- `python-dotenv` for loading credentials from `.env` file
- Structured plain-text email templates built in Python

**How it works:**
- Email credentials are stored in `.env` (git-ignored) and loaded via `dotenv`
- `notify_winner()` sends the winner: product details, winning bid info, bid history, seller contact
- `notify_seller()` sends the seller: product details, sale summary, winner contact, bid history
- Helper functions `_product_block()`, `_bid_summary()`, and `_contact_block()` format the email sections
- `fail_silently=True` prevents email errors from crashing the auction close process

**Emails sent:**
| Event | Recipient | Content |
|-------|-----------|---------|
| Auction won | Winner | Product details, winning amount, bid history, seller contact |
| Auction sold | Seller | Product details, sale summary, winner contact, bid history |
| Password reset | User | Reset link with token |
| Contact form | Admin | Name, email, message |

---

## 13. In-App Notifications

**What it does:** Users receive real-time in-app notifications for key events (outbid, auction won/lost, new bid, new message, auto-bid events). A bell icon in the navbar shows the unread count.

**Technologies used:**
- `Notification` model with type, title, message, link, and read status
- Django context processor for injecting unread count into every page
- AJAX endpoint (`/notifications/unread-count/`) for dynamic badge updates
- 9 notification types with dedicated helper functions

**How it works:**
- Each notification type has a helper function (e.g., `notify_outbid()`) that creates a `Notification` record
- The context processor adds `unread_notification_count` to every template context
- The navbar bell shows a badge with the unread count
- Clicking a notification marks it as read and redirects to the relevant page

**Notification types:**
| Type | Trigger | Recipient |
|------|---------|-----------|
| outbid | Someone places a higher bid | Previous highest bidder |
| new_bid | New bid on a listing | Seller |
| auction_won | Auction closes | Winner |
| auction_lost | Auction closes | Losing bidders |
| auction_sold | Auction closes | Seller |
| auto_bid_placed | Auto-bid fires | Auto-bidder |
| auto_bid_exceeded | Auto-bid limit reached | Auto-bidder |
| new_message | New conversation message | Recipient |

---

## 14. Private Messaging (Conversations)

**What it does:** Bidders and sellers can exchange private messages within the context of a listing. A conversation is auto-created when a user first bids on a listing.

**Technologies used:**
- Two models: `Conversation` (thread) and `Message` (individual message)
- Unique constraint on (listing, bidder) to prevent duplicate conversations
- Participant check (`is_participant()`) for access control
- Chat-style UI with sent/received message styling

**How it works:**
- A `Conversation` links a `Listing` with a `bidder` (the seller is implicit via `listing.seller`)
- When a user places their first bid, a conversation is auto-created
- Messages are displayed chronologically with sender identification
- Only participants (bidder or seller) can view or send messages in a conversation

---

## 15. Reviews & Ratings

**What it does:** After an auction closes, the winner can review the seller and vice versa. Reviews include a 1-5 star rating and optional comment. Users have a public review profile showing their average rating.

**Technologies used:**
- `Review` model with rating (1-5), comment, reviewer, reviewee
- Unique constraint on (listing, reviewer) to prevent duplicate reviews
- Interactive star rating UI using JavaScript (hidden radio buttons + clickable star icons)
- Average rating calculation using Django ORM `Avg()`

**How it works:**
- `leave_review` view checks: auction is closed, winning bid exists, user is winner or seller
- If the user already reviewed this transaction, they are redirected with a message
- The star rating UI uses hidden radio inputs controlled by JavaScript click handlers
- `user_reviews` view aggregates all reviews for a user with average rating and count
- Stars are animated with hover effects and scale transforms

---

## 16. Watchlist

**What it does:** Users can add listings to their watchlist (like a "favorites" list) and view all watched listings on a dedicated page.

**Technologies used:**
- ManyToManyField (`watchers`) on the `Listing` model
- `@require_POST` toggle endpoint
- Django ORM `.add()` / `.remove()` for M2M relationship

**How it works:**
- Clicking the watch/unwatch button sends a POST request
- The view toggles the user's membership in the listing's `watchers` M2M relation
- The watchlist page filters listings where the user is in `watchers`

---

## 17. Seller Dashboard

**What it does:** Sellers can view all their listings in a table with status, current price, bid count, and winner information. Links to edit listings and view bid history.

**Technologies used:**
- Django ORM filtering (`Listing.objects.filter(seller=request.user)`)
- Annotated queries for bid counts and highest bid
- Bootstrap table with responsive design
- Action buttons for edit and bid history

**How it works:**
- `seller_dashboard_view` queries all listings where `seller=request.user`
- Annotates each listing with current price and bid count
- Displays in a table with columns: Title, Category, Start Price, Current Price, Bids, Status, Winner, Actions

---

## 18. Bid History & Management

**What it does:** Shows all bids on a listing in descending order with bidder names, amounts, auto/manual flags, and timestamps. Users can edit or delete their own non-winning bids.

**Technologies used:**
- Paginated queryset (20 per page) with `select_related('bidder')`
- Conditional display of edit/delete buttons based on bid ownership and listing status
- JavaScript confirm dialog for bid deletion
- Form-based DELETE with CSRF protection

**How it works:**
- `bid_history` view returns all bids for a listing, paginated
- Each bid shows: bidder avatar, username, amount, auto-bid badge, winner badge, timestamp
- Non-highest bids by the current user show edit/delete buttons (only on active listings)
- Edit loads a form pre-filled with the current amount
- Delete requires confirmation and uses a POST form

---

## 19. Daily Visit Tracking

**What it does:** Tracks how many times each user visits the site per day. Users can view their visit history (last 14 days) on the history page.

**Technologies used:**
- `DailyVisit` model with unique constraint on (user, date)
- Custom middleware (`TrackVisitMiddleware`)
- Session flag to prevent double-counting within a session
- Cookie (`last_visit_date`) for persistence across sessions

**How it works:**
- On each request, middleware checks if the user is authenticated
- Uses a session key to track if today's visit was already counted
- If not, creates or increments the `DailyVisit` record for today
- The history page queries the last 14 days of `DailyVisit` records

---

## 20. Password Reset via Email

**What it does:** Users can reset their password by entering their email. They receive a link with a secure token to set a new password.

**Technologies used:**
- Django's built-in `PasswordResetView`, `PasswordResetConfirmView`, etc.
- Email sending via configured SMTP backend
- Secure token generation using Django's token generator (uidb64 + token)

**How it works:**
- User enters email on the password reset form
- Django sends an email with a unique reset link containing a uidb64 and token
- Clicking the link validates the token and shows a new password form
- On submit, the password is updated and the user can log in

---

## 21. Contact Form

**What it does:** Public contact form on the home page that sends an email to the site administrator.

**Technologies used:**
- Django `Form` (`ContactForm`) with name, email, and message fields
- `send_mail()` to send to `CONTACT_EMAIL` setting
- Django messages framework for success feedback

---

## 22. Static Pages

**What it does:** Informational pages: Home (landing), About, Team, Privacy Policy, Terms of Service.

**Technologies used:**
- Simple Django function-based views rendering templates
- Team page uses a Python list of team member dictionaries
- All pages extend `base.html` for consistent layout

---

## 23. Responsive UI & Design System

**What it does:** The entire application uses a consistent, modern design with responsive layout, custom color palette, gradients, animations, and typography.

**Technologies used:**
- **Bootstrap 5.3.3** (CDN) for grid, components, and utilities
- **Bootstrap Icons** for iconography
- **Plus Jakarta Sans** (Google Fonts) for typography
- **CSS Custom Properties** (variables) for theming
- Custom CSS in `base.html` for gradients, shadows, animations

**Design system:**
| Token | Value | Usage |
|-------|-------|-------|
| `--primary` | `#6C5CE7` | Buttons, links, accents |
| `--accent` | `#FD79A8` | Highlights, badges |
| `--success` | `#00B894` | Active status, winning bids |
| `--warning` | `#F39C12` | Timer, auto-bid |
| `--danger` | `#E17055` | Errors, delete buttons |
| `--g-primary` | `linear-gradient(135deg, #6C5CE7, #a29bfe)` | Primary gradient |

---

## 24. Deployment Configuration

**What it does:** The project is configured for deployment on Render.com with WhiteNoise for static files and Gunicorn as the WSGI server.

**Technologies used:**
- **Gunicorn** as production WSGI server
- **WhiteNoise** for serving static files without a CDN
- **Render.com** deployment via `render.yaml`
- **python-dotenv** for environment variable management
- **SQLite** (development) with easy swap to PostgreSQL for production

**Configuration files:**
- `Procfile` - Gunicorn command
- `render.yaml` - Render service definition
- `requirements.txt` - Python dependencies
- `.env` / `.env.example` - Environment variables
