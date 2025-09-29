from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.views.decorators.http import require_POST
from .models import Product, Order, OrderItem
from .forms import CheckoutForm

# ---------- STATIC PAGES ----------
def about(request):
    return render(request, 'shop/about.html')

def home(request):
    return render(request, "shop/home.html")

from django.core.mail import send_mail
from django.shortcuts import render, redirect
from django.contrib import messages

def contact(request):
    if request.method == "POST":
        name = request.POST.get("name")
        email = request.POST.get("email")
        message = request.POST.get("message")

        subject = f"New message from {name}"
        body = f"Name: {name}\nEmail: {email}\n\nMessage:\n{message}"

        try:
            send_mail(
                subject,
                body,
                email,  # from
                ["luchi.addiction@outlook.com"],  # to
                fail_silently=False,
            )
            messages.success(request, "✅ Your message has been sent successfully!")
        except Exception as e:
            messages.error(request, f"❌ Error: {e}")

        return redirect("contact")

    return render(request, "shop/contact.html")

# ---------- PRODUCT VIEWS ----------
def wigs(request):
    wigs = Product.objects.filter(category="wigs")
    return render(request, "shop/wigs.html", {"products": wigs})

def laces(request):
    laces = Product.objects.filter(category="laces")
    return render(request, "shop/laces.html", {"products": laces})

def product_detail(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    return render(request, "shop/product_detail.html", {"product": product})

# ---------- CART VIEWS ----------
def add_to_cart(request, product_id):
    product = get_object_or_404(Product, pk=product_id)

    if product.stock < 1:
        messages.error(request, "❌ This product is out of stock.")
        return redirect("product_detail", id=product.id)

    # Get quantity from form (default = 1)
    try:
        quantity = int(request.POST.get("quantity", 1))
    except ValueError:
        quantity = 1

    if quantity < 1:
        quantity = 1

    if quantity > product.stock:
        messages.warning(request, f"⚠️ Only {product.stock} in stock.")
        return redirect("product_detail", id=product.id)

    cart = request.session.get("cart", {})

    print("DEBUG BEFORE:", cart)

    current_qty = cart.get(str(product.id), 0)
    new_qty = current_qty + quantity

    if new_qty > product.stock:
        messages.warning(request, f"⚠️ Not enough stock available. Max is {product.stock}.")
        return redirect("cart")

    cart[str(product.id)] = new_qty
    request.session["cart"] = cart
    request.session.modified = True  # force save

    print("DEBUG AFTER:", request.session["cart"])

    messages.success(request, f"✅ {product.name} (x{quantity}) added to cart.")
    return redirect("cart")


def cart(request):
    cart = request.session.get("cart", {})
    products = []
    total = 0
    updated_cart = cart.copy()

    for product_id, quantity in cart.items():
        product = get_object_or_404(Product, pk=product_id)

        # If cart quantity is higher than stock, adjust it
        if quantity > product.stock:
            quantity = product.stock
            updated_cart[str(product_id)] = quantity
            request.session["cart"] = updated_cart

        # Skip if stock is 0
        if product.stock == 0:
            continue

        subtotal = product.price * quantity
        total += subtotal

        products.append({
            "product": product,
            "quantity": quantity,
            "subtotal": subtotal
        })

    return render(request, "shop/cart.html", {
        "products": products,
        "total": total
    })


def remove_from_cart(request, product_id):
    cart = request.session.get("cart", {})

    if str(product_id) in cart:
        cart.pop(str(product_id))
        request.session["cart"] = cart
        messages.success(request, "🗑️ Item removed from cart.")
    else:
        messages.warning(request, "⚠️ Item not found in cart.")

    return redirect("cart")


@require_POST
def update_cart(request, product_id):
    cart = request.session.get("cart", {})
    try:
        quantity = int(request.POST.get("quantity", 1))
    except ValueError:
        quantity = 1

    if quantity > 0:
        cart[str(product_id)] = quantity
    else:
        cart.pop(str(product_id), None)

    request.session["cart"] = cart
    return redirect("cart")


# ---------- CHECKOUT & ORDERS ----------
def checkout(request):
    cart = request.session.get("cart", {})

    if not cart:
        return redirect("cart")  # if cart empty

    if request.method == "POST":
        form = CheckoutForm(request.POST)
        if form.is_valid():
            order = form.save(commit=False)

            # calculate total
            total = 0
            for pid, qty in cart.items():
                product = Product.objects.get(id=pid)
                total += product.price * qty
            order.total = total
            order.save()

            # save items
            for pid, qty in cart.items():
                product = Product.objects.get(id=pid)
                OrderItem.objects.create(
                    order=order,
                    product=product,
                    quantity=qty,
                    price=product.price
                )

            request.session["cart"] = {}  # clear cart
            return redirect("payment", order_id=order.id)
    else:
        form = CheckoutForm()

    return render(request, "shop/checkout.html", {"form": form})


def payment(request, order_id):
    order = get_object_or_404(Order, id=order_id)

    if request.method == "POST":
        # Later: integrate Paystack/Stripe/Flutterwave
        return redirect("order_success", order_id=order.id)

    return render(request, "shop/payment.html", {"order": order})

def order_success(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    return render(request, "shop/order_success.html", {"order": order})

from django.shortcuts import render
from .models import Product

def product_list(request):
    products_wigs = Product.objects.filter(category="wigs")
    products_laces = Product.objects.filter(category="laces")
    return render(request, "shop/products.html", {
        "products_wigs": products_wigs,
        "products_laces": products_laces,
    })


def home(request):
    new_arrivals = Product.objects.order_by("-created_at")[:6]
    best_sellers = Product.objects.filter(is_best_seller=True)[:6]
    return render(request, "shop/home.html", {
        "new_arrivals": new_arrivals,
        "best_sellers": best_sellers,
    })

from django.shortcuts import render

def shipping_view(request):
    return render(request, "shop/shipping.html")

def returns_view(request):
    return render(request, "shop/returns.html")

def faqs_view(request):
    return render(request, "shop/faqs.html")

def privacy_view(request):
    return render(request, "shop/privacy-policy.html")

# shop/views.py (add near other small views)
from django.shortcuts import redirect
from django.conf import settings

def set_currency(request):
    if request.method == "POST":
        code = request.POST.get("currency", "").upper()
    else:
        code = request.GET.get("currency", "").upper()

    supported = getattr(settings, "SUPPORTED_CURRENCIES", ["USD", "EUR", "NGN"])
    if code in supported:
        request.session["currency"] = 'NGN'

    return redirect(request.META.get("HTTP_REFERER", "/"))
