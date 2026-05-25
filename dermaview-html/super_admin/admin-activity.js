// Super Admin module: full-system control surface.
(function () {
  function escapeHtml(value) {
    const div = document.createElement('div');
    div.textContent = value == null ? '' : String(value);
    return div.innerHTML;
  }

  function formatDate(value) {
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return '';
    return date.toLocaleString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
      hour: 'numeric',
      minute: '2-digit'
    });
  }

  window.initActivityLogs = function () {
    const body = document.getElementById('activityLogsBody');
    const search = document.getElementById('activitySearch');
    const refresh = document.getElementById('refreshActivityLogs');

    if (!body) return;

    let logs = [];

    function render() {
      const query = search ? search.value.trim().toLowerCase() : '';
      const rows = query
        ? logs.filter(item => `${item.type} ${item.title} ${item.status} ${item.date}`.toLowerCase().includes(query))
        : logs;

      body.innerHTML = rows.length ? rows.map(item => `
        <tr>
          <td>${escapeHtml(item.type || 'Activity')}</td>
          <td><strong>${escapeHtml(item.title || 'System activity')}</strong></td>
          <td>${escapeHtml(item.status || 'Recorded')}</td>
          <td>${escapeHtml(formatDate(item.date))}</td>
        </tr>
      `).join('') : '<tr><td colspan="4" class="accounts-empty-cell">No activity logs found.</td></tr>';
    }

    function loadLogs() {
      fetch(`admin-dashboard.php?v=${Date.now()}`, { cache: 'no-store' })
        .then(response => response.json())
        .then(payload => {
          if (!payload || payload.status !== 'ok') throw new Error('Failed to load activity logs.');
          logs = payload.recent_activity || [];
          render();
        })
        .catch(error => {
          body.innerHTML = `<tr><td colspan="4" class="accounts-empty-cell">${escapeHtml(error.message || 'Failed to load activity logs.')}</td></tr>`;
        });
    }

    if (search) search.addEventListener('input', render);
    if (refresh) refresh.addEventListener('click', loadLogs);

    loadLogs();
  };
})();
