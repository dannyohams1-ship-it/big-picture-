document.addEventListener("DOMContentLoaded", function () {
  const paystackButton = document.getElementById("paystackButton");
  const paymentForm = document.getElementById("paymentForm");

  if (!paystackButton || !paymentForm) return;

  paystackButton.addEventListener("click", function () {
    const email = document.getElementById("email").value.trim();
    const publicKey = paymentForm.dataset.publicKey;
    const orderId = paymentForm.dataset.orderId;
    const currency = paymentForm.dataset.currency || "NGN";
    const amount = parseFloat(paymentForm.dataset.total) * 100; // Convert to lowest currency unit
    const reference =
      "ORDER_" + orderId + "_" + Math.floor(Math.random() * 1000000000 + 1);

    if (!email) {
      alert("Please enter your email address.");
      return;
    }

    let handler = PaystackPop.setup({
      key: publicKey,
      email: email,
      amount: amount,
      currency: currency,
      ref: reference,
      callback: function (response) {
        // Redirect to backend verification route
        window.location.href =
          `/verify-payment/?reference=${response.reference}&order_id=${orderId}`;
      },
      onClose: function () {
        alert("Payment process was cancelled.");
      },
    });

    handler.openIframe();
  });
});
