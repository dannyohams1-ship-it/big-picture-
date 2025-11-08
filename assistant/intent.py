from .utils import extract_keywords_and_entities

def detect_intent(message: str) -> str:
    """
    Hybrid intent detector — combines rule-based logic + NLP (spaCy).
    Handles product search, order tracking, FAQ, contact/handoff,
    and fallback with lightweight NLP keyword/entity extraction.
    """
    if not message:
        return "fallback"

    msg = message.lower().strip()
    nlp_data = extract_keywords_and_entities(msg)
    keywords = nlp_data.get("keywords", [])
    entities = nlp_data.get("entities", [])

    # === Rule-based intent detection ===

    # FAQ topics
    if any(word in msg for word in ["shipping", "delivery", "ship", "courier"]):
        return "faq_shipping"
    elif any(word in msg for word in ["return", "refund", "exchange"]):
        return "faq_return"

    # Product search
    elif any(word in msg for word in ["buy", "show", "price", "wig", "lace", "extensions", "shop"]):
        return "product_search"

    # Order tracking
    elif any(phrase in msg for phrase in [
        "track", "order status", "where is my order", "track my order"
    ]):
        return "order_tracking"

    # === Human handoff detection (Step 16) ===
    elif any(phrase in msg for phrase in [
        "help", "not working", "problem", "stuck", "assist", "issue", "can't", "cannot", "error"
    ]):
        return "needs_help"

    # Direct contact request
    elif any(phrase in msg for phrase in ["contact", "agent", "representative", "talk to", "support"]):
        return "contact"

    # === NLP-based fallback logic ===
    if any(k in keywords for k in ["track", "order", "status"]):
        return "order_tracking"
    if any(k in keywords for k in ["buy", "show", "wig", "frontal", "bundle", "curly"]):
        return "product_search"
    if any(ent.lower() in ["lagos", "abuja", "nigeria"] for ent in entities):
        return "location_query"
    if any(k in keywords for k in ["problem", "help", "assist", "issue", "fix"]):
        return "needs_help"

    return "fallback"
