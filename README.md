# OnlineAuctionSystem

A Django app for running timed auctions: sellers list items, bidders bid,
and the highest bid automatically wins once the listing's countdown ends.

## Setup

```bash
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

Visit `http://localhost:8000/`.

## Running the test suite

```bash
python manage.py test
```

## Seeing a working demo

```bash
python manage.py seed_demo
```

This creates demo accounts (password `demopass123` for all of them):

- `admin` - staff account, see `/admin/`
- `seller1` - lists three items across categories
- `alice` / `bob` - have placed bids on those listings

One listing (`Antique Wall Clock`) is seeded already ended with a winner
picked, so you can see the auto-close/notify-winner flow without waiting.
To watch that flow happen live instead, shorten a listing's `ends_at` and run:

```bash
python manage.py close_expired_auctions
```

This closes any listing whose countdown has passed, marks the highest bid
(tie-broken by earliest bid) as the winner, and emails them - printed to the
console with the default `EMAIL_BACKEND`.

## Deployment

The app reads its production settings from environment variables (see
`.env.example`):

- `DJANGO_SECRET_KEY` - required in production, falls back to an insecure
  dev key otherwise.
- `DJANGO_DEBUG` - set to `False` in production.
- `DJANGO_ALLOWED_HOSTS` - comma-separated list of allowed hostnames.

Static files are served via WhiteNoise (already wired into `MIDDLEWARE`); run
`python manage.py collectstatic` before deploying. The included `Procfile`
runs migrations on release and serves the app with `gunicorn`:

```
release: python manage.py migrate --noinput
web: gunicorn auction_project.wsgi --log-file -
```

`close_expired_auctions` isn't wired into a scheduler - run it on a
recurring job (cron, Heroku Scheduler, etc.) to actually close auctions
automatically in production.
