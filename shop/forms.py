# shop/forms.py
from django import forms
from .models import Order
from .utils import NIGERIA_STATES

class BaseCheckoutForm(forms.ModelForm):
    DELIVERY_CHOICES = [
        ("deliver", "Deliver to Address"),
        ("pickup", "Store Pickup"),
    ]

    # Server-rendered radio (will show in template as {{ form.delivery_method }})
    delivery_method = forms.ChoiceField(
        choices=DELIVERY_CHOICES,
        widget=forms.RadioSelect(attrs={"class": "form-check-input"}),
        initial="deliver",
        required=True
    )

    def clean(self):
        cleaned = super().clean()
        method = cleaned.get("delivery_method", "deliver")

        # If user chose delivery, ensure address fields exist
        if method == "deliver":
            # For local we expect address, city, state (some forms use address or address_line1)
            if hasattr(self, "fields") and "address" in self.fields:
                if not cleaned.get("address"):
                    self.add_error("address", "Address is required for delivery.")
                if not cleaned.get("city"):
                    self.add_error("city", "City is required for delivery.")
                if not cleaned.get("state"):
                    self.add_error("state", "State is required for delivery.")
            # For international form using address_line1
            if "address_line1" in self.fields:
                if not cleaned.get("address_line1"):
                    self.add_error("address_line1", "Address line 1 is required for delivery.")
                if not cleaned.get("city"):
                    self.add_error("city", "City is required for delivery.")
                if not cleaned.get("postal_code"):
                    self.add_error("postal_code", "Postal code is required for delivery.")

        # If pickup, it's OK for address fields to be blank
        return cleaned


class LocalCheckoutForm(BaseCheckoutForm):
    address = forms.CharField(
        widget=forms.Textarea(attrs={
            "class": "form-control",
            "placeholder": "Delivery Address",
            "rows": 3
        }),
        required=False  # 👈 allow blank for pickup
    )
    city = forms.CharField(
        max_length=100,
        required=False,  # 👈 allow blank for pickup
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "City"})
    )
    state = forms.ChoiceField(
        choices=[(s, s) for s in NIGERIA_STATES],
        required=False,  # 👈 allow blank for pickup
        widget=forms.Select(attrs={"class": "form-select"})
    )
    country = forms.CharField(initial="NG", widget=forms.HiddenInput())

    # Optional: ensure a store is chosen for pickup
    store_location = forms.CharField(
        required=False,
        widget=forms.Select(
            choices=[
                ("", "-- Select Store --"),
                ("Lagos - Branch", "Lagos - Branch"),
                ("Port Harcourt - Branch", "Port Harcourt - Branch"),
            ],
            attrs={"class": "form-select"}
        )
    )

    class Meta:
        model = Order
        fields = [
            "delivery_method", "customer_name", "email", "phone",
            "address", "city", "state", "country", "store_location"
        ]
        widgets = {
            "customer_name": forms.TextInput(attrs={"class": "form-control", "placeholder": "Full Name"}),
            "email": forms.EmailInput(attrs={"class": "form-control", "placeholder": "Email"}),
            "phone": forms.TextInput(attrs={"class": "form-control", "placeholder": "Phone Number"}),
        }

    def clean(self):
        cleaned = super().clean()
        method = cleaned.get("delivery_method")

        if method == "pickup":
            # store_location required for pickup
            if not cleaned.get("store_location"):
                self.add_error("store_location", "Please select a pickup store.")
        return cleaned



class InternationalCheckoutForm(BaseCheckoutForm):
    address_line1 = forms.CharField(
        max_length=255,
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "Address Line 1"}),
        label="Address Line 1"
    )
    address_line2 = forms.CharField(
        max_length=255, required=False,
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "Address Line 2"}),
        label="Address Line 2"
    )
    city = forms.CharField(max_length=100, widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "City"}))
    state = forms.CharField(max_length=100, widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "State/Province"}))
    postal_code = forms.CharField(max_length=20, widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "Postal Code"}))
    country = forms.CharField(widget=forms.HiddenInput())

    class Meta:
        model = Order
        fields = ["delivery_method", "customer_name", "email", "phone",
                  "address_line1", "address_line2", "city", "state", "postal_code", "country"]
        widgets = {
            "customer_name": forms.TextInput(attrs={"class": "form-control", "placeholder": "Full Name"}),
            "email": forms.EmailInput(attrs={"class": "form-control", "placeholder": "Email Address"}),
            "phone": forms.TextInput(attrs={"class": "form-control", "placeholder": "Phone Number"}),
        }

class ContactForm(forms.Form):
    name = forms.CharField(max_length=100, widget=forms.TextInput(attrs={
        "class": "form-control", "placeholder": "Your Name"
    }))
    email = forms.EmailField(widget=forms.EmailInput(attrs={
        "class": "form-control", "placeholder": "Your Email"
    }))
    message = forms.CharField(widget=forms.Textarea(attrs={
        "class": "form-control", "placeholder": "Your Message", "rows": 3
    }))
    