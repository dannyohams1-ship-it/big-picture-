
  // Sync mini carousel click → open modal at same slide
  document.querySelectorAll(".testimonial-img").forEach((img, index) => {
    img.addEventListener("click", function () {
      let modal = new bootstrap.Modal(document.getElementById("testimonialModal"));
      modal.show();

      let modalCarousel = bootstrap.Carousel.getOrCreateInstance(document.getElementById("testimonialModalCarousel"));
      modalCarousel.to(index);
    });
  });

  // Pause/resume on hold (both carousels)
  function addPauseOnHold(carouselId) {
    let carouselEl = document.querySelector(carouselId);
    let carouselInstance = bootstrap.Carousel.getOrCreateInstance(carouselEl);

    let pressTimer;
    carouselEl.addEventListener("mousedown", () => {
      pressTimer = setTimeout(() => carouselInstance.pause(), 200);
    });
    carouselEl.addEventListener("mouseup", () => {
      clearTimeout(pressTimer);
      carouselInstance.cycle();
    });

    // For touch devices
    carouselEl.addEventListener("touchstart", () => {
      pressTimer = setTimeout(() => carouselInstance.pause(), 200);
    });
    carouselEl.addEventListener("touchend", () => {
      clearTimeout(pressTimer);
      carouselInstance.cycle();
    });
  }

  addPauseOnHold("#testimonialCarousel");
  addPauseOnHold("#testimonialModalCarousel");
