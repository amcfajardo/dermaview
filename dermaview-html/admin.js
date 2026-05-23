document.addEventListener('DOMContentLoaded', function () {
  const nav = document.getElementById('adminNav');
  const links = nav.querySelectorAll('a[data-page]');
  const pageTitle = document.getElementById('pageTitle');
  const pageContent = document.getElementById('pageContent');

  const titles = {
    dashboard: 'Dashboard',
    staff: 'Manage Staff / Employee Accounts',
    appointments: 'Schedules / Appointments',
    procedures: 'Manage Procedures',
    beforeafter: 'Manage Before-and-After Images',
    processed: 'View Processed Images',
    processing: 'Configure Image Processing Settings',
    records: 'View Consultation / Image Records',
    reports: 'View Reports'
  };

  const pages = {
    dashboard: {
      init: function () {
        window.initAdminDashboard(pageContent);
      }
    },
    staff: {
      url: 'admin_pages/manage-accounts.html',
      init: window.initManageAccounts
    },
    appointments: {
      url: 'admin_pages/manage-appointments.html',
      init: window.initManageAppointments
    },
    procedures: {
      url: 'admin_pages/manage-procedures.html'
    },
    beforeafter: {
      url: 'admin_pages/manage-before-after.html'
    },
    processed: {
      url: 'admin_pages/view-processed.html',
      init: window.initProcessedImages
    },
    processing: {
      url: 'admin_pages/configure-processing.html'
    },
    records: {
      url: 'admin_pages/view-records.html'
    },
    reports: {
      url: 'admin_pages/view-reports.html'
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
    const page = location.hash ? location.hash.replace('#', '') : 'dashboard';
    renderPage(page);
  }

  window.addEventListener('hashchange', handleHash);
  handleHash();
});
