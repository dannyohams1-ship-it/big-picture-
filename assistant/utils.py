import logging
import re
from collections import Counter
from datetime import timedelta
from difflib import SequenceMatcher
from functools import lru_cache
from typing import Dict, List, Optional
from django.urls import reverse
from django.utils.html import escape
from django.conf import settings
from django.core.cache import cache
from django.db.models import Q
from django.utils import timezone
from assistant.models import Lead
from assistant.utils_notify import notify_team_of_lead

from django.utils.html import strip_tags
from .models import Lead

from shop.models import Order, Product
from shop.templatetags.currency_tags import as_currency

from bs4 import BeautifulSoup

from .models import ChatSession, ChatMessage, Lead, UnansweredQuery
from .faqs_data import FAQS
from .parsers import fetch_faq_from_page

logger = logging.getLogger(__name__)

# ==========================================================
# Configuration
# ==========================================================
FAQ_PAGE_URL = getattr(settings, "FAQ_PAGE_URL", "https://drizzy.pythonanywhere.com/faqs/")
FUZZY_THRESHOLD = float(getattr(settings, "FAQ_MATCH_THRESHOLD", 0.6))
FAQ_CACHE_TTL = int(getattr(settings, "FAQ_CACHE_TTL", 3600))  # seconds

# ==========================================================
# spaCy (lazy load)
# ==========================================================
_nlp = None


def _get_spacy():
    global _nlp
    if _nlp is None:
        try:
            import spacy  # local import to avoid startup overhead
            _nlp = spacy.load("en_core_web_sm")
        except Exception as e:
            logger.exception("Failed to load spaCy model: %s", e)
            _nlp = None
    return _nlp


# ==========================================================
# NLP helpers
# ==========================================================
def extract_keywords_and_entities(text: str) -> Dict[str, List[str]]:
    """
    Return { "keywords": [...], "entities": [...] }.
    Lightweight fallback if spaCy unavailable.
    """
    if not text or not isinstance(text, str):
        return {"keywords": [], "entities": []}

    nlp = _get_spacy()
    if not nlp:
        # Fallback: crude tokenization
        words = [w.lower() for w in re.findall(r"\w+", text) if len(w) > 2]
        keywords = list(dict.fromkeys(words))[:5]
        return {"keywords": keywords, "entities": []}

    doc = nlp(text.lower())
    entities = [ent.text for ent in doc.ents]
    keywords = [
        token.lemma_
        for token in doc
        if token.pos_ in ("NOUN", "PROPN", "VERB") and not token.is_stop and token.is_alpha
    ]
    top_keywords = [w for w, _ in Counter(keywords).most_common(5)]
    return {"keywords": top_keywords, "entities": entities}


# ---------------------------------------------------------------------
#  Core Message Handling
# ---------------------------------------------------------------------

def process_user_message(session: ChatSession, message_text: str, memory: dict | None = None) -> dict:
    """
    Handles incoming user messages using session memory.
    If chatbot cannot answer confidently, it marks message as 'requires_human=True'.
    Returns dict: {"reply": str, "requires_human": bool}
    """

    if not message_text or not isinstance(message_text, str):
        return {"reply": _save_bot_reply(session, "I didn’t quite catch that — could you rephrase? 💬")}

    user_input = message_text.strip().lower()
    memory = memory or {}

    last_intent = memory.get("last_intent")
    last_message = memory.get("last_user_message")
    last_reply = memory.get("last_bot_reply")
    topic = memory.get("topic", "general")
    history = memory.get("recent_history", [])

    # --- Context-aware continuity ---
    if last_intent == "product_search" and any(k in user_input for k in ["yes", "more", "show", "those", "similar"]):
        reply = "Looking for more similar items? 👗 I can show related products!"
        return {"reply": _save_bot_reply(session, reply)}

    if last_intent == "order_tracking" and any(k in user_input for k in ["yes", "still", "update", "where", "arrived"]):
        reply = "No worries 😊 could you share your order number again so I can recheck?"
        return {"reply": _save_bot_reply(session, reply)}

    # --- Topic continuity ---
    if topic == "shipping" and "how long" in user_input:
        reply = "Our shipping usually takes 2–5 working days, depending on location 🚚"
        return {"reply": _save_bot_reply(session, reply)}

    if topic == "returns" and "how" in user_input:
        reply = "To return an item, just head to your orders page and click 'Request Return' 🔄"
        return {"reply": _save_bot_reply(session, reply)}

    # --- Reset context if user changes topic ---
    if last_intent and last_intent not in user_input and len(user_input.split()) > 3:
        memory["context_reset"] = True
        session.update_memory("context_reset", True)

    # --- Dynamic FAQ ---
    faq_answer = get_best_faq_answer(user_input)
    if faq_answer:
        reply = _save_bot_reply(session, faq_answer)
        return {"reply": reply, "requires_human": False}

    # --- Small Talk ---
    small_talk_reply = handle_small_talk(user_input)
    if small_talk_reply:
        reply = _save_bot_reply(session, small_talk_reply)
        return {"reply": reply, "requires_human": False}

    # --- Fallback: AI unsure, mark for human handoff ---
    default_reply = (
        "Hmm 🤔 I’m not sure about that yet.\n"
        "Would you like me to connect you with a human from support?"
    )

    try:
        # Save unanswered query for admin review
        UnansweredQuery.objects.create(
            session=session,
            message=message_text,
            detected_intent=memory.get("last_intent", "unknown"),
            context=memory,
            requires_human=True,
        )
        logger.info(f"Marked message as requires_human in session {session.id}")
    except Exception as e:
        logger.exception(f"Failed to log unanswered query: {e}")

    # --- Save message & update memory ---
    history.append({"user": message_text, "bot": default_reply})
    memory.update({
        "last_user_message": message_text,
        "last_bot_reply": default_reply,
        "topic": "general",
        "recent_history": history[-5:]
    })
    session.memory = memory
    session.save(update_fields=["memory", "last_active"])

    reply = _save_bot_reply(session, default_reply)
    return {"reply": reply, "requires_human": True}

# ==========================================================
# FAQ helpers & caching
# ==========================================================
@lru_cache(maxsize=1)
def _static_faq_list():
    """Return preprocessed list of (lower_question, answer) for fast matching."""
    return [(q.lower(), a) for q, a in FAQS.items()]


def match_faq_response(user_input: str) -> Optional[str]:
    """
    Try exact, keyword overlap, then fuzzy matching over static FAQS.
    Returns answer or None.
    """
    if not user_input:
        return None
    text = user_input.lower().strip()
    faqs = _static_faq_list()

    # Exact substring match
    for q, a in faqs:
        if q in text:
            return a

    # Keyword overlap (cheap)
    for q, a in faqs:
        if any(word in text for word in q.split()):
            return a

    # Fuzzy match
    best_ratio = 0.0
    best_answer = None
    for q, a in faqs:
        ratio = SequenceMatcher(None, text, q).ratio()
        if ratio > best_ratio:
            best_ratio = ratio
            best_answer = a

    return best_answer if best_ratio >= FUZZY_THRESHOLD else None


def _fetch_dynamic_faqs() -> List[Dict]:
    """Fetch & parse remote FAQ page; returns list of dicts with 'question'/'answer'."""
    cache_key = "dynamic_faqs"
    faqs = cache.get(cache_key)
    if faqs is not None:
        return faqs

    try:
        faqs = fetch_faq_from_page(FAQ_PAGE_URL) or []
        cache.set(cache_key, faqs, timeout=FAQ_CACHE_TTL)
        return faqs
    except Exception:
        logger.exception("Failed to fetch dynamic FAQs from %s", FAQ_PAGE_URL)
        return []


def get_dynamic_faq_answer(user_message: str) -> Optional[str]:
    """Match against dynamic FAQ list with fuzzy matching."""
    if not user_message:
        return None
    faqs = _fetch_dynamic_faqs()
    if not faqs:
        return None

    text = user_message.lower().strip()
    best_ratio = 0.0
    best_answer = None
    for f in faqs:
        q = f.get("question", "").lower()
        ratio = SequenceMatcher(None, q, text).ratio()
        if ratio > best_ratio:
            best_ratio = ratio
            best_answer = f.get("answer")
    return best_answer if best_ratio >= FUZZY_THRESHOLD else None


def get_best_faq_answer(user_message: str) -> Optional[str]:
    """
    Combine static and dynamic FAQ checks and return best result.
    """
    if not user_message:
        return None

    static_answer = match_faq_response(user_message)
    dynamic_answer = get_dynamic_faq_answer(user_message)

    if not static_answer and not dynamic_answer:
        return None
    # Heuristic: prefer dynamic if similarity to question is stronger
    # We score by comparing messages to all FAQ questions quickly
    def score_candidates(answer_candidate: Optional[str], lookup_list):
        if not answer_candidate:
            return 0.0
        # score as max similarity to any question string
        return max((SequenceMatcher(None, q, user_message.lower()).ratio() for q in lookup_list), default=0.0)

    static_questions = [q for q, _ in _static_faq_list()]
    dynamic_questions = [f.get("question", "") for f in _fetch_dynamic_faqs()]

    static_score = score_candidates(static_answer, static_questions) if static_answer else 0.0
    dynamic_score = score_candidates(dynamic_answer, dynamic_questions) if dynamic_answer else 0.0

    return dynamic_answer if dynamic_score >= static_score and dynamic_answer else static_answer


# ---------------------------------------------------------------------
#  Persona & Small Talk
# ---------------------------------------------------------------------

def handle_small_talk(user_input: str) -> str | None:
    """Friendly personality responses for small talk and common phrases."""

    greetings = ["hi", "hello", "hey", "good morning", "good evening"]
    farewells = ["bye", "goodbye", "see you", "talk later"]
    thanks = ["thank", "thanks", "appreciate"]

    if any(re.search(rf"\b{g}\b", user_input) for g in greetings):
        return "Hey gorgeous ✨ I’m Luchi — your beauty assistant. How can I make your day better?"

    if "how are you" in user_input:
        return "Feeling fabulous 💅 Ready to glam up your day?"

    if "who are you" in user_input:
        return "I’m Luchi, your personal beauty assistant 💖 Here to help you shine."

    if any(re.search(rf"\b{t}\b", user_input) for t in thanks):
        return "You’re very welcome, love 💫 Always happy to help!"

    if any(re.search(rf"\b{f}\b", user_input) for f in farewells):
        return "Goodbye for now 💕 Come back soon for more glam inspo!"

    return None


# ---------------------------------------------------------------------
#  Utilities
# ---------------------------------------------------------------------

def clean_html(raw_html: str) -> str:
    """Sanitize and clean incoming text."""
    return BeautifulSoup(raw_html, "html.parser").get_text()


def _save_bot_reply(session: ChatSession, reply_text: str, topic: str | None = None) -> str:
    """
    Save bot reply, update session memory, and refresh last_active timestamp.
    Keeps rolling chat history and prepares for NLP-enhanced memory (Step 18).
    """
    try:
        # ---- Save reply message ----
        ChatMessage.objects.create(
            session=session,
            sender=ChatMessage.SENDER_BOT,
            content=reply_text,
        )

        # ---- Update memory structure ----
        memory = session.memory or {}

        # Append this turn to recent history
        history = memory.get("recent_history", [])
        history.append({"bot": reply_text})
        memory["recent_history"] = history[-5:]

        # Update key memory fields
        memory["last_bot_reply"] = reply_text
        if topic:
            memory["topic"] = topic

        # Save updates safely
        session.memory = memory
        session.last_active = timezone.now()
        session.save(update_fields=["memory", "last_active"])

    except Exception as e:
        logger.exception(f"⚠️ Failed to save bot reply or update memory: {e}")

    return reply_text


# ---------------------------------------------------------------------
#  Lead Management
# ---------------------------------------------------------------------

def save_lead(
    email: str,
    name: str = "",
    phone: str = "",
    message: str = "",
    source: str = "chat-widget",
):
    """Safely capture lead/contact data from the assistant."""
    if not email:
        raise ValueError("Email is required to save a lead.")

    try:
        lead = Lead.objects.create(
            email=email.strip().lower(),
            name=name.strip(),
            phone=phone.strip(),
            message=message.strip(),
            source=source,
        )
        logger.info(f"Lead captured: {lead.email} ({lead.source})")
        return lead
    except Exception as e:
        logger.exception(f"Failed to save lead: {e}")
        raise

def get_faq_answer(user_message: str) -> str | None:
    """
    Backward-compatible wrapper for legacy FAQ calls.
    Uses the improved match_faq_response() under the hood.
    """
    return match_faq_response(user_message)


def handle_product_search(request, query: str) -> dict:
    """
    Searches products by name, description, or category keywords.
    Returns structured product card data.
    """
    query = query.lower().strip()
    products = Product.objects.filter(
        Q(name__icontains=query) |
        Q(description__icontains=query) |
        Q(category__icontains=query)
    ).filter(stock__gt=0)[:5]

    if not products.exists():
        return {
            "message": "I couldn’t find anything matching that 🥺. Try another keyword, maybe?",
            "products": []
        }

    # ✅ safely use session currency
    currency = request.session.get("currency", "NGN")

    product_cards = [
        {
            "name": p.name,
            "price": as_currency(p.price, currency),
            "image": p.image.url if p.image else "",
            "url": reverse("shop:product_detail", args=[p.id]),
        }
        for p in products
    ]

    return {
        "message": "Here are some options I found for you 💁‍♀️✨",
        "products": product_cards
    }


def handle_order_tracking(request, query: str) -> dict:
    """
    Handles user requests to track an order by ID, tracking number, or email.
    Returns both chat-friendly text and structured data for the frontend.
    """

    query = query.strip()
    if not query:
        return {
            "message": "Please provide your *order number* or *email address* so I can look it up 💅.",
            "order": None,
        }

    # --- STEP 1: Detect query type (email or numeric ID) ---
    email_match = re.search(r"[\w\.-]+@[\w\.-]+\.\w+", query)
    order_id_match = re.search(r"\b\d{2,}\b", query)

    order = None

    # --- STEP 2: Priority lookup ---
    if email_match:
        lookup_email = email_match.group(0)
        order = (
            Order.objects.filter(email__iexact=lookup_email)
            .order_by("-created_at")
            .first()
        )
        logger.info(f"[OrderTracking] Lookup by email: {lookup_email}")

    elif order_id_match:
        try:
            int_id = int(order_id_match.group(0))
            order = (
                Order.objects.filter(id=int_id)
                .order_by("-created_at")
                .first()
            )
            logger.info(f"[OrderTracking] Lookup by order ID: {int_id}")
        except ValueError:
            logger.warning(f"[OrderTracking] Invalid order ID format: {order_id_match.group(0)}")

    # --- STEP 3: Fallback lookup by payment reference or full-text match ---
    if not order:
        lookup_value = query
        order = (
            Order.objects.filter(
                Q(payment_reference__iexact=lookup_value)
                | Q(email__iexact=lookup_value)
            )
            .order_by("-created_at")
            .first()
        )
        logger.info(f"[OrderTracking] Fallback lookup by reference/query: {lookup_value}")

    if not order:
        return {
            "message": "🤔 I couldn’t find any order with that tracking number or email. Double-check and try again 💅.",
            "order": None,
        }

    # --- STEP 4: Status normalization ---
    STATUS_MAP = {
        "pending": ("Pending Payment", "🕓"),
        "processing": ("Processing", "🔧"),
        "shipped": ("Shipped", "📦"),
        "out_for_delivery": ("Out for Delivery", "🚚"),
        "delivered": ("Delivered", "✅"),
        "delayed": ("Delayed", "⚠️"),
        "cancelled": ("Cancelled", "❌"),
    }

    raw_status = str(getattr(order, "status", "") or "").lower()
    status_label, status_icon = STATUS_MAP.get(raw_status, ("Processing", "ℹ️"))
    status_display = f"{status_icon} {status_label}"

    # --- STEP 5: Format total safely ---
    currency = getattr(order, "currency", "NGN")
    total_value = getattr(order, "total", 0)
    try:
        formatted_total = f"{currency} {float(total_value):,.2f}"
    except (ValueError, TypeError):
        formatted_total = f"{currency} {total_value}"

    # --- STEP 6: Build user-facing message ---
    customer_name = escape(getattr(order, "customer_name", "Customer"))
    status_msg = (
        f"✨ Order **#{order.id}** for **{customer_name}**\n"
        f"{status_display} — {'Paid ✅' if getattr(order, 'paid', False) else 'Unpaid ❌'}\n"
        f"💰 Total: {formatted_total}\n"
        f"📅 Date: {order.created_at.strftime('%b %d, %Y')}\n"
    )

    address = getattr(order, "address", None)
    if address:
        status_msg += f"🏠 Shipping to: {escape(address)}\n"

    tracking_id = getattr(order, "payment_reference", None)
    if tracking_id:
        status_msg += f"🔖 Tracking ID: {tracking_id}\n"

    # --- STEP 7: Structured response for frontend ---
    order_card_data = {
        "id": str(order.id),
        "status": status_label,
        "paid": bool(getattr(order, "paid", False)),
        "total": formatted_total,
        "date": order.created_at.strftime("%b %d, %Y"),
        "address": address,
        "tracking": tracking_id,
        "customer_name": customer_name,
    }

    logger.info(f"[OrderTracking] Found order #{order.id} | Status: {status_label}")

    return {
        "message": status_msg.strip(),
        "order": order_card_data,
    }


logger = logging.getLogger(__name__)

def save_lead_from_chat(session, message, email=None, name=None, phone=None):
    """
    Extracts lead info (email, phone, name) from chat and saves to Lead model.
    Returns a user-facing message or None on success.
    Side-effects:
      - Updates session.memory with lead details
      - Notifies internal team via email
    """
    message = strip_tags(str(message or "")).strip()

    # --- Try regex extraction ---
    if not email:
        email_match = re.search(r"[\w\.-]+@[\w\.-]+\.\w+", message)
        if email_match:
            email = email_match.group(0).lower().strip()

    if not phone:
        phone_match = re.search(r"\+?\d{7,15}", re.sub(r"\s+", "", message))
        if phone_match:
            phone = phone_match.group(0).strip()

    # --- Fallback to existing session data ---
    memory = session.memory or {}
    name = name or memory.get("user_name")
    email = (email or memory.get("user_email") or "").strip()
    phone = phone or memory.get("user_phone")

    if not email:
        return "Please share your email so our team can reach you 📩"

    # --- Check for existing lead to prevent duplication ---
    try:
        existing = Lead.objects.filter(email__iexact=email, source="chat-widget").order_by("-created_at").first()
    except Exception:
        existing = None

    if existing:
        memory.update({
            "user_name": existing.name or name,
            "user_email": existing.email,
            "user_phone": existing.phone,
            "lead_id": str(existing.id),
            "lead_opt_in": bool(existing.opt_in),
        })
        try:
            session.memory = memory
            session.save(update_fields=["memory"])
        except Exception as e:
            logger.exception("Failed to save session memory for existing lead: %s", e)

        return f"Our team already has your contact ({existing.email}) 💌 — they’ll follow up soon!"

    # --- Create new lead ---
    try:
        lead = Lead.objects.create(
            name=(name or "")[:120],
            email=email,
            phone=(phone or "")[:30],
            message=(message or "")[:2000],
            source="chat-widget",
            opt_in=True,
        )
        logger.info("✅ Lead created via chat: %s (id=%s)", email, lead.id)
    except Exception as exc:
        logger.exception("Failed to create Lead: %s", exc)
        return "Oops — something went wrong saving your contact. Try again in a moment, please."

    # --- Save context back to session ---
    try:
        memory.update({
            "user_name": name,
            "user_email": email,
            "user_phone": phone,
            "lead_id": str(lead.id),
            "lead_opt_in": True,
        })
        session.memory = memory
        session.save(update_fields=["memory"])
    except Exception as e:
        logger.exception("Failed to update session memory after lead creation: %s", e)

    # --- Notify internal team ---
    try:
        notify_team_of_lead(lead)
    except Exception as e:
        logger.exception("Lead notification failed: %s", e)

    return f"Thanks {name or 'there'} 💫 Our team will reach out to you soon at {email}!"
