document.addEventListener('DOMContentLoaded', function () {
  // gallery thumbnail swap
  document.querySelectorAll('.thumb-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      const src = btn.dataset.src;
      const hero = document.getElementById('hero-img');
      if (hero && src) hero.src = src;
    });
  });

  // variant pills & client-side variant resolution
  const variantsDataScript = document.getElementById('variants-data');
  let variants = [];
  if (variantsDataScript) {
    try { variants = JSON.parse(variantsDataScript.textContent); } catch (e) { variants = []; }
  }

  const selected = {};
  document.querySelectorAll('.variant-pill').forEach(pill => {
    pill.addEventListener('click', () => {
      const opt = pill.dataset.opt;
      const value = pill.dataset.value;
      // toggle active
      document.querySelectorAll(`.variant-pill[data-opt="${opt}"]`).forEach(b => b.classList.remove('active'));
      pill.classList.add('active');
      selected[opt] = value;
      resolveVariant();
    });
  });

  function resolveVariant() {
    // find variant with all selected options matching
    const v = variants.find(variant => {
      return Object.keys(selected).every(k => {
        // variant fields may be strings; compare loosely
        return String(variant[k]) === String(selected[k]);
      });
    });
    const priceEl = document.getElementById('price-display');
    const compareEl = document.getElementById('compare-price');
    const meta = document.getElementById('variant-meta');
    const variantInput = document.getElementById('variant_id');
    const addBtn = document.getElementById('add-to-cart-btn');

    if (v) {
      variantInput.value = v.id;
      if (v.price) priceEl.textContent = '₦' + Number(v.price).toLocaleString();
      if (v.sale_price) { compareEl.style.display = 'block'; compareEl.textContent = 'Was ₦' + Number(v.sale_price).toLocaleString(); }
      else compareEl.style.display = 'none';
      meta.textContent = v.sku ? `SKU: ${v.sku}` : '';
      if (v.stock <= 0) { addBtn.disabled = true; meta.textContent += ' • Out of stock'; }
      else addBtn.disabled = false;
    } else {
      variantInput.value = '';
      // leave price as-is (server-rendered)
      compareEl.style.display = 'none';
      meta.textContent = 'Please select product options';
      addBtn.disabled = true;
    }
  }

  // Ensure Add-to-Cart gets validated client-side for missing variant
  const addForm = document.getElementById('add-to-cart-form');
  if (addForm) {
    addForm.addEventListener('submit', function (e) {
      const variantField = document.getElementById('variant_id');
      if (variants.length > 0 && (!variantField || !variantField.value)) {
        e.preventDefault();
        alert('Please select all product options before adding to cart.');
        return false;
      }
      // server will do authoritative validation
    });
  }

  // sticky CTA wiring
  const stickyAdd = document.getElementById('sticky-add');
  if (stickyAdd) {
    stickyAdd.addEventListener('click', () => {
      const addBtn = document.getElementById('add-to-cart-btn');
      if (addBtn) addBtn.click();
    });
  }
});


  document.addEventListener("DOMContentLoaded", function () {
    const carousel = document.getElementById("storyCarousel");
    const storyText = document.getElementById("storyText");

    if (carousel && storyText) {
      carousel.addEventListener("slid.bs.carousel", function (event) {
        const activeItem = carousel.querySelector(".carousel-item.active");
        const newStory = activeItem?.dataset.description?.trim();
        if (newStory) storyText.textContent = newStory;
      });
    }
  });
