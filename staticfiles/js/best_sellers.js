
function scrollBestSellers(direction) {
  const container = document.querySelector('.best-sellers-scroll');
  const cardWidth = container.querySelector('.product-card').offsetWidth + 24; // card + gap
  container.scrollBy({
    left: direction * cardWidth,
    behavior: 'smooth'
  });
}
