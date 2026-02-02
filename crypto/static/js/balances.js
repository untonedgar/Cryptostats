document.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll('.exchange-card').forEach(card => {
    const header = card.querySelector('.exchange-header');
    const list = card.querySelector('.coin-list');

    if (!header || !list) return;

    header.addEventListener('click', () => {
      list.classList.toggle('show');
    });
  });
});