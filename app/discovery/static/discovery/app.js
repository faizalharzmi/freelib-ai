document.querySelectorAll('[data-search-form]').forEach(form => {
  form.addEventListener('submit', () => {
    const button = form.querySelector('button[type="submit"]');
    if (button && form.reportValidity()) {
      button.disabled = true;
      button.textContent = 'Searching live catalogs…';
    }
  });
});
