(function () {
  function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text || '';
    return div.innerHTML;
  }

  function dashboardShell() {
    return `
      <section class="dashboard-shell">
        <div class="dashboard-hero panel-card">
          <div>
            <span class="dashboard-kicker">Admin Overview</span>
            <h3>DermaView System Dashboard</h3>
            <p class="section-text">Monitor procedures, image records, staff accounts, appointment activity, and system health.</p>
          </div>
          <button type="button" class="dashboard-refresh" id="dashboardRefresh">Refresh</button>
        </div>

        <div class="dashboard-stat-grid">
          <div class="dashboard-stat-card panel-card">
            <span>Total Procedures</span>
            <strong data-stat="procedures">--</strong>
            <p>Supported treatment catalog</p>
          </div>
          <div class="dashboard-stat-card panel-card">
            <span>Processed Images</span>
            <strong data-stat="images">--</strong>
            <p>Uploaded or processed image records</p>
          </div>
          <div class="dashboard-stat-card panel-card">
            <span>Staff Accounts</span>
            <strong data-stat="staff">--</strong>
            <p>Admin and staff users</p>
          </div>
          <div class="dashboard-stat-card panel-card">
            <span>Appointments</span>
            <strong data-stat="appointments">--</strong>
            <p>Recorded schedule requests</p>
          </div>
        </div>

        <div class="dashboard-main-grid">
          <section class="panel-card dashboard-activity-card">
            <div class="dashboard-card-header">
              <div>
                <span class="dashboard-kicker">Recent Activity</span>
                <h3>Latest clinic updates</h3>
              </div>
            </div>
            <div class="dashboard-activity-list" id="dashboardActivity">
              <p class="dashboard-empty">Loading recent activity...</p>
            </div>
          </section>

          <aside class="panel-card dashboard-status-card">
            <span class="dashboard-kicker">System Status</span>
            <h3>Current health</h3>
            <div class="dashboard-status-list" id="dashboardStatus">
              <p class="dashboard-empty">Checking system status...</p>
            </div>
            <div class="dashboard-appointment-summary">
              <div>
                <span>Pending</span>
                <strong data-stat="pending_appointments">--</strong>
              </div>
              <div>
                <span>Confirmed</span>
                <strong data-stat="confirmed_appointments">--</strong>
              </div>
              <div>
                <span>Completed</span>
                <strong data-stat="completed_appointments">--</strong>
              </div>
            </div>
          </aside>
        </div>
      </section>
    `;
  }

  function formatActivityDate(value) {
    const date = new Date(value);

    if (Number.isNaN(date.getTime())) {
      return '';
    }

    return date.toLocaleString('en-US', {
      month: 'short',
      day: 'numeric',
      hour: 'numeric',
      minute: '2-digit'
    });
  }

  function renderDashboardData(pageContent, data) {
    const stats = data.stats || {};

    Object.entries(stats).forEach(([key, value]) => {
      const el = pageContent.querySelector(`[data-stat="${key}"]`);
      if (el) el.textContent = Number(value || 0).toLocaleString();
    });

    const activity = pageContent.querySelector('#dashboardActivity');
    const status = pageContent.querySelector('#dashboardStatus');

    if (activity) {
      const items = data.recent_activity || [];
      activity.innerHTML = items.length
        ? items.map(item => `
            <div class="dashboard-activity-item">
              <div class="dashboard-activity-icon">${escapeHtml((item.type || 'A').charAt(0))}</div>
              <div>
                <strong>${escapeHtml(item.title)}</strong>
                <span>${escapeHtml(item.type)}${item.meta ? ' - ' + escapeHtml(item.meta) : ''}</span>
              </div>
              <time>${escapeHtml(formatActivityDate(item.created_at))}</time>
            </div>
          `).join('')
        : '<p class="dashboard-empty">No recent activity yet.</p>';
    }

    if (status) {
      const items = data.system_status || [];
      status.innerHTML = items.length
        ? items.map(item => `
            <div class="dashboard-status-item">
              <span class="dashboard-status-dot status-${escapeHtml(item.state)}"></span>
              <div>
                <strong>${escapeHtml(item.label)}</strong>
                <span>${escapeHtml(item.value)}</span>
              </div>
            </div>
          `).join('')
        : '<p class="dashboard-empty">No status details available.</p>';
    }
  }

  function loadDashboard(pageContent) {
    fetch(`admin-dashboard.php?v=${Date.now()}`, { cache: 'no-store' })
      .then(response => response.json())
      .then(data => {
        if (!data || data.status !== 'ok') {
          throw new Error('Dashboard data unavailable');
        }
        renderDashboardData(pageContent, data);
      })
      .catch(() => {
        const activity = pageContent.querySelector('#dashboardActivity');
        const status = pageContent.querySelector('#dashboardStatus');
        if (activity) activity.innerHTML = '<p class="dashboard-empty">Failed to load recent activity.</p>';
        if (status) status.innerHTML = '<p class="dashboard-empty">Failed to load system status.</p>';
      });
  }

  window.initAdminDashboard = function (pageContent) {
    pageContent.innerHTML = dashboardShell();

    const refresh = document.getElementById('dashboardRefresh');
    if (refresh) {
      refresh.addEventListener('click', function () {
        loadDashboard(pageContent);
      });
    }

    loadDashboard(pageContent);
  };
})();
