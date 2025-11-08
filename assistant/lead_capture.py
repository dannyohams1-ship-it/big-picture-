# assistant/lead_capture.py

import re
import logging
from .models import Lead

logger = logging.getLogger(__name__)


def handle_lead_capture(session: dict, message: str) -> dict:
    """
    Multi-step flow:
      1️⃣ Ask for consent
      2️⃣ Collect contact info
      3️⃣ Save lead
    """
    context = session.get("context", {})
    stage = context.get("stage")

    # === STAGE 1: Start lead flow ===
    if not stage:
        context.update({
            "stage": "awaiting_consent",
            "partial_lead": {"message": message, "source": "chat-widget"}
        })
        session["context"] = context
        return {"reply": "Sure! Can we reach out to you to assist further? 😊"}

    # === STAGE 2: Waiting for consent ===
    if stage == "awaiting_consent":
        if message.lower() in ["yes", "yeah", "yep", "sure", "ok", "okay"]:
            context["stage"] = "awaiting_contact"
            session["context"] = context
            return {"reply": "Great! Please provide your email or phone number so our team can reach you."}
        else:
            context.clear()
            session["context"] = context
            return {"reply": "No problem! I won’t store any info. Let me know if you change your mind."}

    # === STAGE 3: Waiting for contact info ===
    if stage == "awaiting_contact":
        email_match = re.search(r"[\w\.-]+@[\w\.-]+\.\w+", message)
        phone_match = re.search(r"\+?\d{7,15}", message.replace(" ", ""))

        email = email_match.group(0) if email_match else None
        phone = phone_match.group(0) if phone_match else None

        if not (email or phone):
            return {"reply": "That doesn’t look like a valid email or phone number. Could you re-enter it?"}

        try:
            lead = Lead.objects.create(
                name="",
                email=email or "",
                phone=phone or "",
                message=context["partial_lead"].get("message"),
                source=context["partial_lead"].get("source"),
                opt_in=True,
            )
            logger.info(f"✅ Lead saved: {lead.email or lead.phone}")
        except Exception as e:
            logger.exception("Failed to save lead: %s", e)
            return {"reply": "Oops, something went wrong while saving your info. Please try again."}

        context.clear()
        session["context"] = context
        return {"reply": "Thank you! Our team will reach out soon. 💬", "saved_lead": lead.id}

    return {"reply": "I'm not sure what you mean."}
