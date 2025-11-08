
function scrollNewArrivals(direction) {
  const container = document.querySelector('.new-scroll');
  const cardWidth = container.querySelector('.new-card').offsetWidth + 16; // card + gap
  container.scrollBy({
    left: direction * cardWidth,
    behavior: 'smooth'
  });
}
