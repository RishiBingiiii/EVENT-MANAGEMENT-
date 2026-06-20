"""
AI-powered chat support bot for EventHub — now using Groq.

Groq runs open-weight models (Llama, GPT-OSS, Qwen, etc.) on custom
inference hardware, and offers a generous free developer tier — a good fit
if you don't want to set up Anthropic API billing just for this chat bot.

SETUP:
    1. Get a free API key at https://console.groq.com/keys
    2. Set the GROQ_API_KEY environment variable before running the app:

        PowerShell:
            $env:GROQ_API_KEY="gsk_..."
        macOS/Linux:
            export GROQ_API_KEY="gsk_..."

    3. pip install groq
    4. Restart Streamlit from the same terminal so it inherits the variable.

Without a key set, the chat tab shows a clear setup message instead of
crashing. The key is never hardcoded here or anywhere else in this app —
it's read fresh from the environment on every call.
"""

import os

SYSTEM_PROMPT = """You are the support assistant for EventHub, an event \
registration platform. You help users with questions about:
- How to browse and register for events (categories: Workshops, Tech Events, Sports, Cultural)
- How seat availability and capacity limits work
- How the (currently test-mode/stubbed) payment flow works for paid events, including the UPI QR code
- How to cancel a registration
- How to leave a rating/review after attending an event
- How the "You may like" recommendations work (based on past registration categories)
- General navigation of the app

Keep answers short (2-4 sentences), friendly, and specific to EventHub. If \
asked about something unrelated to the platform, politely redirect back to \
what you can help with. If asked about real payments, mention that payments \
are currently in test/stub mode and no real money is charged yet."""

# openai/gpt-oss-20b is Groq's current recommended lightweight general-purpose
# model (as of mid-2026), replacing the deprecated llama-3.1-8b-instant.
MODEL = "openai/gpt-oss-20b"


def is_configured():
    return bool(os.environ.get("GROQ_API_KEY"))


def get_bot_reply(conversation_history):
    """conversation_history: list of {'role': 'user'|'assistant', 'content': str}

    Returns the assistant's reply text, or a clear setup/error message if
    the API key is missing or the call fails.
    """
    if not is_configured():
        return (
            "⚠️ The chat bot isn't connected yet. To enable it, get a free "
            "API key at console.groq.com/keys, set the `GROQ_API_KEY` "
            "environment variable, and restart the app."
        )

    try:
        from groq import Groq
    except ImportError:
        return (
            "⚠️ The `groq` package isn't installed. Run `pip install groq` "
            "and restart the app."
        )

    try:
        client = Groq()  # reads GROQ_API_KEY from env
        messages = [{"role": "system", "content": SYSTEM_PROMPT}
                    ] + conversation_history
        response = client.chat.completions.create(
            model=MODEL,
            max_tokens=400,
            messages=messages,
        )
        text = (response.choices[0].message.content or "").strip()
        return text or "Sorry, I didn't get a response — please try again."
    except Exception as exc:  # noqa: BLE001 — surface any API error to the user
        return f"⚠️ Couldn't reach the chat assistant right now ({exc})."
