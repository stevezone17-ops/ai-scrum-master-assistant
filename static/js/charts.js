// Dashboard Chart.js Integration

function renderDashboardCharts(taskStats, workloadData, velocityData) {
    Chart.defaults.color = '#9ca3af';
    Chart.defaults.font.family = "'Inter', sans-serif";

    // 1. Task Status Breakdown (Doughnut Chart)
    const taskCanvas = document.getElementById('taskStatusChart');
    if (taskCanvas) {
        new Chart(taskCanvas.getContext('2d'), {
            type: 'doughnut',
            data: {
                labels: ['To Do', 'In Progress', 'Testing', 'Done'],
                datasets: [{
                    data: [
                        taskStats.todo || 0,
                        taskStats.in_progress || 0,
                        taskStats.testing || 0,
                        taskStats.done || 0
                    ],
                    backgroundColor: ['#64748b', '#3b82f6', '#f59e0b', '#10b981'],
                    borderWidth: 0,
                    hoverOffset: 6
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { position: 'bottom', labels: { boxWidth: 12, padding: 16 } }
                },
                cutout: '70%'
            }
        });
    }

    // 2. Team Workload Distribution (Bar Chart)
    const workloadCanvas = document.getElementById('workloadChart');
    if (workloadCanvas && workloadData && workloadData.length > 0) {
        const labels = workloadData.map(w => w.username);
        const estHours = workloadData.map(w => w.est_hours || 0);
        const actHours = workloadData.map(w => w.act_hours || 0);

        new Chart(workloadCanvas.getContext('2d'), {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [
                    {
                        label: 'Estimated Hours',
                        data: estHours,
                        backgroundColor: '#6366f1',
                        borderRadius: 6
                    },
                    {
                        label: 'Actual Hours Spent',
                        data: actHours,
                        backgroundColor: '#10b981',
                        borderRadius: 6
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { position: 'bottom' }
                },
                scales: {
                    x: { grid: { display: false } },
                    y: { grid: { color: 'rgba(255, 255, 255, 0.05)' }, beginAtZero: true }
                }
            }
        });
    }

    // 3. Sprint Velocity Trend (Line Chart)
    const velocityCanvas = document.getElementById('velocityChart');
    if (velocityCanvas) {
        const sprintLabels = (velocityData && velocityData.labels) ? velocityData.labels : ['Sprint 1', 'Sprint 2 (Current)', 'Sprint 3 (Predicted)'];
        const velocityValues = (velocityData && velocityData.values) ? velocityData.values : [14, 18, 22];

        new Chart(velocityCanvas.getContext('2d'), {
            type: 'line',
            data: {
                labels: sprintLabels,
                datasets: [{
                    label: 'Sprint Velocity (Story Points)',
                    data: velocityValues,
                    borderColor: '#8b5cf6',
                    backgroundColor: 'rgba(139, 92, 246, 0.15)',
                    fill: true,
                    tension: 0.4,
                    pointBackgroundColor: '#8b5cf6',
                    pointRadius: 5
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { position: 'bottom' }
                },
                scales: {
                    x: { grid: { display: false } },
                    y: { grid: { color: 'rgba(255, 255, 255, 0.05)' }, beginAtZero: true }
                }
            }
        });
    }
}
