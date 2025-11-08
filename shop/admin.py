from django.contrib import admin
from django.utils.html import format_html
from .models import Product, ProductImage, Review, Order, OrderItem

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

    list_display = ("id", "name", "category", "lace_type", "price", "stock", "is_best_seller", "thumb", "created_at")
    list_filter = ("category", "lace_type", "is_best_seller", "created_at")
    search_fields = ("name", "description")
    ordering = ("-id",)
    readonly_fields = ("created_at",)
    list_editable = ("is_best_seller",)
    list_per_page = 50

    def thumb(self, obj):
        if obj and getattr(obj, "image", None):
            return format_html(
                '<img src="{}" style="max-height:50px; border-radius:4px;" />',
                obj.image.url
            )
        return "—"
    thumb.short_description = "Image"


# ---- ProductImage admin ----
@admin.register(ProductImage)
class ProductImageAdmin(admin.ModelAdmin):
    list_display = ("id", "product", "image")
    list_filter = ("product",)
    search_fields = ("product__name",)


# ---- Review admin ----
@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ("id", "product", "user_name", "rating", "created_at")
    list_filter = ("rating", "created_at")
    search_fields = ("product__name", "user_name", "comment")


# ---- Orders ----
@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("id", "customer_name", "total", "status", "created_at", "paid")
    list_filter = ("status", "paid", "created_at")
    search_fields = ("customer_name", "email", "tracking_number")


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ("id", "order", "product", "quantity", "price")
    list_select_related = ("order", "product")
    search_fields = ("order__id", "product__name")
