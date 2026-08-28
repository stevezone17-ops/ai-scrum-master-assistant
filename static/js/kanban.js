// Interactive Kanban Board Drag & Drop with Instant API Updates and RBAC Rollback

document.addEventListener('DOMContentLoaded', () => {
    const cards = document.querySelectorAll('.task-card[draggable="true"]');
    const columns = document.querySelectorAll('.kanban-column');

    let draggedCard = null;
    let sourceColumn = null;

    cards.forEach(card => {
        card.addEventListener('dragstart', dragStart);
        card.addEventListener('dragend', dragEnd);
    });

    columns.forEach(column => {
        column.addEventListener('dragover', dragOver);
        column.addEventListener('dragenter', dragEnter);
        column.addEventListener('dragleave', dragLeave);
        column.addEventListener('drop', dragDrop);
    });

    function dragStart(e) {
        draggedCard = this;
        sourceColumn = this.closest('.kanban-column');
        this.classList.add('dragging');
        e.dataTransfer.setData('text/plain', this.dataset.taskId);
        e.dataTransfer.effectAllowed = 'move';
    }

    function dragEnd() {
        this.classList.remove('dragging');
        columns.forEach(col => col.classList.remove('drag-over'));
        draggedCard = null;
        sourceColumn = null;
    }

    function dragOver(e) {
        e.preventDefault();
        e.dataTransfer.dropEffect = 'move';
    }

    function dragEnter(e) {
        e.preventDefault();
        this.classList.add('drag-over');
    }

    function dragLeave(e) {
        // Prevent flashing when dragging over child elements
        if (!this.contains(e.relatedTarget)) {
            this.classList.remove('drag-over');
        }
    }

    function dragDrop(e) {
        e.preventDefault();
        this.classList.remove('drag-over');

        if (!draggedCard) return;

        const targetColumn = this;
        const targetContainer = targetColumn.querySelector('.kanban-cards-container');
        const newStatus = targetColumn.dataset.status;
        const oldStatus = sourceColumn ? sourceColumn.dataset.status : null;
        const taskId = draggedCard.dataset.taskId;

        if (newStatus === oldStatus) return;

        // Save original container for rollback if request fails
        const originalContainer = sourceColumn ? sourceColumn.querySelector('.kanban-cards-container') : null;

        // Move card DOM element to target column container
        moveCardDOM(draggedCard, targetContainer);
        updateAllColumnState();

        // Send backend API update request
        fetch(`/tasks/${taskId}/status`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-Requested-With': 'XMLHttpRequest'
            },
            body: JSON.stringify({ status: newStatus })
        })
        .then(async res => {
            const data = await res.json();
            if (!res.ok || !data.success) {
                const errorMsg = data.error || 'Failed to update task status.';
                showToast(errorMsg, 'danger');
                
                // Rollback card position & column counts if backend rejects update
                if (originalContainer) {
                    moveCardDOM(draggedCard, originalContainer);
                    updateAllColumnState();
                }
            } else {
                showToast(`Task #${taskId} moved to "${newStatus}"`, 'success');
                if (data.task_stats) {
                    updateSummaryStats(data.task_stats);
                }
            }
        })
        .catch(err => {
            console.error('Kanban API Error:', err);
            showToast('Network error updating task status. Rolling back changes.', 'danger');
            if (originalContainer) {
                moveCardDOM(draggedCard, originalContainer);
                updateAllColumnState();
            }
        });
    }

    function moveCardDOM(card, container) {
        // Remove empty state placeholder in target container if present
        const emptyPlaceholder = container.querySelector('.empty-kanban-state');
        if (emptyPlaceholder) {
            emptyPlaceholder.remove();
        }
        container.appendChild(card);
    }

    function updateAllColumnState() {
        document.querySelectorAll('.kanban-column').forEach(col => {
            const container = col.querySelector('.kanban-cards-container');
            const colName = col.dataset.status;
            const countBadge = col.querySelector('.column-count-badge');
            
            // Count actual task cards in column
            const taskCards = container.querySelectorAll('.task-card');
            const count = taskCards.length;

            if (countBadge) {
                countBadge.textContent = `${colName} (${count})`;
            }

            // Manage empty column placeholder (Requirement 7)
            if (count === 0 && !container.querySelector('.empty-kanban-state')) {
                const placeholder = document.createElement('div');
                placeholder.className = 'empty-kanban-state';
                placeholder.style.cssText = 'text-align:center; padding:36px 12px; color:var(--text-muted); font-size:0.85rem; background:rgba(255,255,255,0.01); border:1px dashed var(--border-color); border-radius:var(--radius-md);';
                placeholder.innerHTML = '<i class="fa-regular fa-folder-open" style="font-size:1.4rem; margin-bottom:8px; opacity:0.5; display:block;"></i>No tasks';
                container.appendChild(placeholder);
            }
        });
    }

    function updateSummaryStats(stats) {
        const totalEl = document.getElementById('stat_total_tasks');
        const doneEl = document.getElementById('stat_completed_tasks');
        const pendingEl = document.getElementById('stat_pending_tasks');
        const pctEl = document.getElementById('stat_completion_pct');
        const pctBar = document.getElementById('stat_completion_bar');

        if (totalEl) totalEl.textContent = stats.total_tasks;
        if (doneEl) doneEl.textContent = stats.completed_count;
        if (pendingEl) pendingEl.textContent = stats.pending_count;
        if (pctEl) pctEl.textContent = stats.completion_pct + '%';
        if (pctBar) pctBar.style.width = stats.completion_pct + '%';
    }

    function showToast(message, type) {
        const toast = document.createElement('div');
        toast.className = `alert alert-${type}`;
        toast.style.cssText = 'position:fixed; bottom:24px; right:24px; z-index:9999; box-shadow:0 10px 25px rgba(0,0,0,0.5); min-width:280px; margin:0; animation: fadeIn 0.3s ease;';
        toast.innerHTML = `<i class="fa-solid ${type === 'success' ? 'fa-circle-check' : 'fa-circle-exclamation'}"></i> <span>${message}</span>`;
        document.body.appendChild(toast);

        setTimeout(() => {
            toast.style.opacity = '0';
            toast.style.transition = 'opacity 0.5s ease';
            setTimeout(() => toast.remove(), 500);
        }, 3500);
    }
});
