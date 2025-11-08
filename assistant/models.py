import uuid
from django.db import models
from django.utils import timezone
from django.conf import settings
import uuid
from django.conf import settings
from django.db import models
from django.utils import timezone


class FAQ(models.Model):
    """
    Stores frequently asked questions and their answers.
    Used by the assistant to respond to common user inquiries.
    """
    CATEGORY_CHOICES = [
        ('shipping', 'Shipping & Delivery'),
        ('returns', 'Returns & Refunds'),
        ('payment', 'Payment & Checkout'),
        ('product', 'Product Info'),
        ('general', 'General'),
    ]

    question = models.CharField(max_length=255, unique=True)
    answer = models.TextField()
    keywords = models.TextField(
        blank=True,
        help_text="Comma-separated trigger words/phrases for rule-based matching"
    )
    category = models.CharField(
        max_length=50,
        choices=CATEGORY_CHOICES,
        blank=True,
        help_text="Used to group related FAQs (optional)"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "FAQ"
        verbose_name_plural = "FAQs"
        indexes = [
            models.Index(fields=['question']),
            models.Index(fields=['category']),
        ]

    def __str__(self):
        return self.question




class ChatSession(models.Model):
    """
    Represents a user's chat session.
    Stores short-term memory and optional metadata for personalization.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='chat_sessions',
        help_text="Linked user (if logged in)"
    )
    created_at = models.DateTimeField(default=timezone.now)
    last_active = models.DateTimeField(auto_now=True)
    memory = models.JSONField(default=dict, blank=True, help_text="Session memory (context during chat)")
    meta = models.JSONField(default=dict, blank=True, help_text="Optional metadata (ip, user agent, utm, etc.)")

    class Meta:
        ordering = ['-last_active']
        indexes = [
            models.Index(fields=['last_active']),
        ]

    def __str__(self):
        return f"Session {self.id} ({self.user})" if self.user else str(self.id)

    def update_memory(self, key, value):
        """Helper to store temporary memory context."""
        mem = self.memory or {}
        mem[key] = value
        self.memory = mem
        self.save(update_fields=['memory', 'last_active'])

    # ✅ New helper for admin analytics
    def message_count(self):
        """Count total messages in the session."""
        return self.messages.count()


class ChatMessage(models.Model):
    """
    Each chat message (from user, bot, or system).
    Stores message text, sender type, and metadata (intent, confidence, etc.).
    """
    SENDER_USER = 'user'
    SENDER_BOT = 'bot'
    SENDER_SYSTEM = 'system'
    SENDER_CHOICES = [
        (SENDER_USER, 'User'),
        (SENDER_BOT, 'Bot'),
        (SENDER_SYSTEM, 'System'),
    ]

    id = models.BigAutoField(primary_key=True)
    session = models.ForeignKey(ChatSession, on_delete=models.CASCADE, related_name='messages')
    sender = models.CharField(max_length=10, choices=SENDER_CHOICES)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    metadata = models.JSONField(default=dict, blank=True, help_text="Optional metadata (e.g. detected intent)")

    class Meta:
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['session', 'created_at']),
        ]

    def __str__(self):
        return f'{self.sender} @ {self.created_at.isoformat()}'

    def short_content(self):
        """Truncated message preview for admin display."""
        return (self.content[:60] + "...") if len(self.content) > 60 else self.content


class Lead(models.Model):
    """
    Stores opt-in contact info collected through the assistant.
    Keep minimal and obtain explicit consent before saving PII.
    """
    name = models.CharField(max_length=120, blank=True)
    email = models.EmailField()
    phone = models.CharField(max_length=30, blank=True)
    message = models.TextField(blank=True)
    source = models.CharField(max_length=50, blank=True, help_text='Source of lead (e.g. chat-widget)')
    opt_in = models.BooleanField(default=False, help_text='User explicitly consented to follow-up messages')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['email']),
        ]

    def __str__(self):
        label = f'{self.email} ({self.name})' if self.name else self.email
        return label

    # ✅ Simple analytics summary (for admin or dashboard)
    @staticmethod
    def stats():
        total = Lead.objects.count()
        last_30_days = Lead.objects.filter(
            created_at__gte=timezone.now() - timezone.timedelta(days=30)
        ).count()
        return {"total": total, "last_30_days": last_30_days}

class UnansweredQuery(models.Model):
    session = models.ForeignKey(ChatSession, on_delete=models.CASCADE, related_name="unanswered_queries")
    message = models.TextField()
    detected_intent = models.CharField(max_length=100, blank=True, null=True)
    context = models.JSONField(default=dict, blank=True)
    requires_human = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def short_message(self):
        return (self.message[:60] + "...") if len(self.message) > 60 else self.message

    def __str__(self):
        return f"Unanswered ({self.detected_intent or 'unknown'}) – {self.short_message()}"