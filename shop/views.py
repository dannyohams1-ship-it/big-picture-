# shop/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.views.decorators.http import require_POST
from django.conf import settings
from django.utils import timezone
from django.http import JsonResponse
from decimal import Decimal,InvalidOperation
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db.models import Prefetch
from .models import Product, ProductImage
from django.db.models import Avg, Q,Count
from django.core.paginator import Paginator
import requests
from .models import Product, Order, OrderItem
from .forms import LocalCheckoutForm, InternationalCheckoutForm
from .utils import get_currency_for_country
from shop.utils import calculate_local_shipping
from .utils import NIGERIA_STATES, get_country_name
from .models import Product
from .models import Product, Review
from django.http import HttpResponse

import json
from django.shortcuts import render, get_object_or_404
from django.utils.safestring import mark_safe
from django.core.serializers.json import DjangoJSONEncoder
from .models import Product


# ---------- STATIC PAGES ----------
def about(request):
    return render(request, 'shop/about.html')

def home(request):
    new_arrivals = Product.objects.order_by("-created_at")[:6]
    best_sellers = Product.objects.filter(is_best_seller=True)[:6]
    return render(request, "shop/home.html", {
        "new_arrivals": new_arrivals,
        "best_sellers": best_sellers,
    })

def contact(request):
    from django.core.mail import send_mail
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

        return redirect("shop:contact")

    return render(request, "shop/contact.html")



def wigs(request):
    # Base queryset — only wigs
    products = Product.objects.filter(category__iexact="wigs")

    # --- Filters ---
    lace_selected = request.GET.getlist("lace_type")
    if lace_selected:
        # Case-insensitive lace_type filtering
        filters = Q()
        for lace in lace_selected:
            filters |= Q(lace_type__iexact=lace)
        products = products.filter(filters)

    products = products.annotate(
    avg_rating=Avg("reviews__rating"),
    review_count=Count("reviews")

    )

    # --- Sorting ---
    sort_option = request.GET.get("sort")
    if sort_option == "price_asc":
        products = products.order_by("price")
    elif sort_option == "price_desc":
        products = products.order_by("-price")
    elif sort_option == "rating_desc":
        products = products.annotate(avg_rating=Avg("reviews__rating")).order_by("-avg_rating")
    elif sort_option == "rating_asc":
        products = products.annotate(avg_rating=Avg("reviews__rating")).order_by("avg_rating")
    elif sort_option == "new_arrivals":
        products = products.order_by("-created_at")

    # --- Pagination ---
    paginator = Paginator(products, 12)  
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    # --- Context ---
    context = {
        "products": page_obj.object_list,   
        "page_obj": page_obj,               
        "is_paginated": page_obj.has_other_pages(),
        "lace_selected": lace_selected,
        "product_count": products.count(),     
    }

    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        return render(request, "shop/includes/product_grid.html", context)

    return render(request, "shop/wigs.html", context)


def laces(request):
    lace_type = request.GET.get("type") 
    products = Product.objects.filter(category__iexact="laces")
    print("Laces count:", products.count()) 

    lace_selected = request.GET.getlist("lace_type")
    if lace_selected:
        # Case-insensitive lace_type filtering
        filters = Q()
        for lace in lace_selected:
            filters |= Q(lace_type__iexact=lace)
        products = products.filter(filters)

    products = products.annotate(
    avg_rating=Avg("reviews__rating"),
    review_count=Count("reviews")
    
    )

    # --- Sorting ---
    sort_option = request.GET.get("sort")
    if sort_option == "price_asc":
        products = products.order_by("price")
    elif sort_option == "price_desc":
        products = products.order_by("-price")
    elif sort_option == "rating_desc":
        products = products.annotate(avg_rating=Avg("reviews__rating")).order_by("-avg_rating")
    elif sort_option == "rating_asc":
        products = products.annotate(avg_rating=Avg("reviews__rating")).order_by("avg_rating")
    elif sort_option == "new_arrivals":
        products = products.order_by("-created_at")

    # --- Pagination ---
    paginator = Paginator(products, 12)  
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    # --- Context ---
    context = {
        "products": page_obj.object_list,   
        "page_obj": page_obj,               
        "is_paginated": page_obj.has_other_pages(),
        "lace_selected": lace_selected,
        "product_count": products.count(),     
    }

    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        return render(request, "shop/includes/product_grid.html", context)

    return render(request, "shop/laces.html", context)


def product_detail(request, product_id):
    # --- Main Product ---
    product = get_object_or_404(Product, id=product_id)

    # --- Related Products ---
    related_products = (
        Product.objects.filter(category=product.category)
        .exclude(id=product.id)
        .order_by("?")[:8]  # random for variety; use -created_at for chronological
    )

    # --- Variants ---
    variants = []
    variant_options = {}

    qs = getattr(product, "variants", None)
    if qs is not None:
        for v in qs.all():
            variant_data = {
                "id": v.id,
                "sku": getattr(v, "sku", ""),
                "price": str(getattr(v, "price", "0")),
                "sale_price": str(getattr(v, "sale_price", "")) if getattr(v, "sale_price", None) else None,
                "stock": getattr(v, "stock", 0),
            }

            # Option fields — adapt based on your variant model
            for field in ("length", "lace_type", "color", "cap_size", "density"):
                value = getattr(v, field, None)
                variant_data[field] = value
                if value:
                    variant_options.setdefault(field, set()).add(value)

            variants.append(variant_data)

    # --- Convert variant options to sorted lists ---
    variant_options = {k: sorted(list(v)) for k, v in variant_options.items()}

    # --- Context ---
    context = {
        "product": product,
        "related_products": related_products,
        "variants_json": mark_safe(json.dumps(variants, cls=DjangoJSONEncoder)),
        "variant_options": variant_options,
    }

    return render(request, "shop/product_detail.html", context)



def product_list(request):
    """
    Shows all product categories (collections) like Wigs & Laces.
    Uses the same products.html template.
    """
    categories = dict(Product.CATEGORY_CHOICES)

    context = {
        "categories": categories,
        "page_title": "Our Collections",
    }

    return render(request, "shop/products.html", context)


# ---------- CART VIEWS ----------
def add_to_cart(request, product_id):
    product = get_object_or_404(Product, pk=product_id)

    if product.stock < 1:
        messages.error(request, "❌ This product is out of stock.")
        return redirect("shop:product_detail", id=product.id)

    try:
        quantity = int(request.POST.get("quantity", 1))
    except ValueError:
        quantity = 1

    if quantity < 1:
        quantity = 1

    if quantity > product.stock:
        messages.warning(request, f"⚠️ Only {product.stock} in stock.")
        return redirect("shop:product_detail", id=product.id)

    cart = request.session.get("cart", {})
    current_qty = cart.get(str(product.id), 0)
    new_qty = current_qty + quantity

    if new_qty > product.stock:
        messages.warning(request, f"⚠️ Not enough stock available. Max is {product.stock}.")
        return redirect("cart")

    cart[str(product.id)] = new_qty
    request.session["cart"] = cart
    request.session.modified = True

    messages.success(request, f"✅ {product.name} (x{quantity}) added to cart.")
    return redirect("shop:cart")


def cart(request):
    cart = request.session.get("cart", {})
    products = []
    subtotal = 0
    updated_cart = cart.copy()

    for product_id, quantity in cart.items():
        product = get_object_or_404(Product, pk=product_id)

        if quantity > product.stock:
            quantity = product.stock
            updated_cart[str(product_id)] = quantity
            request.session["cart"] = updated_cart

        if product.stock == 0:
            continue

        item_subtotal = product.price * quantity
        subtotal += item_subtotal

        products.append({
            "product": product,
            "quantity": quantity,
            "subtotal": item_subtotal,
        })

    shipping = request.session.get("selected_shipping")
    shipping_price = shipping["price"] if shipping else 0
    grand_total = subtotal + shipping_price

    return render(request, "shop/cart.html", {
        "products": products,
        "total": subtotal,
        "shipping": shipping,
        "shipping_price": shipping_price,
        "grand_total": grand_total,
    })


def remove_from_cart(request, product_id):
    cart = request.session.get("cart", {})
    if str(product_id) in cart:
        cart.pop(str(product_id))
        request.session["cart"] = cart
        messages.success(request, "🗑️ Item removed from cart.")
    else:
        messages.warning(request, "⚠️ Item not found in cart.")
    return redirect("shop:cart")


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
    return redirect("shop:cart")


def checkout(request):
    detected_country = request.session.get("detected_country", "ZZ")
    detected_country_name = get_country_name(detected_country)
    cart = request.session.get("cart", {})

    if not cart:
        messages.warning(request, "Your cart is empty.")
        return redirect("shop:cart")

    # --- Calculate subtotal (Decimal) ---
    subtotal = Decimal("0.00")
    for pid, qty in cart.items():
        try:
            product = Product.objects.get(id=pid)
            subtotal += product.price * int(qty)
        except (Product.DoesNotExist, InvalidOperation, ValueError, TypeError):
            continue

    # --- Choose appropriate Django form ---
    form_class = LocalCheckoutForm if detected_country == "NG" else InternationalCheckoutForm

    if request.method == "POST":
        form = form_class(request.POST)
        if form.is_valid():
            address_data = form.cleaned_data

            # --- DELIVERY METHOD (from cleaned_data) ---
            delivery_method = address_data.get("delivery_method", request.POST.get("delivery_method", "deliver"))
            # store_location is not part of the ModelForm, so still read from POST
            store_location = request.POST.get("store_location", "").strip()

            # --- Calculate shipping safely ---
            shipping_price = Decimal("0.00")
            shipping_label = ""

            if detected_country == "NG":
                if delivery_method == "pickup":
                    # Store pickup — ₦0 shipping
                    shipping_price = Decimal("0.00")
                    shipping_label = f"Store Pickup — {store_location or 'Unspecified'}"
                else:
                    # Regular delivery — calculate via helper
                    state_for_shipping = address_data.get("state")
                    try:
                        result = calculate_local_shipping(state_for_shipping)
                        # calculate_local_shipping may return tuple (price, label) or a single value.
                        if isinstance(result, tuple) or isinstance(result, list):
                            price_val, label_val = result
                        else:
                            price_val, label_val = result, ""
                        # ensure Decimal
                        shipping_price = Decimal(str(price_val)) if price_val is not None else Decimal("0.00")
                        shipping_label = label_val or ""
                    except Exception as e:
                        # fallback safe option — no shipping or default
                        print("⚠️ Local shipping calc failed:", e)
                        shipping_price = Decimal("0.00")
                        shipping_label = ""
            else:
                # International: DHL lookup (unchanged, but robust)
                try:
                    payload = {
                        "customerDetails": {
                            "shipperDetails": {"postalCode": "100001", "countryCode": "NG"},
                            "receiverDetails": {
                                "postalCode": address_data.get("postal_code"),
                                "cityName": address_data.get("city"),
                                "countryCode": detected_country,
                            },
                        },
                        "accounts": [{"number": settings.DHL_ACCOUNT_NUMBER, "typeCode": "shipper"}],
                        "plannedShippingDateAndTime": timezone.now().strftime("%Y-%m-%dT%H:%M:%S GMT+01:00"),
                        "unitOfMeasurement": "metric",
                        "content": [{"weight": 2.5, "dimensions": {"length": 30, "width": 20, "height": 10}}],
                    }

                    headers = {
                        "DHL-API-Key": settings.DHL_API_KEY,
                        "Content-Type": "application/json",
                    }
                    response = requests.post(settings.DHL_RATE_URL, json=payload, headers=headers, timeout=30)
                    response.raise_for_status()
                    data = response.json()
                    products = data.get("products", [])
                    if products:
                        # defensive extraction
                        price_raw = products[0].get("totalPrice", [{}])[0].get("price")
                        shipping_price = Decimal(str(price_raw)) if price_raw is not None else Decimal("50.00")
                        shipping_label = products[0].get("productName") or "DHL Shipping"
                    else:
                        messages.warning(request, "Could not fetch DHL rate, using fallback $50.")
                        shipping_price = Decimal("50.00")
                        shipping_label = "DHL Fallback"
                except Exception as e:
                    print("⚠️ DHL API error:", e)
                    shipping_price = Decimal("50.00")
                    shipping_label = "DHL International Shipping"

            # --- Compute totals ---
            grand_total = subtotal + shipping_price

            # --- Create order: if pickup, don't persist delivery address text (optional) ---
            address_to_save = address_data.get("address") or address_data.get("address_line1") or ""
            if delivery_method == "pickup":
                # intentionally clear address fields for pickup if you prefer to keep DB tidy
                address_to_save = ""
                address_line1 = None
                address_line2 = None
                city_val = None
                state_val = None
                postal_code_val = None
            else:
                address_line1 = address_data.get("address_line1")
                address_line2 = address_data.get("address_line2")
                city_val = address_data.get("city")
                state_val = address_data.get("state")
                postal_code_val = address_data.get("postal_code")

            order_id = request.session.get("current_order_id")
            order = None

            if order_id:
               try:
                     order = Order.objects.get(id=order_id, paid=False)
               except Order.DoesNotExist:
                     order = None
                
            if not order:
                order = Order.objects.create(
                    customer_name=address_data.get("customer_name"),
                    email=address_data.get("email"),
                    phone=address_data.get("phone"),
                    address=address_to_save,
                    address_line1=address_line1,
                    address_line2=address_line2,
                    city=city_val,
                    state=state_val,
                    postal_code=postal_code_val,
                    country=address_data.get("country", detected_country),
                    total=grand_total,
                    shipping_fee=shipping_price,
                    shipping_label=shipping_label,
                    delivery_method=delivery_method,
                    store_location=store_location,
                )

                request.session["current_order_id"] = order.id

            else:
                 order.customer_name = address_data.get("customer_name")
                 order.email = address_data.get("email")
                 order.phone = address_data.get("phone")
                 order.address = address_to_save
                 order.address_line1 = address_line1
                 order.address_line2 = address_line2
                 order.city = city_val
                 order.state = state_val
                 order.postal_code = postal_code_val
                 order.country = address_data.get("country", detected_country)
                 order.total = grand_total
                 order.shipping_fee = shipping_price
                 order.shipping_label = shipping_label
                 order.delivery_method = delivery_method
                 order.store_location = store_location
                 order.save()


            # --- Create order items ---
            OrderItem.objects.filter(order=order).delete()
            for pid, qty in cart.items():
                product = get_object_or_404(Product, id=pid)
                OrderItem.objects.create(
                    order=order,
                    product=product,
                    quantity=qty,
                    price=product.price,
                )

            # --- Clear cart and store summary in session ---
            
            request.session["order_summary"] = {
                "order_id": order.id,
                "subtotal": str(subtotal),
                "shipping_price": str(shipping_price),
                "grand_total": str(grand_total),
                "shipping_label": shipping_label,
                "delivery_method": delivery_method,
                "store_location": store_location,
            }

            request.session.modified = True


            return redirect("shop:order_summary", order_id=order.id)
    else:
        initial_data = {"country": detected_country} if detected_country != "NG" else {}
        form = form_class(initial=initial_data)

    return render(
        request,
        "shop/checkout.html",
        {
            "form": form,
            "detected_country": detected_country,
            "detected_country_name": detected_country_name,
            "nigeria_states": NIGERIA_STATES,
            "subtotal": subtotal,
        },
    )

def add_review(request, product_id):
    product = get_object_or_404(Product, id=product_id)

    if request.method == "POST":
        user_name = request.POST.get("user_name")
        rating = request.POST.get("rating")
        comment = request.POST.get("comment")

        if not (user_name and rating and comment):
            messages.error(request, "All fields are required.")
            return redirect("shop:product_detail", product.id)

        Review.objects.create(
            product=product,
            user_name=user_name,
            rating=rating,
            comment=comment
        )
        messages.success(request, "Thank you for your review!")
        return redirect("shop:product_detail", product.id)

    return redirect("shop:product_detail", product.id)

def select_shipping(request):
    """
    Step 2: Select DHL shipping (only for international orders).
    Local orders skip this and go straight to the order summary.
    """
    detected_country = request.session.get("detected_country", "ZZ")
    shipping_address = request.session.get("shipping_address")
    cart = request.session.get("cart", {})

    if not shipping_address:
        return redirect("checkout")

    # --- Always compute subtotal early ---
    subtotal = Decimal("0.00")
    for pid, qty in cart.items():
        product = get_object_or_404(Product, id=pid)
        subtotal += product.price * qty

    # --- Local (Nigeria) customers: skip this step ---
    if detected_country == "NG":
        return redirect("shop:order_summary")

    # --- DHL Rate Fetch for International Customers ---
    shipping_options = []
    try:
        payload = {
            "customerDetails": {
                "shipperDetails": {"postalCode": "100001", "countryCode": "NG"},
                "receiverDetails": {
                    "postalCode": shipping_address.get("postal_code"),
                    "cityName": shipping_address.get("city"),
                    "countryCode": detected_country,
                },
            },
            "accounts": [{"number": settings.DHL_ACCOUNT_NUMBER, "typeCode": "shipper"}],
            "plannedShippingDateAndTime": timezone.now().strftime("%Y-%m-%dT%H:%M:%S GMT+01:00"),
            "unitOfMeasurement": "metric",
            "content": [{"weight": 2.5, "dimensions": {"length": 30, "width": 20, "height": 10}}],
        }

        headers = {"DHL-API-Key": settings.DHL_API_KEY, "Content-Type": "application/json"}
        response = requests.post(settings.DHL_RATE_URL, json=payload, headers=headers, timeout=30)
        response.raise_for_status()
        data = response.json()

        for product in data.get("products", []):
            price = Decimal(product["totalPrice"][0]["price"])
            shipping_options.append({
                "code": product["productCode"],
                "label": product["productName"],
                "price": price,
            })
    except Exception as e:
        print("⚠️ DHL API error:", e)
        messages.error(request, "Unable to fetch DHL international rates at this time.")
        return redirect("shop:checkout")

    # --- Handle POST: store chosen DHL shipping option ---
    if request.method == "POST":
        selected_code = request.POST.get("shipping_option")
        selected = next((opt for opt in shipping_options if opt["code"] == selected_code), None)

        if selected:
            request.session["selected_shipping"] = selected
            return redirect("shop:order_summary")

        messages.error(request, "Please select a valid shipping option.")

    return render(request, "shop/select_shipping.html", {
        "shipping_options": shipping_options,
        "detected_country": detected_country,
        "shipping_address": shipping_address,
        "subtotal": subtotal,
    })

def get_local_shipping(request):
    state = request.GET.get("state")
    if not state:
        return JsonResponse({"error": "Missing state"}, status=400)
    price, label = calculate_local_shipping(state)
    return JsonResponse({"price": price, "label": label})

def order_summary(request, order_id):
    if str(request.session.get("current_order_id")) != str(order_id):
        messages.warning(request, "Session expired or invalid order. Please start checkout again.")
        return redirect("shop:checkout")
    
    
    order = get_object_or_404(Order, id=order_id)
    items = OrderItem.objects.filter(order=order)

    summary = request.session.get("order_summary", {})

    # Defaults
    shipping_label = order.shipping_label if getattr(order, "shipping_label", None) else ""
    delivery_method = getattr(order, "delivery_method", None)
    store_location = getattr(order, "store_location", None)

    # Try to read numeric values from session first (they were stored as strings)
    subtotal = None
    shipping = None
    grand_total = None

    if summary:
        # Parse values safely from session (they may be strings)
        try:
            subtotal = Decimal(summary.get("subtotal")) if summary.get("subtotal") is not None else None
        except Exception:
            subtotal = None

        try:
            shipping = Decimal(summary.get("shipping_price")) if summary.get("shipping_price") is not None else None
        except Exception:
            shipping = None

        try:
            grand_total = Decimal(summary.get("grand_total")) if summary.get("grand_total") is not None else None
        except Exception:
            grand_total = None

        # override labels & delivery info if present in session
        shipping_label = summary.get("shipping_label") or shipping_label
        delivery_method = summary.get("delivery_method") or delivery_method
        store_location = summary.get("store_location") or store_location

    # If any value is still None, compute fallbacks from DB
    if subtotal is None:
        subtotal = sum((item.price * item.quantity) for item in items) or Decimal("0.00")

    if shipping is None:
        # Prefer explicit shipping_fee on order if available, else compute from order.total - subtotal
        shipping = getattr(order, "shipping_fee", None)
        if shipping is None:
            try:
                shipping = (order.total - subtotal) if order.total is not None else Decimal("0.00")
            except Exception:
                shipping = Decimal("0.00")

    if grand_total is None:
        # Prefer order.total if set, otherwise subtotal + shipping
        grand_total = getattr(order, "total", None) or (subtotal + shipping)

    # Ensure types are Decimal for template logic/formatting
    try:
        subtotal = Decimal(subtotal)
    except Exception:
        subtotal = Decimal("0.00")
    try:
        shipping = Decimal(shipping)
    except Exception:
        shipping = Decimal("0.00")
    try:
        grand_total = Decimal(grand_total)
    except Exception:
        grand_total = subtotal + shipping

    is_pickup = (str(delivery_method).lower() == "pickup") or (store_location and shipping == Decimal("0.00"))

    return render(request, "shop/order_summary.html", {
        "order": order,
        "items": items,
        "subtotal": subtotal,
        "shipping": shipping,
        "grand_total": grand_total,
        "shipping_label": shipping_label,
        "delivery_method": delivery_method,
        "store_location": store_location,
        "is_pickup": is_pickup,
    })


from decouple import config

def payment(request, order_id):
    """
    Step 3: Payment gateway selection and initialization.
    Handles Paystack for NG and Stripe for other countries.
    """

    order = get_object_or_404(Order, id=order_id)
    detected_country = order.country
    currency = "NGN" if detected_country == "NG" else "USD"  # Default fallback for others

    # 🔒 Load keys securely (from .env)
    paystack_public_key = config("PAYSTACK_PUBLIC_KEY")
    paystack_secret_key = config("PAYSTACK_SECRET_KEY")
    paystack_base_url = config("PAYSTACK_BASE_URL", default="https://api.paystack.co")

    # 🧠 Determine gateway and redirect
    if request.method == "POST":
        if detected_country == "NG":
            # Redirect to Paystack payment page (test or live)
            return redirect("shop:paystack_payment", order_id=order.id)
        else:
            # Redirect to Stripe for non-NG countries
            return redirect("shop:stripe_payment", order_id=order.id)

    # 💳 Render payment template
    return render(
        request,
        "shop/payment.html",
        {
            "order": order,
            "currency": currency,
            "PAYSTACK_PUBLIC_KEY": paystack_public_key,
        },
    )


def order_success(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    return render(request, "shop/order_success.html", {"order": order})



def verify_payment(request):
    reference = request.GET.get("reference")
    order_id = request.GET.get("order_id")

    if not reference or not order_id:
        return HttpResponse("Missing reference or order ID", status=400)

    order = get_object_or_404(Order, id=order_id)

    headers = {"Authorization": f"Bearer {settings.PAYSTACK_SECRET_KEY}"}
    url = f"{settings.PAYSTACK_BASE_URL}/transaction/verify/{reference}"

    try:
        res = requests.get(url, headers=headers)
        result = res.json()
    except Exception as e:
        return HttpResponse(f"Error contacting Paystack: {str(e)}", status=500)

    if result.get("data") and result["data"]["status"] == "success":
        order.paid = True
        order.payment_reference = reference
        order.amount_paid = result["data"]["amount"] / 100
        order.currency = result["data"]["currency"]
        order.save()

        request.session["cart"] = {}
        request.session["order_summary"] = {}
        request.session["current_order_id"] = None
        request.session.modified = True

        return redirect("shop:order_success", order_id=order.id)
    else:
        return HttpResponse("Payment verification failed or was declined", status=400)
    
# ---------- POLICY PAGES ----------
def shipping_view(request):
    return render(request, "shop/shipping.html")

def returns_view(request):
    return render(request, "shop/returns.html")

def faqs_view(request):
    return render(request, "shop/faqs.html")

def privacy_view(request):
    return render(request, "shop/privacy-policy.html")


# ---------- COUNTRY & CURRENCY ----------
def set_currency(request):
    currency = request.GET.get("currency")
    if currency in settings.SUPPORTED_CURRENCIES:
        request.session["currency"] = currency
    return redirect(request.META.get("HTTP_REFERER", "/"))


def select_country_view(request):
    dhl_list = getattr(settings, "DHL_SUPPORTED_COUNTRIES", [])
    country_choices = [(c, c) for c in dhl_list]

    if request.method == "POST":
        chosen = request.POST.get("country")
        if chosen:
            return set_country_view(request, chosen)

    return render(request, "shop/select_country.html", {
        "country_choices": country_choices,
        "detected_country": request.session.get("detected_country", "ZZ"),
    })


def set_country_view(request, code=None):
    if request.method == "POST":
        code = request.POST.get("country", code)
    if not code:
        return redirect(request.META.get("HTTP_REFERER", "/"))

    code = code.upper()
    request.session["detected_country"] = code
    request.session["country_source"] = "manual"
    request.session["country_timestamp"] = timezone.now().isoformat()
    request.session["currency"] = get_currency_for_country(code)

    import json
    referer = request.META.get("HTTP_REFERER", "/")
    response = redirect(referer)
    response.set_cookie(
        settings.COUNTRY_COOKIE_NAME,
        json.dumps({"country": code, "source": "manual", "ts": request.session["country_timestamp"]}),
        max_age=settings.COUNTRY_COOKIE_AGE,
        httponly=False,
        samesite="Lax",
    )
    return response


def override_country(request):
    detected_country = request.session.get("detected_country", "ZZ")

    if request.method == "POST":
        new_country = request.POST.get("country")
        if new_country:
            request.session["detected_country"] = new_country
            request.session["manual_override"] = True
            return redirect("shop:checkout")

    return render(request, "shop/override_country.html", {
        "country_choices": settings.COUNTRY_CHOICES,
        "detected_country": detected_country,
    })


def get_cities(request):
    country = request.GET.get("country")
    city_name = request.GET.get("city")

    if not country:
        return JsonResponse({"error": "Country is required"}, status=400)

    url = "https://wft-geo-db.p.rapidapi.com/v1/geo/cities"
    headers = {
        "X-RapidAPI-Key": str(settings.RAPIDAPI_KEY).strip(),
        "X-RapidAPI-Host": "wft-geo-db.p.rapidapi.com",
        "Accept": "application/json"
    }
    params = {"countryIds": country, "limit": 5}
    if city_name:
        params["namePrefix"] = city_name
        params["limit"] = 1

    try:
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        data = response.json()
        return JsonResponse(data)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

