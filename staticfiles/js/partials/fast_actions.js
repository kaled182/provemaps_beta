document.addEventListener('DOMContentLoaded', () => {
    const button = document.getElementById('manualActionsButton');
    const dropdown = document.getElementById('manualActionsDropdown');
    const arrow = document.getElementById('fastactionsMenuArrow');

    if (!button || !dropdown) {
        return;
    }

    button.addEventListener('click', (event) => {
        event.stopPropagation();
        const isHidden = dropdown.classList.contains('hidden');
        dropdown.classList.toggle('hidden', !isHidden);
        if (arrow) arrow.style.transform = isHidden ? 'rotate(180deg)' : 'rotate(0deg)';
    });

    document.addEventListener('click', (event) => {
        if (!dropdown.classList.contains('hidden') && !event.target.closest('#manualActionsMenu')) {
            dropdown.classList.add('hidden');
            if (arrow) arrow.style.transform = 'rotate(0deg)';
        }
    });

    document.addEventListener('keydown', (event) => {
        if (event.key === 'Escape' && !dropdown.classList.contains('hidden')) {
            dropdown.classList.add('hidden');
            if (arrow) arrow.style.transform = 'rotate(0deg)';
        }
    });
});
