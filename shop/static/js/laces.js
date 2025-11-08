document.addEventListener('DOMContentLoaded', function () {
  const filterForm = document.getElementById('filterForm');
  const productGrid = document.getElementById('productGrid');

  // ✅ FILTER CHECKBOX HANDLING
  document.querySelectorAll('.filter-checkbox').forEach(cb => {
    cb.addEventListener('change', () => {
      const params = new URLSearchParams(new FormData(filterForm));

      fetch(window.location.pathname + '?' + params, {
        headers: { 'X-Requested-With': 'XMLHttpRequest' }
      })
      .then(res => res.text())
      .then(html => {
        const parsed = new DOMParser().parseFromString(html, 'text/html');

        // Update products
        productGrid.innerHTML = parsed.querySelector('#productGrid').innerHTML;

        // Update pagination
        const newPagination = parsed.querySelector('.pagination');
        if (newPagination) {
          document.querySelector('.pagination').innerHTML = newPagination.innerHTML;
        }

        // Update URL so filters persist
        window.history.replaceState({}, '', window.location.pathname + '?' + params);

        // Optional live count update
        const newCount = parsed.querySelector('#productCount');
        if (newCount && document.querySelector('#productCount')) {
          document.querySelector('#productCount').textContent = newCount.textContent;
        }
      });
    });
  });

  // ✅ PAGINATION HANDLING
  document.addEventListener('click', e => {
    const link = e.target.closest('.pagination a');
    if (link) {
      e.preventDefault();
      const url = link.href;

      fetch(url, { headers: { 'X-Requested-With': 'XMLHttpRequest' } })
      .then(res => res.text())
      .then(html => {
        const parsed = new DOMParser().parseFromString(html, 'text/html');
        productGrid.innerHTML = parsed.querySelector('#productGrid').innerHTML;

        const newPagination = parsed.querySelector('.pagination');
        if (newPagination) {
          document.querySelector('.pagination').innerHTML = newPagination.innerHTML;
        }

        // Update URL (so user can refresh or go back)
        window.history.replaceState({}, '', url);
      });
    }
  });
});
