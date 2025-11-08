import json
import logging
from datetime import timedelta

from django.conf import settings
from django.contrib.admin.views.decorators import staff_member_required
from django.http import JsonResponse
from django.shortcuts import render
from django.urls import reverse, NoReverseMatch
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from .intent import detect_intent

from .models import ChatSession, ChatMessage
from .analytics import get_chat_stats, get_lead_stats
from .lead_capture import handle_lead_capture
from .utils import (
    handle_product_search,
    handle_order_tracking,
    get_faq_answer,
    process_user_message,
    extract_keywords_and_entities,
    clean_html,
    save_lead_from_chat,
)

logger = logging.getLogger(__name__)

# =============================================================
# === Constants & Configuration
# =============================================================
CHAT_SESSION_TIMEOUT_MINUTES = getattr(settings, "CHAT_SESSION_TIMEOUT_MINUTES", 30)
CHAT_MIN_MESSAGE_INTERVAL = getattr(settings, "CHAT_MIN_MESSAGE_INTERVAL", 2)  # seconds


# =============================================================
# === Utilities
# =============================================================
def ping(request):
    """Basic health check endpoint."""
    return JsonResponse({"status": "ok", "app": "assistant"})


def safe_reverse(name: str, fallback: str = "/contact/") -> str:
    """Return a reversed URL if available, else fallback safely."""
    try:
        return reverse(name)
    except NoReverseMatch:
        return fallback


def is_session_stale(session: ChatSession) -> bool:
    """Check if a chat session is inactive beyond timeout."""
    return timezone.now() - session.last_active > timedelta(minutes=CHAT_SESSION_TIMEOUT_MINUTES)


def rate_limited(session: ChatSession) -> bool:
    """Return True if message sent too soon after previous."""
    return (timezone.now() - session.last_active).total_seconds() < CHAT_MIN_MESSAGE_INTERVAL


# =============================================================
# === Main Chat API
# =============================================================
@csrf_exempt
@require_POST
def chat_api(request):
    try:
        data = json.loads(request.body.decode("utf-8"))
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON payload."}, status=400)

    message = (data.get("message") or "").strip()
    session_id = data.get("session_id")

    if not message:
        return JsonResponse({"reply": "Say something, beautiful 💬"}, status=200)

    # Retrieve or create session
    session = ChatSession.objects.filter(id=session_id).first() if session_id else None
    if not session:
        session = ChatSession.objects.create()
        logger.info(f"🆕 New chat session created: {session.id}")

    # Prevent concurrent processing
    if session.memory.get("is_processing"):
        return JsonResponse(
            {"reply": "⏳ Hold on a second — I'm still processing your last message!"},
            status=429,
        )

    session.memory["is_processing"] = True
    session.save(update_fields=["memory"])

    try:
        # Reset stale sessions
        if is_session_stale(session):
            session.memory = {}
            if hasattr(session, "requires_human"):
                session.requires_human = False
                session.save(update_fields=["memory", "requires_human"])
            else:
                session.save(update_fields=["memory"])
            logger.info(f"♻️ Reset stale session memory: {session.id}")

        # --- initialize memory + helpers ---
        memory = session.memory or {}
        history = memory.get("recent_history", [])
        topic = memory.get("topic", "general")
        # New structured lead flow stage: None | "awaiting_consent" | "awaiting_contact"
        lead_stage = memory.get("lead_flow_stage")
        handoff_prompt_shown = bool(memory.get("handoff_prompt_shown", False))

        # Persist user message
        ChatMessage.objects.create(session=session, sender=ChatMessage.SENDER_USER, content=message)

        reply_text = ""
        response_data = {}
        products = []
        requires_human = False
        bot_message_already_saved = False

        # NLP & intent
        nlp_data = extract_keywords_and_entities(message)
        intent = detect_intent(message)
        logger.info(f"[Intent] {intent} | Message: {message}")

        # If already queued for human
        if getattr(session, "requires_human", False):
            reply_text = "You're already being connected to a human representative 👩🏽‍💻"

        # ---------- Lead capture flow ----------
        # 1) user expresses need for help -> ask consent (only once)
        elif intent == "needs_help" and not lead_stage:
            reply_text = "I can have someone reach out to assist you 😊 — can we do that?"
            memory["lead_flow_stage"] = "awaiting_consent"
            memory["handoff_prompt_shown"] = True

        # 2) waiting for consent
        elif lead_stage == "awaiting_consent":
            low = message.lower().strip()
            if low in ["yes", "yeah", "yep", "sure", "ok", "okay", "please", "please do"]:
                # move to contact collection
                memory["lead_flow_stage"] = "awaiting_contact"
                memory["handoff_prompt_shown"] = False
                reply_text = "Great — please provide your email or phone number so our team can reach you."
            elif low in ["no", "nope", "nah", "not now"]:
                # user declined
                memory.pop("lead_flow_stage", None)
                memory["handoff_prompt_shown"] = False
                reply_text = "No problem! I won’t store any info. Let me know if you change your mind."
            else:
                # not a clear yes/no; treat message as possible contact if it contains email/phone
                import re
                email_match = re.search(r"[\w\.-]+@[\w\.-]+\.\w+", message)
                phone_match = re.search(r"\+?\d{7,15}", message.replace(" ", ""))
                if email_match or phone_match:
                    # user responded with contact info straight away after prompt
                    saved_msg = save_lead_from_chat(session, message)
                    # save_lead_from_chat is expected to return a user-facing string
                    reply_text = saved_msg or "Thanks — our team will reach out soon."
                    memory.pop("lead_flow_stage", None)
                    memory["lead_opt_in"] = True
                    requires_human = True
                    session.requires_human = True
                    session.save(update_fields=["requires_human"])
                else:
                    # unclear answer, re-prompt consent question once
                    reply_text = "Would you like us to reach out to help you? (Yes / No)"
                    memory["handoff_prompt_shown"] = True
                    # keep still in awaiting_consent

        # 3) waiting for contact info
        elif lead_stage == "awaiting_contact":
            import re
            email_match = re.search(r"[\w\.-]+@[\w\.-]+\.\w+", message)
            phone_match = re.search(r"\+?\d{7,15}", message.replace(" ", ""))
            if email_match or phone_match:
                saved_msg = save_lead_from_chat(session, message)
                # If helper returns a guidance string (e.g., asks for email), honor it
                reply_text = saved_msg or "Thanks — our team will reach out soon."
                # Clear stage and mark opt-in
                memory.pop("lead_flow_stage", None)
                memory["lead_opt_in"] = True
                requires_human = True
                session.requires_human = True
                session.save(update_fields=["requires_human"])
            else:
                # User didn't provide contact info — prompt again
                reply_text = "That doesn’t look like a valid email or phone number. Could you re-enter it?"
                # remain in awaiting_contact

        # If the bot showed the handoff prompt and user answered simple yes/no without entering lead_stage (older flag)
        elif handoff_prompt_shown and message.lower() in ["yes", "yeah", "yep", "sure", "ok", "okay"]:
            # ask for contact info
            memory["lead_flow_stage"] = "awaiting_contact"
            memory["handoff_prompt_shown"] = False
            reply_text = "Great — please provide your email or phone number so our team can reach you."

        elif handoff_prompt_shown and message.lower() in ["no", "nope", "nah"]:
            memory["handoff_prompt_shown"] = False
            reply_text = "Alright! I’ll stay with you then 💪"

        # ---------- Existing intents ----------
        elif intent == "product_search":
            response_data = handle_product_search(request, message)
            reply_text = response_data.get("message", "")
            products = response_data.get("products", [])
            topic = "shopping"

        elif intent == "order_tracking":
            response_data = handle_order_tracking(request, message)
            reply_text = response_data.get("message", "")
            topic = "orders"

        # FAQs and fallback / process_user_message
        else:
            faq_answer = get_faq_answer(message)
            if faq_answer:
                reply_text = faq_answer
                topic = "faq"
            else:
                pm_result = process_user_message(session, message)
                if isinstance(pm_result, dict):
                    # process_user_message already saved the bot reply inside utils._save_bot_reply()
                    reply_text = pm_result.get("reply", "") or ""
                    requires_human = pm_result.get("requires_human", False)
                    bot_message_already_saved = True
                else:
                    reply_text = str(pm_result) if pm_result is not None else ""
                topic = "general"

        # Sanitize reply
        safe_reply = clean_html(reply_text)

        # Persist bot message only if helper hasn't already persisted it
        if not bot_message_already_saved:
            try:
                ChatMessage.objects.create(session=session, sender=ChatMessage.SENDER_BOT, content=safe_reply)
            except Exception as e:
                logger.exception(f"Failed to persist bot message: {e}")

        # Update session memory and history
        history.append({"user": message, "bot": safe_reply, "intent": intent})
        memory.update({
            "last_user_message": message,
            "last_bot_reply": safe_reply,
            "last_intent": intent,
            "topic": topic,
            "recent_history": history[-5:],
            "context_reset": False,
        })
        # Persist memory and last_active
        session.memory = memory
        session.last_active = timezone.now()
        session.save(update_fields=["memory", "last_active"])

        response = {
            "session_id": str(session.id),
            "reply": safe_reply,
            "products": products,
            "order": response_data.get("order"),
            "requires_human": requires_human,
            "handoff_url": safe_reverse("contact") if requires_human else None,
            "timestamp": timezone.now().isoformat(),
        }

        return JsonResponse(response, status=200)

    finally:
        # Ensure we clear the processing flag even on error
        try:
            session.memory = session.memory or {}
            session.memory["is_processing"] = False
            session.save(update_fields=["memory"])
        except Exception:
            logger.exception("Failed to clear is_processing flag for session %s", getattr(session, "id", None))

# =============================================================
# === Analytics Dashboard
# =============================================================
@staff_member_required
def analytics_dashboard(request):
    """Simple admin-only dashboard for chat & lead analytics."""
    chat_stats = get_chat_stats()
    lead_stats = get_lead_stats()
    return render(
        request,
        "assistant/analytics.html",
        {"chat_stats": chat_stats, "lead_stats": lead_stats},
    )
