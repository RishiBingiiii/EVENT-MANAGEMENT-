"""
Event Management System — EventHub
====================================
A Streamlit app with two roles:

- Admin: create / edit / delete events, view who's registered for each one.
- User:  create an account, browse events, register / cancel, rate events
         attended, see recommendations, and use the calendar view + chat bot.

Run with:  streamlit run app.py
"""

import calendar as calendar_module
from datetime import date, datetime

import pandas as pd
import streamlit as st

import chatbot
import database as db
import payments
import utils

st.set_page_config(page_title="EventHub", page_icon="🎫", layout="wide")


def load_css():
    try:
        with open("style.css") as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
    except FileNotFoundError:
        pass


db.init_db()
load_css()

if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if "user" not in st.session_state:
    st.session_state.user = None
if "calendar_year" not in st.session_state:
    st.session_state.calendar_year = date.today().year
if "calendar_month" not in st.session_state:
    st.session_state.calendar_month = date.today().month
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "pending_payment_event" not in st.session_state:
    st.session_state.pending_payment_event = None


def logout():
    st.session_state.authenticated = False
    st.session_state.user = None


CATEGORY_ICONS = {
    "Workshops": "🛠️",
    "Tech Events": "💻",
    "Sports": "🏆",
    "Cultural": "🎭",
}

CATEGORY_CSS_CLASS = {
    "Workshops": "cat-workshops",
    "Tech Events": "cat-tech",
    "Sports": "cat-sports",
    "Cultural": "cat-cultural",
}


def category_chip(category):
    """Return an HTML span styled as a colored pill for this category."""
    css_class = CATEGORY_CSS_CLASS.get(category, "cat-tech")
    return f"<span class='cat-chip {css_class}'>{category}</span>"


# --------------------------------------------------------------- Login/Register

def login_register_view():
    st.markdown(
        "<div class='hero'><h1>🎫 EventHub</h1>"
        "<p>Discover events, register in a click, and manage everything from one place.</p>"
        "</div>",
        unsafe_allow_html=True,
    )

    tab_login, tab_register = st.tabs(["Log In", "Create Account"])

    with tab_login:
        with st.form("login_form"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button(
                "Log In", use_container_width=True)
        if submitted:
            user = db.authenticate_user(username, password)
            if user:
                st.session_state.authenticated = True
                st.session_state.user = user
                st.rerun()
            else:
                st.error("Incorrect username or password.")
        st.caption(
            "Default admin account for testing: **admin / admin123** "
            "— change this before using the app for anything real."
        )

    with tab_register:
        st.caption(
            "New accounts are created as regular users. The admin account is fixed above.")
        with st.form("register_form"):
            full_name = st.text_input("Full name")
            email = st.text_input("Email")
            new_username = st.text_input("Choose a username")
            new_password = st.text_input("Choose a password", type="password")
            confirm_password = st.text_input(
                "Confirm password", type="password")
            submitted = st.form_submit_button(
                "Create Account", use_container_width=True)
        if submitted:
            if not new_username or not new_password:
                st.error("Username and password are required.")
            elif new_password != confirm_password:
                st.error("Passwords don't match.")
            else:
                ok, message = db.create_user(
                    new_username, new_password, full_name, email, role="user"
                )
                if ok:
                    st.success(
                        message + " You can now log in from the other tab.")
                else:
                    st.error(message)


# --------------------------------------------------------------- Admin dashboard

def admin_dashboard(user):
    with st.sidebar:
        st.markdown(f"### 👋 {user['full_name'] or user['username']}")
        st.caption("Administrator")
        if st.button("Log Out", use_container_width=True):
            logout()
            st.rerun()

    st.title("Admin Dashboard")
    tab_create, tab_manage, tab_regs, tab_reviews = st.tabs(
        ["➕ Create Event", "🛠️ Manage Events", "📋 Registrations", "⭐ Reviews"]
    )

    with tab_create:
        st.subheader("Create a new event")
        with st.form("create_event_form", clear_on_submit=True):
            title = st.text_input("Title")
            description = st.text_area("Description")
            col1, col2 = st.columns(2)
            with col1:
                event_date = st.date_input("Date", min_value=date.today())
            with col2:
                event_time = st.time_input("Time")
            location = st.text_input("Location")
            col3, col4, col5 = st.columns(3)
            with col3:
                capacity = st.number_input(
                    "Capacity (0 = unlimited)", min_value=0, step=1, value=0)
            with col4:
                category = st.selectbox("Category", db.CATEGORIES)
            with col5:
                price = st.number_input(
                    "Price ₹ (0 = free)", min_value=0.0, step=50.0, value=0.0)
            submitted = st.form_submit_button(
                "Create Event", use_container_width=True)
        if submitted:
            if not title:
                st.error("Title is required.")
            else:
                db.create_event(
                    title,
                    description,
                    str(event_date),
                    event_time.strftime("%H:%M"),
                    location,
                    capacity,
                    user["id"],
                    category=category,
                    price_rupees=price,
                )
                st.success(f"Event '{title}' created.")

    with tab_manage:
        st.subheader("Existing events")
        events = db.get_all_events()
        if not events:
            st.info("No events yet — create one in the previous tab.")
        for ev in events:
            with st.expander(f"{ev['title']} — {ev['event_date']} {ev['event_time'] or ''}"):
                with st.form(f"edit_form_{ev['id']}"):
                    e_title = st.text_input(
                        "Title", value=ev["title"], key=f"title_{ev['id']}")
                    e_desc = st.text_area(
                        "Description", value=ev["description"] or "", key=f"desc_{ev['id']}"
                    )
                    col1, col2 = st.columns(2)
                    with col1:
                        e_date = st.text_input(
                            "Date (YYYY-MM-DD)", value=ev["event_date"], key=f"date_{ev['id']}"
                        )
                    with col2:
                        e_time = st.text_input(
                            "Time (HH:MM)", value=ev["event_time"] or "", key=f"time_{ev['id']}"
                        )
                    e_loc = st.text_input(
                        "Location", value=ev["location"] or "", key=f"loc_{ev['id']}"
                    )
                    col3, col4, col5 = st.columns(3)
                    with col3:
                        e_cap = st.number_input(
                            "Capacity (0 = unlimited)",
                            min_value=0,
                            step=1,
                            value=ev["capacity"] or 0,
                            key=f"cap_{ev['id']}",
                        )
                    with col4:
                        e_cat = st.selectbox(
                            "Category",
                            db.CATEGORIES,
                            index=db.CATEGORIES.index(ev["category"])
                            if ev["category"] in db.CATEGORIES else 0,
                            key=f"cat_{ev['id']}",
                        )
                    with col5:
                        e_price = st.number_input(
                            "Price ₹ (0 = free)",
                            min_value=0.0,
                            step=50.0,
                            value=float(ev["price_rupees"] or 0),
                            key=f"price_{ev['id']}",
                        )
                    col_save, col_delete = st.columns(2)
                    save = col_save.form_submit_button(
                        "💾 Save changes", use_container_width=True)
                    delete = col_delete.form_submit_button(
                        "🗑️ Delete event", use_container_width=True
                    )
                if save:
                    db.update_event(
                        ev["id"], e_title, e_desc, e_date, e_time, e_loc, e_cap,
                        category=e_cat, price_rupees=e_price,
                    )
                    st.success("Updated.")
                    st.rerun()
                if delete:
                    db.delete_event(ev["id"])
                    st.warning(f"Deleted '{ev['title']}'.")
                    st.rerun()

    with tab_regs:
        st.subheader("View registrations")
        events = db.get_all_events()
        if not events:
            st.info("No events yet.")
        else:
            options = {f"{e['title']} ({e['event_date']})": e["id"]
                       for e in events}
            choice = st.selectbox("Select an event", list(options.keys()))
            event_id = options[choice]
            regs = db.get_event_registrations(event_id)
            capacity = db.get_event(event_id)["capacity"]
            st.metric("Registered", f"{len(regs)}" +
                      (f" / {capacity}" if capacity else ""))
            if regs:
                st.dataframe(pd.DataFrame(regs),
                             use_container_width=True, hide_index=True)
            else:
                st.info("No one has registered for this event yet.")

    with tab_reviews:
        st.subheader("Ratings & reviews per event")
        events = db.get_all_events()
        if not events:
            st.info("No events yet.")
        else:
            options = {f"{e['title']} ({e['event_date']})": e["id"]
                       for e in events}
            choice = st.selectbox("Select an event", list(
                options.keys()), key="review_event_select")
            event_id = options[choice]
            avg_rating, count = db.get_event_rating_summary(event_id)
            if count:
                st.metric(
                    "Average rating", f"{avg_rating} ⭐ ({count} review{'s' if count != 1 else ''})")
            else:
                st.info("No reviews yet for this event.")
            reviews = db.get_event_reviews(event_id)
            for rv in reviews:
                st.markdown(
                    f"**{rv['full_name'] or rv['username']}** — {'⭐' * rv['rating']}"
                )
                if rv["comment"]:
                    st.caption(rv["comment"])
                st.divider()


# --------------------------------------------------------------- User dashboard

def render_event_card(ev, user, count, full, already):
    """Shared event-card renderer used in the browse tab."""
    avg_rating, review_count = db.get_event_rating_summary(ev["id"])
    countdown = utils.countdown_text(ev["event_date"], ev["event_time"])
    price_label = utils.format_price(ev["price_rupees"])

    with st.container(border=True):
        cols = st.columns([3, 1])
        with cols[0]:
            icon = CATEGORY_ICONS.get(ev["category"], "🎫")
            st.markdown(f"#### {icon} {ev['title']}")
            chip_html = category_chip(ev["category"])
            countdown_html = f"&nbsp;&nbsp;{countdown}" if countdown else ""
            st.markdown(f"{chip_html}{countdown_html}", unsafe_allow_html=True)
            st.write(ev["description"] or "")
            st.caption(
                f"📅 {ev['event_date']}  🕒 {ev['event_time'] or 'TBA'}  "
                f"📍 {ev['location'] or 'TBA'}"
            )
            st.caption(f"💰 {price_label}")
            if ev["capacity"]:
                st.progress(
                    min(count / ev["capacity"], 1.0),
                    text=f"Seats: {count}/{ev['capacity']} filled",
                )
            else:
                st.caption(f"Spots taken: {count} (unlimited capacity)")
            if review_count:
                st.caption(
                    f"⭐ {avg_rating} average ({review_count} review{'s' if review_count != 1 else ''})")
            else:
                st.caption("⭐ No reviews yet")

        with cols[1]:
            if already:
                paid_ok = already["payment_status"] in ("paid", "not_required")
                if paid_ok:
                    st.success("Registered")
                else:
                    st.warning("Payment pending")
                if st.button("Cancel", key=f"cancel_{ev['id']}", use_container_width=True):
                    db.cancel_registration(user["id"], ev["id"])
                    st.rerun()
            elif full:
                st.button("Full", disabled=True,
                          use_container_width=True, key=f"full_{ev['id']}")
            else:
                if ev["price_rupees"] and ev["price_rupees"] > 0:
                    if st.button(
                        f"Pay & Register ({price_label})",
                        key=f"pay_{ev['id']}",
                        use_container_width=True,
                    ):
                        st.session_state.pending_payment_event = ev["id"]
                        st.rerun()
                else:
                    if st.button("Register", key=f"reg_{ev['id']}", use_container_width=True):
                        ok, message = db.register_for_event(
                            user["id"], ev["id"])
                        (st.success if ok else st.error)(message)
                        st.rerun()


def payment_modal(user):
    """Simple inline 'checkout' for the event currently pending payment."""
    event_id = st.session_state.pending_payment_event
    ev = db.get_event(event_id)
    if not ev:
        st.session_state.pending_payment_event = None
        return

    st.warning(
        "🧪 **Test mode** — this is a stubbed checkout with a placeholder "
        "UPI QR code. No real payment gateway is connected yet and no "
        "money will be charged, even if you scan it with a real UPI app."
    )
    st.markdown(
        f"**{ev['title']}** — {utils.format_price(ev['price_rupees'])}")

    order_id = payments.create_order(ev["price_rupees"], ev["title"])
    st.caption(f"Order reference: `{order_id}`")

    qr_bytes = payments.generate_upi_qr(ev["price_rupees"], order_id)
    if qr_bytes:
        qr_col, info_col = st.columns([1, 2])
        with qr_col:
            st.image(qr_bytes, caption="Scan to pay (test mode)", width=220)
        with info_col:
            st.caption(
                f"Payee VPA: `{payments.STUB_UPI_ID}` (placeholder, not a real account)")
            st.caption(
                "Scanning this with a real UPI app will show the payment "
                "request, but it won't go through since this isn't a "
                "live merchant account yet."
            )
    else:
        st.caption(
            "Install the `qrcode` package (`pip install qrcode[pil]`) to "
            "show a scannable QR code here."
        )

    col1, col2 = st.columns(2)
    with col1:
        if st.button("✅ Simulate successful payment", use_container_width=True):
            success, payment_ref = payments.verify_payment(order_id)
            if success:
                ok, message = db.register_for_event(
                    user["id"], event_id, payment_status="paid", payment_ref=payment_ref
                )
                (st.success if ok else st.error)(message)
            else:
                st.error("Payment verification failed.")
            st.session_state.pending_payment_event = None
            st.rerun()
    with col2:
        if st.button("Cancel", use_container_width=True):
            st.session_state.pending_payment_event = None
            st.rerun()


def calendar_view(events):
    st.subheader("📅 Calendar view")
    col_prev, col_label, col_next = st.columns([1, 3, 1])
    with col_prev:
        if st.button("◀ Prev"):
            m = st.session_state.calendar_month - 1
            y = st.session_state.calendar_year
            if m < 1:
                m, y = 12, y - 1
            st.session_state.calendar_month, st.session_state.calendar_year = m, y
            st.rerun()
    with col_next:
        if st.button("Next ▶"):
            m = st.session_state.calendar_month + 1
            y = st.session_state.calendar_year
            if m > 12:
                m, y = 1, y + 1
            st.session_state.calendar_month, st.session_state.calendar_year = m, y
            st.rerun()
    with col_label:
        month_name = calendar_module.month_name[st.session_state.calendar_month]
        st.markdown(
            f"<h4 style='text-align:center'>{month_name} {st.session_state.calendar_year}</h4>",
            unsafe_allow_html=True,
        )

    grid = utils.build_month_grid(
        st.session_state.calendar_year, st.session_state.calendar_month)
    grouped = utils.events_by_date(events)

    header_cols = st.columns(7)
    for col, day_name in zip(header_cols, ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]):
        col.markdown(f"**{day_name}**")

    for week in grid:
        row_cols = st.columns(7)
        for col, day in zip(row_cols, week):
            if day is None:
                col.write("")
                continue
            day_events = grouped.get(str(day), [])
            with col.container(border=bool(day_events)):
                is_today = day == date.today()
                label = f"**{day.day}**" if is_today else str(day.day)
                col.markdown(label)
                for ev in day_events[:3]:
                    icon = CATEGORY_ICONS.get(ev["category"], "🎫")
                    col.caption(f"{icon} {ev['title'][:14]}")
                if len(day_events) > 3:
                    col.caption(f"+{len(day_events) - 3} more")


def chat_support_tab():
    st.subheader("💬 Chat Support")
    if not chatbot.is_configured():
        st.info(
            "The chat bot isn't connected yet. Set the `ANTHROPIC_API_KEY` "
            "environment variable with your Anthropic API key and restart "
            "the app to enable it."
        )

    for msg in st.session_state.chat_history:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    user_msg = st.chat_input(
        "Ask about registration, payments, cancellations…")
    if user_msg:
        st.session_state.chat_history.append(
            {"role": "user", "content": user_msg})
        with st.chat_message("user"):
            st.markdown(user_msg)
        with st.chat_message("assistant"):
            with st.spinner("Thinking…"):
                reply = chatbot.get_bot_reply(st.session_state.chat_history)
            st.markdown(reply)
        st.session_state.chat_history.append(
            {"role": "assistant", "content": reply})


def user_dashboard(user):
    with st.sidebar:
        st.markdown(f"### 👋 {user['full_name'] or user['username']}")
        st.caption("Attendee")
        if st.button("Log Out", use_container_width=True):
            logout()
            st.rerun()

    st.title("EventHub")

    if st.session_state.pending_payment_event:
        payment_modal(user)
        st.divider()

    tab_browse, tab_mine, tab_calendar, tab_chat = st.tabs(
        ["🔎 Browse Events", "🎟️ My Registrations", "📅 Calendar", "💬 Support"]
    )

    with tab_browse:
        category_filter = st.selectbox(
            "Filter by category", ["All"] + db.CATEGORIES)
        events = db.get_all_events(category=category_filter)
        if not events:
            st.info("No events match this filter — check back soon!")
        for ev in events:
            count = db.get_registration_count(ev["id"])
            full = ev["capacity"] and count >= ev["capacity"]
            already = db.get_user_registration(user["id"], ev["id"])
            render_event_card(ev, user, count, full, already)

        recommendations = db.get_recommended_events(user["id"])
        if recommendations:
            st.divider()
            st.subheader("✨ You may like")
            rec_cols = st.columns(min(len(recommendations), 4))
            for col, ev in zip(rec_cols, recommendations):
                with col:
                    icon = CATEGORY_ICONS.get(ev["category"], "🎫")
                    st.markdown(f"**{icon} {ev['title']}**")
                    st.markdown(category_chip(
                        ev["category"]), unsafe_allow_html=True)
                    st.caption(ev["event_date"])
                    countdown = utils.countdown_text(
                        ev["event_date"], ev["event_time"])
                    if countdown:
                        st.caption(countdown)

    with tab_mine:
        my_events = db.get_user_registrations(user["id"])
        if not my_events:
            st.info("You haven't registered for any events yet.")
        else:
            st.dataframe(
                pd.DataFrame(my_events)[
                    ["title", "event_date", "event_time",
                        "location", "payment_status"]
                ],
                use_container_width=True,
                hide_index=True,
            )

            st.divider()
            st.subheader("⭐ Rate an event you've attended")
            past_events = [
                ev for ev in my_events if ev["event_date"] <= str(date.today())
            ]
            if not past_events:
                st.caption("You can rate events after their date has passed.")
            else:
                options = {f"{e['title']} ({e['event_date']})": e["id"]
                           for e in past_events}
                choice = st.selectbox(
                    "Select an event to review", list(options.keys()))
                rev_event_id = options[choice]
                existing = db.get_user_review(user["id"], rev_event_id)
                with st.form("review_form"):
                    rating = st.slider(
                        "Rating", 1, 5, value=existing["rating"] if existing else 5
                    )
                    comment = st.text_area(
                        "Comment (optional)", value=existing["comment"] if existing else ""
                    )
                    submitted = st.form_submit_button(
                        "Submit review", use_container_width=True
                    )
                if submitted:
                    db.add_or_update_review(
                        user["id"], rev_event_id, rating, comment)
                    st.success("Thanks for your review!")
                    st.rerun()

    with tab_calendar:
        calendar_view(db.get_all_events())

    with tab_chat:
        chat_support_tab()


# --------------------------------------------------------------- Router

if not st.session_state.authenticated:
    login_register_view()
elif st.session_state.user["role"] == "admin":
    admin_dashboard(st.session_state.user)
else:
    user_dashboard(st.session_state.user)
