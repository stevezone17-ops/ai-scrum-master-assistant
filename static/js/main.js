// Main Application JavaScript

document.addEventListener('DOMContentLoaded', () => {
    // Project Selector Switcher
    const projectSelector = document.getElementById('projectSelector');
    if (projectSelector) {
        projectSelector.addEventListener('change', (e) => {
            const selectedId = e.target.value;
            if (!selectedId || isNaN(selectedId)) return;

            const pathname = window.location.pathname;

            // 1. /projects/<id>/(sprints|backlog|tasks|kanban|team|standup|assistant|reports) or /projects/<id>
            const projectSubpageMatch = pathname.match(/^\/projects\/(\d+)(\/.*)?$/);
            if (projectSubpageMatch) {
                const subpath = projectSubpageMatch[2] || '';
                const newUrl = new URL(window.location.href);
                newUrl.pathname = `/projects/${selectedId}${subpath}`;
                window.location.href = newUrl.toString();
                return;
            }

            // 2. /dashboard or /
            if (pathname === '/dashboard' || pathname === '/') {
                const newUrl = new URL(window.location.href);
                newUrl.pathname = '/dashboard';
                newUrl.searchParams.set('project_id', selectedId);
                window.location.href = newUrl.toString();
                return;
            }

            // 3. /projects
            if (pathname === '/projects') {
                const newUrl = new URL(window.location.href);
                newUrl.pathname = '/projects';
                newUrl.searchParams.set('project_id', selectedId);
                window.location.href = newUrl.toString();
                return;
            }

            // 4. Fallback for any other pages
            const newUrl = new URL(window.location.href);
            newUrl.searchParams.set('project_id', selectedId);
            window.location.href = newUrl.toString();
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
