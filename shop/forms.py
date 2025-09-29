
from django import forms
from .models import Order


from django import forms
from .models import Order

class CheckoutForm(forms.ModelForm):
    class Meta:
        model = Order
        fields = ["customer_name", "email", "phone", "address"]

        widgets = {
            "customer_name": forms.TextInput(attrs={"class": "form-control", "placeholder": "Full Name"}),
            "email": forms.EmailInput(attrs={"class": "form-control", "placeholder": "Email"}),
            "phone": forms.TextInput(attrs={"class": "form-control", "placeholder": "Phone Number"}),
            "address": forms.Textarea(attrs={"class": "form-control", "placeholder": "Delivery Address", "rows": 3}),
        }

from django import forms

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
    