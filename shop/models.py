from django.db import models
from django.utils import timezone
import uuid 

class Product(models.Model):
    CATEGORY_CHOICES = [
        ('wigs', 'Wigs & Extensions'),
        ('laces', 'Laces'),
    ]
    LACE_TYPE_CHOICES = [
    ('HD Lace', 'HD Lace'),
    ('Swiss Lace', 'Swiss Lace'),
    ('Transparent Lace', 'Transparent Lace'),
]


    name = models.CharField(max_length=200)
    description = models.TextField()
    short_description = models.CharField(max_length=255, blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    image = models.ImageField(upload_to='products/', blank=True, null=True)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default="wigs")

    lace_type = models.CharField(
        max_length=50,
        choices=LACE_TYPE_CHOICES,
        blank=True,
        null=True,
        help_text="If this product is a lace, choose its lace type (HD Lace / Swiss Lace)."
    )

    # --- New descriptive fields ---
    story_text = models.TextField(blank=True)
    overview = models.TextField(blank=True)
    hair_type = models.CharField(max_length=100, blank=True, null=True)
    density = models.CharField(max_length=50, blank=True, null=True)
    color = models.CharField(max_length=100, blank=True, null=True)
    origin = models.CharField(max_length=100, blank=True, null=True)
    length = models.CharField(max_length=50, blank=True, null=True)

    # --- Variant options ---
    length_options = models.JSONField(default=list, blank=True)
    lace_type_options = models.JSONField(default=list, blank=True)
    color_options = models.JSONField(default=list, blank=True)

    # --- Existing system fields ---
    created_at = models.DateTimeField(auto_now_add=True)
    stock = models.PositiveIntegerField(default=10)
    is_best_seller = models.BooleanField(default=False)

    def __str__(self):
        return self.name

    @property
    def average_rating(self):
        try:
            qs = self.reviews.all()
            if not qs.exists():
                return 0
            avg = qs.aggregate(models.Avg('rating'))['rating__avg']
            return round(avg or 0, 2)
        except Exception:
            return 0


class ProductImage(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="images")
    image = models.ImageField(upload_to="products/")
    caption = models.CharField(max_length=255, blank=True, null=True)
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.product.name} Image - {self.caption or 'No Caption'}"


class Order(models.Model):
    # === Customer Info ===
    customer_name = models.CharField(max_length=100)
    email = models.EmailField(blank=True, null=True)
    phone = models.CharField(max_length=20)

    # === Address ===
    address = models.TextField(blank=True, null=True)
    address_line1 = models.CharField(max_length=255, blank=True, null=True)
    address_line2 = models.CharField(max_length=255, blank=True, null=True)
    city = models.CharField(max_length=100, blank=True, null=True)
    state = models.CharField(max_length=100, blank=True, null=True)
    postal_code = models.CharField(max_length=20, blank=True, null=True)
    country = models.CharField(max_length=2, blank=True, null=True)

    # === Financial & System Fields ===
    total = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    shipping_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    shipping_label = models.CharField(max_length=255, blank=True, null=True)

    delivery_method = models.CharField(
        max_length=20,
        choices=[
            ("deliver", "Deliver to Address"),
            ("pickup", "Store Pickup"),
        ],
        default="deliver"
    )
    store_location = models.CharField(max_length=100, blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    paid = models.BooleanField(default=False)
    payment_reference = models.CharField(max_length=100, blank=True, null=True)
    tracking_number = models.CharField(max_length=100, blank=True, null=True, unique=True)

    amount_paid = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    currency = models.CharField(max_length=10, default="NGN")

    STATUS_CHOICES = [
        ("pending", "Pending Payment"),
        ("processing", "Processing"),
        ("shipped", "Shipped"),
        ("out_for_delivery", "Out for Delivery"),
        ("delivered", "Delivered"),
        ("delayed", "Delayed"),
        ("cancelled", "Cancelled"),
    ]

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="processing")

    def __str__(self):
        return f"Order #{self.id} - {self.customer_name}"


    def get_tracking_identifier(self):
        return self.tracking_number or self.payment_reference or str(self.id)


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)
    price = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.quantity} x {self.product.name}"


class FAQ(models.Model):
    question = models.CharField(max_length=255)
    answer = models.TextField()
    # comma-separated keywords/phrases used by the rule-based matcher
    keywords = models.TextField(blank=True, help_text="Comma-separated trigger words/phrases")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "FAQ"
        verbose_name_plural = "FAQs"
        indexes = [
            models.Index(fields=['question']),
        ]

    def __str__(self):
        return self.question


class ChatSession(models.Model):
    """
    One session per visitor (client stores UUID). Using UUID prevents easy enumeration.
    Use ChatSession.memory to store ephemeral per-session context (not long-term PII).
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(default=timezone.now)
    last_active = models.DateTimeField(auto_now=True)
    memory = models.JSONField(default=dict, blank=True, help_text="Ephemeral session memory (JSON)")
    meta = models.JSONField(default=dict, blank=True, help_text="Optional metadata (utm, ip, user agent)")

    class Meta:
        ordering = ['-last_active']
        indexes = [
            models.Index(fields=['last_active']),
        ]

    def __str__(self):
        return str(self.id)


class ChatMessage(models.Model):
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
    metadata = models.JSONField(default=dict, blank=True, help_text="Optional per-message metadata")

    class Meta:
        indexes = [
            models.Index(fields=['session', 'created_at']),
        ]
        ordering = ['created_at']

    def __str__(self):
        return f'{self.sender} @ {self.created_at.isoformat()}'


class Lead(models.Model):
    """
    Stores opt-in contact info captured through the assistant.
    Keep PII minimal and get explicit permission before saving sensitive info.
    """
    name = models.CharField(max_length=120, blank=True)
    email = models.EmailField()
    phone = models.CharField(max_length=30, blank=True)
    message = models.TextField(blank=True)
    source = models.CharField(max_length=50, blank=True, help_text='eg. chat-widget')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['email']),
        ]

    def __str__(self):
        return f'{self.email} ({self.name})' if self.name else self.email


class Review(models.Model):
    product = models.ForeignKey("Product", related_name="reviews", on_delete=models.CASCADE)
    user_name = models.CharField(max_length=100)
    rating = models.PositiveSmallIntegerField(choices=[(i, str(i)) for i in range(1, 6)])
    comment = models.TextField()
    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"{self.user_name} - {self.product.name} ({self.rating}★)"
