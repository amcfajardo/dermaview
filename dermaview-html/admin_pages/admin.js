document.addEventListener('DOMContentLoaded', function () {
  const nav = document.getElementById('adminNav');
  if (!nav) return;

  const links = nav.querySelectorAll('a[data-page]');
  const pageTitle = document.getElementById('pageTitle');
  const pageContent = document.getElementById('pageContent');

  const titles = {
    dashboard: 'Dashboard',
    appointments: 'Appointments',
    patients: 'Patient Records',
    staff: 'Staff / Employee Accounts',
    activity: 'Activity Logs',
    records: 'Consultation / Image Records',
    reports: 'Reports',
    restricted: 'Super Admin Access Required'
  };

  const pages = {
    dashboard: {
      init: function () {
        window.initAdminDashboard(pageContent);
      }
    },
    staff: {
      url: 'admin-accounts.html',
      init: window.initManageAccounts
    },
    appointments: {
      url: 'admin-appointments.html',
      init: window.initManageAppointments
    },
    patients: {
      url: 'admin-patients.html',
      init: window.initPatientRecords
    },
    activity: {
      url: 'admin-activity.html',
      init: window.initActivityLogs
    },
    records: {
      url: 'admin-consultation-records.html',
      init: window.initConsultationRecords
    },
    reports: {
      url: 'admin-reports.html',
      init: window.initReports
    }
  };

  const pageAliases = {
    accounts: 'staff',
    'admin-accounts': 'staff',
    employees: 'staff',
    procedures: 'restricted',
    procedure: 'restricted',
    'procedure-management': 'restricted',
    processing: 'restricted',
    'image-processing-settings': 'restricted',
    settings: 'restricted',
    system: 'restricted',
    'system-settings': 'restricted',
    privacy: 'restricted',
    'privacy-data': 'restricted',
    backup: 'restricted',
    roles: 'restricted',
    permissions: 'restricted',
    adminaccounts: 'restricted',
    admins: 'restricted',
    logs: 'activity',
    'activity-logs': 'activity',
    consultation: 'records',
    'consultation-records': 'records',
    'image-records': 'records'
  };

  function showLoading() {
    pageContent.innerHTML = '<div class="card placeholder">Loading...</div>';
  }

  function setActiveNav(page) {
    links.forEach(link => {
      link.classList.toggle('active', link.dataset.page === page);
    });
  }

  function normalizePage(value) {
    const key = String(value || '').replace(/^#/, '').trim();
    return pages[key] ? key : (pageAliases[key.toLowerCase()] || 'dashboard');
  }

  function renderRestrictedPage() {
    setActiveNav('');
    pageTitle.textContent = titles.restricted;
    pageContent.innerHTML = `
      <section class="panel-card" style="max-width: 760px;">
        <h3>Super Admin Access Required</h3>
        <p class="section-text">
          Procedure configuration, image-processing settings, system settings, privacy controls,
          role permissions, admin accounts, and backup tools are reserved for Super Admin.
        </p>
        <div class="admin-button-row" style="margin-top: 16px;">
          <a class="accounts-create-btn" href="../super_admin/super-admin.html">Open Super Admin</a>
          <button type="button" class="accounts-close" id="returnToAdminDashboard">Back to Admin Dashboard</button>
        </div>
      </section>
    `;

    const back = document.getElementById('returnToAdminDashboard');
    if (back) {
      back.addEventListener('click', function () {
        location.hash = 'dashboard';
      });
    }
  }

  function guardAdminSession() {
    fetch('../get-session.php', { cache: 'no-store' })
      .then(response => response.json())
      .then(session => {
        const role = String(session.role || '').trim().toLowerCase().replace(/[\s_-]+/g, '');
        if (session.status !== 'ok' || (role !== 'admin' && role !== 'superadmin')) {
          window.location.replace('../login.html');
          return;
        }

        if (role === 'superadmin') {
          window.location.replace(`../super_admin/super-admin.html${location.hash || ''}`);
        }
      })
      .catch(() => {
        window.location.replace('../login.html');
      });
  }

  function renderPage(page) {
    if (page === 'restricted') {
      renderRestrictedPage();
      return;
    }

    const config = pages[page] || pages.dashboard;

    setActiveNav(page);
    pageTitle.textContent = titles[page] || titles.dashboard;

    if (!config.url) {
      config.init();
      return;
    }

    showLoading();

    fetch(`${config.url}?v=${Date.now()}`, { cache: 'no-store' })
      .then(response => {
        if (!response.ok) throw new Error('Failed to load page');
        return response.text();
      })
      .then(html => {
        const parser = new DOMParser();
        const doc = parser.parseFromString(html, 'text/html');
        const styles = Array.from(doc.head.querySelectorAll('style'))
          .map(style => style.outerHTML)
          .join('');
        const body = doc.body ? doc.body.innerHTML : html;

        pageContent.innerHTML = styles + body;

        if (typeof config.init === 'function') {
          config.init();
        }
      })
      .catch(error => {
        pageContent.innerHTML = `<div class="card placeholder">Error loading page: ${error.message}</div>`;
      });
  }

  links.forEach(link => {
    link.addEventListener('click', function (event) {
      event.preventDefault();

      const page = this.dataset.page;

      if (location.hash !== `#${page}`) {
        location.hash = page;
      } else {
        renderPage(page);
      }
    });
  });

  function handleHash() {
    renderPage(normalizePage(location.hash || 'dashboard'));
  }

  window.addEventListener('hashchange', handleHash);
  guardAdminSession();
  handleHash();
});
