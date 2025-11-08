# admin.py
import json
from datetime import timedelta

from django.contrib import admin
from django.db import models
from django.db.models import Count
from django.utils import timezone
from django.utils.safestring import mark_safe
from django import forms

from .models import FAQ, ChatSession, ChatMessage, Lead, UnansweredQuery

# Try to use the built-in JSON editor widget (Django >= 4.1). Fallback to a Textarea.
try:
    from django.contrib.admin.widgets import JSONEditorWidget  # Django >=4.1
    JSON_WIDGET = JSONEditorWidget
except Exception:
    JSON_WIDGET = forms.Textarea


# -------------------------
# FAQ admin
# -------------------------
@admin.register(FAQ)
class FAQAdmin(admin.ModelAdmin):
    list_display = ("question", "category", "updated_at")
    list_filter = ("category", "created_at")
    search_fields = ("question", "answer", "keywords")
    readonly_fields = ("created_at", "updated_at")
    ordering = ("-updated_at",)
    list_per_page = 25

    fieldsets = (
        ("FAQ Details", {"fields": ("question", "answer", "category", "keywords")}),
        ("Timestamps", {"fields": ("created_at", "updated_at")}),
    )

    formfield_overrides = {
        # Keep keywords as a normal text field but JSONField override shown as example if used
        models.JSONField: {"widget": JSON_WIDGET},
    }


# -------------------------
# ChatMessage inline for ChatSession
# -------------------------
class ChatMessageInline(admin.TabularInline):
    model = ChatMessage
    extra = 0
    # Use a short preview method from the model rather than showing full content in list
    fields = ("sender", "short_content", "created_at", "metadata")
    readonly_fields = ("sender", "short_content", "created_at", "metadata")
    ordering = ("-created_at",)
    show_change_link = False

    # Provide a small formatting for metadata so it isn't a huge blob in the inline
    def metadata(self, obj):
        meta = obj.metadata or {}
        s = json.dumps(meta, indent=2)
        # truncate to avoid overly large inline rows
        short = (s[:200] + "...") if len(s) > 200 else s
        return mark_safe(f"<pre style='white-space:pre-wrap; max-width:420px'>{short}</pre>")
    metadata.short_description = "metadata"


# -------------------------
# ChatSession admin
# -------------------------
@admin.register(ChatSession)
class ChatSessionAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "created_at", "last_active", "message_count_preview", "memory_preview")
    search_fields = ("id", "user__username", "user__email")
    list_filter = ("created_at", "last_active")
    readonly_fields = ("id", "created_at", "last_active", "formatted_memory", "formatted_meta")
    ordering = ("-last_active",)
    list_per_page = 25
    list_select_related = ("user",)
    inlines = [ChatMessageInline]
    actions = ["delete_selected_sessions"]

    fieldsets = (
        (None, {"fields": ("id", "user", "created_at", "last_active")}),
        ("🧠 Memory Context", {"fields": ("formatted_memory",)}),
        ("🧩 Session Metadata", {"fields": ("formatted_meta",)}),
    )

    def delete_selected_sessions(self, request, queryset):
        count = queryset.count()
        queryset.delete()
        self.message_user(request, f"Deleted {count} session(s).")
    delete_selected_sessions.short_description = "Delete selected chat sessions"

    # Annotate message count to avoid N+1 queries in the changelist
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.annotate(_message_count=Count("messages"))

    def message_count_preview(self, obj):
        # use the annotated value if available
        return getattr(obj, "_message_count", obj.messages.count())
    message_count_preview.short_description = "Messages"

    # JSON previews for list/detail
    def memory_preview(self, obj):
        mem = obj.memory or {}
        text = json.dumps(mem, indent=2)
        short = (text[:200] + "...") if len(text) > 200 else text
        return mark_safe(f"<pre style='max-width:420px;white-space:pre-wrap'>{short}</pre>")
    memory_preview.short_description = "Memory (preview)"

    def formatted_memory(self, obj):
        mem = obj.memory or {}
        formatted = json.dumps(mem, indent=2)
        return mark_safe(f"<pre style='white-space:pre-wrap'>{formatted}</pre>")
    formatted_memory.short_description = "Full Memory"

    def formatted_meta(self, obj):
        meta = obj.meta or {}
        formatted = json.dumps(meta, indent=2)
        return mark_safe(f"<pre style='white-space:pre-wrap'>{formatted}</pre>")
    formatted_meta.short_description = "Session Metadata"

    formfield_overrides = {
        models.JSONField: {"widget": JSON_WIDGET},
    }


# -------------------------
# ChatMessage admin (standalone)
# -------------------------
@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    list_display = ("id", "session", "sender", "short_content", "created_at")
    search_fields = ("content", "session__id")
    list_filter = ("sender", "created_at")
    readonly_fields = ("id", "session", "sender", "content", "metadata", "created_at")
    ordering = ("-created_at",)
    list_per_page = 50
    list_select_related = ("session",)

    formfield_overrides = {
        models.JSONField: {"widget": JSON_WIDGET},
    }

    # short_content exists on the model; keep it consistent
    def short_content(self, obj):
        return obj.short_content() if hasattr(obj, "short_content") else (obj.content[:80] + "..." if len(obj.content) > 80 else obj.content)
    short_content.short_description = "Message"


# -------------------------
# Lead admin with changelist stats
# -------------------------
@admin.register(Lead)
class LeadAdmin(admin.ModelAdmin):
    list_display = ("email", "name", "opt_in", "source", "created_at")
    list_filter = ("opt_in", "source", "created_at")
    search_fields = ("email", "name", "message")
    readonly_fields = ("created_at",)
    ordering = ("-created_at",)
    list_per_page = 25

    change_list_template = "admin/assistant/lead_changelist.html"

    def changelist_view(self, request, extra_context=None):
        """
        Inject quick stats (lead analytics) into admin list page.
        """
        extra_context = extra_context or {}
        total = Lead.objects.count()
        cutoff = timezone.now() - timedelta(days=30)
        last_30_days = Lead.objects.filter(created_at__gte=cutoff).count()

        extra_context["total_leads"] = total
        extra_context["recent_leads"] = last_30_days

        return super().changelist_view(request, extra_context=extra_context)


# -------------------------
# UnansweredQuery admin
# -------------------------
@admin.register(UnansweredQuery)
class UnansweredQueryAdmin(admin.ModelAdmin):
    list_display = ("short_message", "detected_intent", "requires_human", "created_at")
    list_filter = ("requires_human", "detected_intent", "created_at")
    search_fields = ("message", "detected_intent")
    readonly_fields = ("session", "message", "context", "requires_human", "detected_intent", "created_at")
    ordering = ("-created_at",)
    list_per_page = 25

    formfield_overrides = {
        models.JSONField: {"widget": JSON_WIDGET},
    }

    # reuse model helper if present
    def short_message(self, obj):
        return obj.short_message() if hasattr(obj, "short_message") else (obj.message[:80] + "..." if len(obj.message) > 80 else obj.message)
    short_message.short_description = "Message"


# -------------------------
# Global admin site branding
# -------------------------
admin.site.site_header = "Luchi Assistant Admin"
admin.site.site_title = "Luchi Portal"
admin.site.index_title = "Assistant Management Dashboard"
