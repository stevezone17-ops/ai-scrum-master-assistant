// Main Application JavaScript

document.addEventListener('DOMContentLoaded', () => {
    // Project Selector Switcher
    const projectSelector = document.getElementById('projectSelector');
    if (projectSelector) {
        projectSelector.addEventListener('change', (e) => {
            const selectedId = e.target.value;
            if (selectedId) {
                const currentUrl = new URL(window.location.href);
                currentUrl.searchParams.set('project_id', selectedId);
                window.location.href = currentUrl.toString();
            }
        });
    }
});

// Modal Utilities
function openModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.classList.add('show');
    }
}

function closeModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.classList.remove('show');
    }
}

// Close modal when clicking on overlay background
window.onclick = function(event) {
    if (event.target.classList.contains('modal')) {
        event.target.classList.remove('show');
    }
}
