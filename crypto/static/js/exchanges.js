// Toggle для списка монет
document.addEventListener('DOMContentLoaded', function() {
    document.querySelectorAll('.exchange-header').forEach(header => {
        header.addEventListener('click', () => {
            const list = header.nextElementSibling;
            list.classList.toggle('show');
        });
    });
});

document.querySelectorAll('.exchange-card').forEach(card => {
    const header = card.querySelector('.exchange-header');
    const list = card.querySelector('.coin-list');

    if (!header || !list) return;

    header.addEventListener('click', () => {
        list.classList.toggle('show');
    });
});