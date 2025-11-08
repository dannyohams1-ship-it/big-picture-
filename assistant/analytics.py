# assistant/analytics.py
from datetime import timedelta
from django.utils import timezone
from django.db.models import Count
from django.db.models.functions import TruncHour
from .models import ChatSession, ChatMessage, Lead

def get_chat_stats():
    
    now = timezone.now()
    day_ago = now - timedelta(days=1)

    total_sessions = ChatSession.objects.count()
    active_sessions = ChatSession.objects.filter(last_active__gte=day_ago).count()

    total_messages = ChatMessage.objects.count()
    avg_messages = total_messages / total_sessions if total_sessions > 0 else 0

    # ✅ Use TruncHour instead of SQLite-only strftime
    hourly_activity = (
        ChatMessage.objects.filter(created_at__gte=day_ago)
        .annotate(hour=TruncHour("created_at"))
        .values("hour")
        .annotate(count=Count("id"))
        .order_by("hour")
    )

    return {
        "total_sessions": total_sessions,
        "active_sessions": active_sessions,
        "total_messages": total_messages,
        "avg_messages": round(avg_messages, 2),
        "hourly_activity": [
            {"hour": entry["hour"].strftime("%H:%M"), "count": entry["count"]}
            for entry in hourly_activity
        ],
    }


def get_lead_stats():
    """
    Aggregates lead data for admin analytics dashboard.
    """
    now = timezone.now()
    month_ago = now - timedelta(days=30)

    total_leads = Lead.objects.count()
    leads_30_days = Lead.objects.filter(created_at__gte=month_ago).count()
    opt_in_count = Lead.objects.filter(opt_in=True).count()

    lead_sources = (
        Lead.objects.values("source")
        .annotate(count=Count("id"))
        .order_by("-count")
    )

    return {
        "total_leads": total_leads,
        "leads_30_days": leads_30_days,
        "opt_in_count": opt_in_count,
        "lead_sources": list(lead_sources),
    }
