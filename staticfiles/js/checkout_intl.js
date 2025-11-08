
document.addEventListener("DOMContentLoaded", () => {
  const phoneInput = document.querySelector("#phone");
  window.intlTelInput(phoneInput, {
    initialCountry: "{{ detected_country|lower }}",
    separateDialCode: true
  });

  const citySelect = document.querySelector("#city");
  const postalInput = document.querySelector("#postal_code");
  const detectedCountry = "{{ detected_country }}";

  fetch(`/api/dhl/cities/?country=${detectedCountry}`)
    .then(res => res.json())
    .then(result => {
      const cities = result.cities || [];
      citySelect.innerHTML = `<option value="">Select City</option>`;
      cities.forEach(city => {
        const option = document.createElement("option");
        option.value = city.cityName;
        option.textContent = city.cityName;
        citySelect.appendChild(option);
      });
    })
    .catch(err => {
      console.error("City API error:", err);
      citySelect.innerHTML = `<option value="">Unable to load cities</option>`;
    });

  citySelect.addEventListener("change", function() {
    const selectedCity = this.value;
    if (!selectedCity) return;

    fetch(`/api/dhl/cities/?country=${detectedCountry}&city=${selectedCity}`)
      .then(res => res.json())
      .then(data => {
        if (data.cities && data.cities.length > 0) {
          const city = data.cities[0];
          postalInput.value = city.postalCode || "";
          if (!city.postalCode) postalInput.placeholder = "Enter postal code manually";
        }
      })
      .catch(err => {
        console.error("Postal lookup failed:", err);
        postalInput.value = "";
        postalInput.placeholder = "Enter postal code manually";
      });
  });
});
