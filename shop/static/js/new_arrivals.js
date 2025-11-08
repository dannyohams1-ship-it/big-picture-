
function scrollNewArrivals(direction) {
  const container = document.querySelector('.new-scroll');
  const cardWidth = container.querySelector('.new-card').offsetWidth + 16; // card + gap
  container.scrollBy({
    left: direction * cardWidth,
    behavior: 'smooth'
  });
}
// ===============================
// New Arrivals – Scroll Logic
// Supports desktop arrows + mobile carousel
// ===============================

function scrollNewArrivals(direction) {
    const container = document.querySelector('.new-scroll');
    if (!container) return;

    const card = container.querySelector('.new-card');
    if (!card) return;

    // Calculate scroll distance dynamically
    const cardStyles = window.getComputedStyle(card);
    const gap = parseInt(cardStyles.marginRight) || 16;
    const cardWidth = card.offsetWidth + gap;

    container.scrollBy({
        left: direction * cardWidth,
        behavior: 'smooth'
    });
}

// ===============================
// Keyboard arrow support
// ===============================

document.addEventListener("keydown", (event) => {
    const container = document.querySelector('.new-scroll');
    if (!container) return;

    // Only scroll when the section is visible on screen
    const rect = container.getBoundingClientRect();
    const inView = rect.top < window.innerHeight && rect.bottom > 0;
    if (!inView) return;

    if (event.key === "ArrowRight") {
        scrollNewArrivals(1);
    } else if (event.key === "ArrowLeft") {
        scrollNewArrivals(-1);
    }
});

// ===============================
// Improve mobile swipe momentum
// ===============================

const newScrollContainer = document.querySelector('.new-scroll');
if (newScrollContainer) {
    let isDown = false;
    let startX;
    let scrollLeft;

    newScrollContainer.addEventListener('mousedown', (e) => {
        isDown = true;
        newScrollContainer.classList.add('active');
        startX = e.pageX - newScrollContainer.offsetLeft;
        scrollLeft = newScrollContainer.scrollLeft;
    });

    newScrollContainer.addEventListener('mouseleave', () => {
        isDown = false;
        newScrollContainer.classList.remove('active');
    });

    newScrollContainer.addEventListener('mouseup', () => {
        isDown = false;
        newScrollContainer.classList.remove('active');
    });

    newScrollContainer.addEventListener('mousemove', (e) => {
        if (!isDown) return;
        e.preventDefault();
        const x = e.pageX - newScrollContainer.offsetLeft;
        const walk = (x - startX) * 1.2; // drag sensitivity
        newScrollContainer.scrollLeft = scrollLeft - walk;
    });
}

// ===============================
// Optional: Auto-hide arrows when not scrollable
// ===============================

function updateArrowVisibility() {
    const container = document.querySelector('.new-scroll');
    if (!container) return;

    const leftArrow = document.querySelector('.scroll-btn.left');
    const rightArrow = document.querySelector('.scroll-btn.right');
    if (!leftArrow || !rightArrow) return;

    const maxScroll = container.scrollWidth - container.clientWidth;

    leftArrow.style.display = container.scrollLeft <= 5 ? "none" : "block";
    rightArrow.style.display = container.scrollLeft >= maxScroll - 5 ? "none" : "block";
}

document.addEventListener("DOMContentLoaded", updateArrowVisibility);
window.addEventListener("resize", updateArrowVisibility);

const containerScroll = document.querySelector('.new-scroll');
if (containerScroll) {
    containerScroll.addEventListener("scroll", updateArrowVisibility);
}
