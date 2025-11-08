
document.addEventListener("DOMContentLoaded", function() {
  const form = document.querySelector("form");
  const addressField = document.getElementById("address");
  if (!addressField) return;

  // Use existing delivery method radio buttons
  const deliverRadio = document.getElementById("deliver_option");
  const pickupRadio = document.getElementById("pickup_option");
  const storeSelector = document.getElementById("store-selector");

  // Cached field groups
  const addressGroup = addressField.closest("div");
  const cityGroup = document.getElementById("city")?.closest("div");
  const stateGroup = document.getElementById("state")?.closest("div");

  // Summary fields
  const shippingText = document.getElementById("shipping_text");
  const grandTotal = document.getElementById("grand_total");
  const subtotalText = document.getElementById("subtotal_text");
  const shippingInput = document.getElementById("shipping_price");
  const labelInput = document.getElementById("shipping_label");
  const subtotal = parseFloat("{{ subtotal|floatformat:2 }}");

  // === Radio Event Listeners ===
  deliverRadio.addEventListener("change", handleDeliveryChoice);
  pickupRadio.addEventListener("change", handleDeliveryChoice);

  function handleDeliveryChoice() {
    const method = document.querySelector("input[name='delivery_method']:checked").value;
    const requiredInputs = [addressField, document.getElementById("city"), document.getElementById("state")]
      .filter(Boolean)
      .map(el => el.querySelector ? el.querySelector("[required]") || el : el);

    if (method === "pickup") {
      [addressGroup, cityGroup, stateGroup].forEach(g => g && (g.style.display = "none"));
      requiredInputs.forEach(el => el.removeAttribute("required"));
      storeSelector.style.display = "block";
      shippingText.textContent = "Pickup – ₦0";
      grandTotal.textContent = `₦${subtotal.toLocaleString()}`;
      shippingInput.value = 0;
      labelInput.value = "Pickup – ₦0";
    } else {
      [addressGroup, cityGroup, stateGroup].forEach(g => g && (g.style.display = ""));
      requiredInputs.forEach(el => el.setAttribute("required", ""));
      storeSelector.style.display = "none";
      shippingText.textContent = "To be calculated";
      grandTotal.textContent = subtotalText.textContent;
      shippingInput.value = 0;
      labelInput.value = "";
    }
  }

  // Initialize on page load
  handleDeliveryChoice();

  // === Dynamic Shipping Calculation ===
  const stateField = document.getElementById("state");
  if (stateField) {
    stateField.addEventListener("change", async function() {
      const method = document.querySelector("input[name='delivery_method']:checked").value;
      if (method !== "deliver") return;
      const state = this.value;
      if (!state) {
        shippingText.textContent = "To be calculated";
        grandTotal.textContent = subtotalText.textContent;
        shippingInput.value = 0;
        labelInput.value = "";
        return;
      }
      try {
        const res = await fetch(`/api/get_local_shipping/?state=${encodeURIComponent(state)}`);
        const data = await res.json();
        if (data.error) {
          shippingText.textContent = "Shipping unavailable";
          return;
        }
        const price = parseFloat(data.price);
        const label = data.label;
        shippingText.textContent = `${label} – ₦${price.toLocaleString()}`;
        grandTotal.textContent = `₦${(subtotal + price).toLocaleString()}`;
        shippingInput.value = price;
        labelInput.value = label;
      } catch (err) {
        console.error("Shipping fetch failed:", err);
        shippingText.textContent = "Error fetching shipping rate";
      }
    });
  }
});



