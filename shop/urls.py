from django.contrib import admin
from django.urls import path
from . import views
from django.views.generic import TemplateView
from django.urls import include, path

app_name = "shop"

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
    path("product/<int:product_id>/add-review/", views.add_review, name="add_review"),

    # Cart
    path("cart/", views.cart, name="cart"),
    path("cart/add/<int:product_id>/", views.add_to_cart, name="add_to_cart"),
    path("cart/remove/<int:product_id>/", views.remove_from_cart, name="remove_from_cart"),
    path("cart/update/<int:product_id>/", views.update_cart, name="update_cart"),

    # Checkout & orders
    path("checkout/", views.checkout, name="checkout"),
    path("payment/<int:order_id>/", views.payment, name="payment"),
    path("verify-payment/", views.verify_payment, name="verify_payment"),
    path("order-success/<int:order_id>/", views.order_success, name="order_success"),

     #customer care
    path("shipping/", views.shipping_view, name="shipping"),
    path("returns/", views.returns_view, name="returns"),
    path("faqs/", views.faqs_view, name="faqs"),
    path("privacy-policy/", views.privacy_view, name="privacy-policy"),
    
    # robots.txt
    path("robots.txt", TemplateView.as_view(template_name="robots.txt", content_type="text/plain")),

    path("set-currency/", views.set_currency, name="set_currency"),

    path("select-country/", views.select_country_view, name="select_country"),

    path("select-shipping/", views.select_shipping, name="select_shipping"),

    path("order-summary/<int:order_id>/", views.order_summary, name="order_summary"),

    path("set-country/<str:code>/", views.set_country_view, name="set_country_code"),  

    path("override-country/", views.override_country, name="override_country"),

    path("api/cities/", views.get_cities, name="get_cities"),

    path("api/local-shipping/", views.get_local_shipping, name="get_local_shipping"),

    path('assistant/', include('assistant.urls')),


]