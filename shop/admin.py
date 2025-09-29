from django.contrib import admin
from django.utils.html import format_html
from .models import Product, ProductImage, Order, OrderItem


# ---- Inline for extra product images ----
class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1
    fields = ("image", "preview")
    readonly_fields = ("preview",)

    def preview(self, obj):
        if obj and getattr(obj, "image", None):
            return format_html(
                '<img src="{}" style="max-height:100px; border-radius:6px;" />',
                obj.image.url
            )
        return "—"
    preview.short_description = "Preview"


# ---- Product admin ----
@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    inlines = [ProductImageInline]

    list_display = ("name", "category", "price", "stock", "is_best_seller", "thumb")
    list_filter = ("category", "is_best_seller")
    search_fields = ("name", "description")
    ordering = ("-id",)

    # ✅ makes it editable directly in list view
    list_editable = ("is_best_seller",)

    def thumb(self, obj):
        if obj and getattr(obj, "image", None):
            return format_html(
                '<img src="{}" style="max-height:50px; border-radius:4px;" />',
                obj.image.url
            )
        return "—"
    thumb.short_description = "Image"


# ---- Orders ----
@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("id", "customer_name", "total", "created_at")
    search_fields = ("id", "customer_name", "email")


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ("order", "product", "quantity", "price")
    list_select_related = ("order", "product")
