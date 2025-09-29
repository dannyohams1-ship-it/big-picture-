from django.contrib import admin
from django.urls import path
from . import views
from django.views.generic import TemplateView

urlpatterns = [
    # Home & static pages
    path("", views.home, name="home"),
    path("about/", views.about, name="about"),
    path("contact/", views.contact, name="contact"),

    # Products
    path("products/", views.product_list, name="product_list"),
    path("products/wigs/", views.wigs, name="wigs"),
    path("products/laces/", views.laces, name="laces"),
    path("products/<int:product_id>/", views.product_detail, name="product_detail"),

    # Cart
    path("cart/", views.cart, name="cart"),
    path("cart/add/<int:product_id>/", views.add_to_cart, name="add_to_cart"),
    path("cart/remove/<int:product_id>/", views.remove_from_cart, name="remove_from_cart"),
    path("cart/update/<int:product_id>/", views.update_cart, name="update_cart"),

    # Checkout & orders
    path("checkout/", views.checkout, name="checkout"),
    path("payment/<int:order_id>/", views.payment, name="payment"),
    path("order-success/<int:order_id>/", views.order_success, name="order_success"),

     #customer care
    path("shipping/", views.shipping_view, name="shipping"),
    path("returns/", views.returns_view, name="returns"),
    path("faqs/", views.faqs_view, name="faqs"),
    path("privacy-policy/", views.privacy_view, name="privacy-policy"),

    path('admin/', admin.site.urls),

    # robots.txt
    path("robots.txt", TemplateView.as_view(template_name="robots.txt", content_type="text/plain")),

    path("set-currency/", views.set_currency, name="set_currency")

]