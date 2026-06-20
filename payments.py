"""
Payment integration — STUBBED.
================================
This module is shaped so that wiring in a *real* Razorpay integration later
is a small, contained change: only the two functions below need real
implementations, and nothing else in the app needs to change.

Currently, no real network calls are made and no real money moves. Calling
create_order() returns a fake order id, and verify_payment() always
succeeds. This lets the rest of the app (UI, registration flow, "Pay &
Register" button) be fully built and tested end-to-end before a real
payment gateway is connected.

--------------------------------------------------------------------------
TO GO LIVE WITH REAL RAZORPAY PAYMENTS LATER:
--------------------------------------------------------------------------
1. `pip install razorpay`
2. Set environment variables RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET
   (get these from the Razorpay dashboard — use test mode keys first).
3. Replace the body of create_order() with a real call, e.g.:

       import razorpay
       client = razorpay.Client(auth=(KEY_ID, KEY_SECRET))
       order = client.order.create({
           "amount": int(amount_rupees * 100),  # paise
           "currency": "INR",
           "payment_capture": 1,
       })
       return order["id"]

4. Replace verify_payment() with Razorpay's signature verification:

       client.utility.verify_payment_signature({
           "razorpay_order_id": order_id,
           "razorpay_payment_id": payment_id,
           "razorpay_signature": signature,
       })

5. On the frontend, you'd also need to load Razorpay's Checkout.js and open
   the real checkout modal — Streamlit can do this via a small custom HTML
   component (st.components.v1.html), since Razorpay's modal is JS-based.
--------------------------------------------------------------------------
"""

import secrets

# placeholder VPA — replace with a real merchant UPI ID when going live
STUB_UPI_ID = "eventhub@stub"


def generate_upi_qr(amount_rupees, order_id, payee_name="EventHub"):
    """STUB: build a scannable UPI QR code for the given amount/order.

    Encodes a standard 'upi://pay?...' deep link using a placeholder VPA
    (STUB_UPI_ID). Most UPI apps (GPay, PhonePe, Paytm, BHIM) can scan and
    parse this link format, but since the VPA isn't a real merchant
    account, completing a real payment against it will fail — this is for
    visual/UX testing only.

    Returns PNG image bytes, or None if the 'qrcode' package isn't
    installed.

    --------------------------------------------------------------------
    TO GO LIVE:
    --------------------------------------------------------------------
    Once you have a real Razorpay (or other PSP) integration, the QR code
    should instead encode the QR string / intent returned by that
    provider's Orders API (e.g. Razorpay's UPI QR Code API), not a raw
    upi://pay link built by hand. Swap the body of this function for that
    call once create_order() in this file is wired to the real API.
    --------------------------------------------------------------------
    """
    try:
        import qrcode
        import io
    except ImportError:
        return None

    upi_link = (
        f"upi://pay?pa={STUB_UPI_ID}&pn={payee_name}"
        f"&am={amount_rupees:.2f}&cu=INR&tn={order_id}"
    )
    img = qrcode.make(upi_link)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def create_order(amount_rupees, event_title=""):
    """STUB: pretend to create a Razorpay order. Returns a fake order id.

    Real implementation would call Razorpay's Orders API and return a
    genuine order_id to hand to Razorpay's Checkout.js on the frontend.
    """
    return "order_stub_" + secrets.token_hex(6)


def verify_payment(order_id, payment_id=None, signature=None):
    """STUB: pretend to verify a Razorpay payment. Always succeeds.

    Real implementation would verify the HMAC signature Razorpay sends back
    against your key secret, and would reject anything that doesn't match.
    """
    fake_payment_ref = payment_id or ("pay_stub_" + secrets.token_hex(6))
    return True, fake_payment_ref
