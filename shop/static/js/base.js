
function switchImage(el, url) {
  let wrapper = el.closest(".product-image-wrapper");
  let mainImg = wrapper.querySelector(".main-img");

  // Change image
  mainImg.src = url;

  // Update active thumbnail
  wrapper.querySelectorAll(".variant-thumb").forEach(t => t.classList.remove("active"));
  el.classList.add("active");
}
