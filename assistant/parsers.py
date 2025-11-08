# assistant/parsers.py
import requests
from bs4 import BeautifulSoup
import logging

logger = logging.getLogger(__name__)

def fetch_faq_from_page(url: str):
    """
    Fetches and parses the live FAQ page into structured question-answer pairs.
    Works with your Bootstrap accordion HTML.
    """
    try:
        response = requests.get(url, timeout=8)
        response.raise_for_status()
    except Exception as e:
        logger.error(f"Failed to fetch FAQ page: {e}")
        return []

    soup = BeautifulSoup(response.text, "html.parser")

    faqs = []
    # Each FAQ is inside a <div class="accordion-item">
    for item in soup.select(".accordion-item"):
        question_tag = item.select_one(".accordion-button")
        answer_tag = item.select_one(".accordion-body")

        if question_tag and answer_tag:
            question = question_tag.get_text(strip=True)
            answer = answer_tag.get_text(strip=True)
            faqs.append({
                "question": question,
                "answer": answer,
            })

    logger.info(f"Parsed {len(faqs)} FAQs from page.")
    return faqs
