# EventHub — Event Management System

A full-stack event management app built with **Python (Streamlit)** for the
app logic and UI, **SQLite** for storage, and a small custom **CSS** layer
for styling. No separate frontend/backend split is needed — Streamlit
renders the HTML/CSS/JS in the browser for you.

## Features

**Admin**
- Log in with an administrator account
- Create events (title, description, date, time, location, capacity,
  **category**, **price**)
- Edit or delete existing events
- View who has registered for each event, including payment status
- View ratings & reviews left for each event

**User**
- Create an account and log in
- Browse events, **filter by category** (Workshops, Tech Events, Sports,
  Cultural)
- See a live **countdown timer** on each event ("🟢 in 3 days", "🟠 Starting
  very soon!", "🔴 Event has ended")
- See **live seat availability** as a progress bar ("Seats: 8/20 filled")
- Register for free events instantly, or **pay & register** for priced
  events (currently a stubbed/test-mode checkout — see "Payments" below)
- Cancel a registration
- **Rate and review** events after they've happened (1–5 stars + comment)
- See **"You may like"** recommendations based on the categories of events
  they've previously registered for
- Browse events in a **calendar view** (month grid, navigate month by month)
- Ask the **AI chat support bot** questions about how the platform works

## Project structure

```
eventhub/
├── app.py              # Streamlit UI: login/register, admin & user dashboards
├── database.py         # SQLite schema + all data access functions
├── auth.py             # Password hashing/verification helpers
├── payments.py         # Stubbed payment integration (UPI QR + shaped for real Razorpay later)
├── chatbot.py          # AI chat support bot (real Anthropic/Claude API)
├── utils.py            # Countdown timer + calendar grid helpers
├── style.css           # Custom styling injected into the Streamlit app
├── requirements.txt
├── migrate_db.py        # One-off script to patch an older database with new columns
└── event_management.db # Created automatically on first run
```

## Setup

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
2. (Optional, for the AI chat bot) Get a free API key from
   [console.groq.com/keys](https://console.groq.com/keys) and set it as an
   environment variable:
   ```bash
   export GROQ_API_KEY="gsk_..."      # macOS/Linux
   $env:GROQ_API_KEY="gsk_..."        # Windows PowerShell
   ```
   Without this set, the Support tab still works — it just shows a clear
   "not connected yet" message instead of crashing.
3. Run the app:
   ```bash
   streamlit run app.py
   ```
4. Open the URL Streamlit prints (usually `http://localhost:8501`).

A SQLite file called `event_management.db` is created automatically the
first time you run the app — no separate database setup required.

### Upgrading an existing database

If you already have an `event_management.db` from an older version of this
app (one without categories/pricing/payments), run the included migration
script once before starting the app:

```bash
python migrate_db.py
```

It only adds the missing columns/tables — your existing events, users, and
registrations are untouched. Safe to run more than once. (`app.py` also
tries to do this automatically on every startup via `database.init_db()`,
but if you ever hit a `KeyError`/`column not found` error, running this
script directly will fix it.)

## Logging in

A default admin account is seeded automatically the first time the app
runs:

- **Username:** `admin`
- **Password:** `admin123`

Change or remove this before using the app for anything beyond local
testing. New accounts created through the "Create Account" tab are always
regular users; there's no self-service way to become an admin (by design).

## Payments — currently stubbed

The "Pay & Register" flow for priced events is fully built end-to-end on
the UI and database side, but `payments.py` is a **stub**: it generates a
fake order id and always reports a successful payment. No real money moves
and no real payment gateway is contacted.

The checkout screen shows a **scannable UPI QR code** (built with the
`qrcode` package) encoding a standard `upi://pay?...` deep link with a
placeholder VPA (`eventhub@stub`). Real UPI apps can scan and read it, but
since it's not a real merchant account, completing payment against it will
fail — it's there for layout/UX testing, not real transactions.

`payments.py` includes step-by-step instructions for swapping in a real
Razorpay integration later — at a high level:

1. `pip install razorpay`
2. Get test-mode API keys from the Razorpay dashboard
3. Replace the two stub functions (`create_order`, `verify_payment`) with
   real Razorpay API calls
4. Replace `generate_upi_qr()`'s hand-built UPI link with the actual QR
   string/intent Razorpay's UPI QR Code API returns
5. Add Razorpay's Checkout.js on the frontend via
   `st.components.v1.html` if you want the full hosted checkout instead
   of just the QR code

Nothing else in the app needs to change — the rest of the registration
flow already calls these functions and reacts to their result.

## The AI chat bot

`chatbot.py` calls the [Groq](https://console.groq.com) API (model:
`openai/gpt-oss-20b`, Groq's current recommended lightweight general-purpose
model) using the `groq` Python SDK. Groq offers a generous free developer
tier, so this works without needing to set up billing.

It reads your API key from the `GROQ_API_KEY` environment variable — the
key is **never** hardcoded anywhere in this codebase. If the variable isn't
set, or the `groq` package isn't installed, the Support tab shows a clear
setup message instead of crashing.

To get a key: sign up at [console.groq.com](https://console.groq.com), go
to **API Keys**, and create one. Then set it as shown in the Setup section
above, and restart Streamlit from the same terminal so it inherits the
variable (a browser refresh alone won't pick up a new environment
variable).

## Notes on the implementation

- Passwords are stored as salted SHA-256 hashes (see `auth.py`). This is
  reasonable for a learning project, but for a production app you'd want a
  dedicated library such as `bcrypt` or `passlib` instead.
- Event capacity of `0` means unlimited; any other number caps registrations
  and the Register/Pay button automatically becomes disabled once an event
  is full.
- Deleting an event also removes any registrations and reviews tied to it
  (`ON DELETE CASCADE` in the schema).
- The recommendation engine is intentionally simple and explainable: it
  looks at the categories of events a user has already registered for and
  suggests other upcoming events in those same categories. New users with
  no registration history see the soonest upcoming events instead, so the
  section never looks broken/empty.
- A review can only be left for an event the user registered for **and**
  whose date has already passed (`has_attended` in `database.py`).
- All UI state (who's logged in, which role, calendar month, chat history,
  pending payment) lives in `st.session_state`, which is how Streamlit apps
  typically handle "pages" and short-term state without a separate router.

## Ideas for extending it further

- Wire up the real Razorpay integration (see "Payments" above).
- Add email/password reset flows.
- Let admins promote a user to admin instead of hardcoding one seed account.
- Add free-text search across events, in addition to category filtering.
- Export registrations to CSV from the admin "Registrations" tab.
- Swap SQLite for Postgres/MySQL if you need multi-instance deployment.
- Replace the rule-based recommendation engine with a real ML/embedding-based
  one once you have enough registration data to make that worthwhile.
