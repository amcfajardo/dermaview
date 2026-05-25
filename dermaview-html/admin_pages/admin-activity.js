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
      fetch(`admin-log-mirror.php?v=${Date.now()}`, { cache: 'no-store' })
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

    // Presence: heartbeat
    function startPresenceHeartbeat() {
      if (window.__presenceHeartbeatStarted) return;
      window.__presenceHeartbeatStarted = true;

      function touch() {
        fetch('../set-presence.php?v=' + Date.now(), { method: 'POST', cache: 'no-store' }).catch(() => {});
      }

      touch();
      setInterval(touch, 30000);
    }

    startPresenceHeartbeat();

    function loadOnlineUsers() {
      const presenceBody = document.getElementById('onlineUsersBody');
      if (!presenceBody) return;

      fetch(`../get-online-users.php?v=${Date.now()}`, { cache: 'no-store' })
        .then(r => {
          if (!r.ok) throw new Error('Failed to load online users');
          return r.json();
        })
        .then(payload => {
          if (!payload || payload.status !== 'ok') throw new Error('Failed to load online users');
          const list = payload.online_users || [];
          if (!list.length) {
            presenceBody.innerHTML = `<tr><td colspan="3" class="accounts-empty-cell">No one online.</td></tr>`;
            return;
          }
          presenceBody.innerHTML = list.map(u => `
            <tr>
              <td>${escapeHtml(u.user_name || '')}</td>
              <td>${escapeHtml(u.role || '')}</td>
              <td>${escapeHtml(formatDate(u.last_seen))}</td>
            </tr>
          `).join('');
        })
        .catch(err => {
          presenceBody.innerHTML = `<tr><td colspan="3" class="accounts-empty-cell">${escapeHtml(err.message || 'Failed to load online users')}</td></tr>`;
        });
    }

    // initial + periodic
    loadOnlineUsers();
    setInterval(loadOnlineUsers, 30000);
  };
})();
