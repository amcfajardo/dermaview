document.addEventListener('DOMContentLoaded', function () {
  const nav = document.getElementById('adminNav');
  const links = nav.querySelectorAll('a[data-page]');
  const pageTitle = document.getElementById('pageTitle');
  const pageContent = document.getElementById('pageContent');

  const titles = {
    dashboard: 'Dashboard',
    staff: 'Staff Accounts',
    appointments: 'Appointments',
    patients: 'Patient Records',
    activity: 'Activity Logs',
    procedures: 'Manage Procedures',
    processing: 'Image Processing Settings',
    system: 'System Settings',
    records: 'Consultation / Image Records',
    reports: 'Reports',
    privacy: 'Privacy / Data Management'
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
    procedures: {
      url: 'admin-procedures.html',
      init: window.initManageProcedures
    },
    processing: {
      url: 'admin-processing-settings.html',
      init: window.initProcessingSettings
    },
    system: {
      url: 'admin-system-settings.html',
      init: window.initSystemSettings
    },
    records: {
      url: 'admin-consultation-records.html',
      init: window.initConsultationRecords
    },
    reports: {
      url: 'admin-reports.html',
      init: window.initReports
    },
    privacy: {
      url: 'admin-privacy-data.html'
    }
  };

  function showLoading() {
    pageContent.innerHTML = '<div class="card placeholder">Loading...</div>';
  }

  function setActiveNav(page) {
    links.forEach(link => {
      link.classList.toggle('active', link.dataset.page === page);
    });
  }

  function renderPage(page) {
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
    const requestedPage = location.hash ? location.hash.replace('#', '') : 'dashboard';
    const page = pages[requestedPage] ? requestedPage : 'dashboard';
    renderPage(page);
  }

  window.addEventListener('hashchange', handleHash);
  handleHash();
});
