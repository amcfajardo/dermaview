document.addEventListener('DOMContentLoaded', function () {
  const nav = document.getElementById('adminNav');
  const links = nav.querySelectorAll('a[data-page]');
  const pageTitle = document.getElementById('pageTitle');
  const pageContent = document.getElementById('pageContent');

  function showLoading() {
    pageContent.innerHTML = '<div class="card placeholder">Loading…</div>';
  }

  function initManageAccounts() {
    const accountForm = document.getElementById('accountForm');
    const accountsTableBody = document.getElementById('accountsTableBody');

    if (!accountForm || !accountsTableBody) return;

    function loadAccounts() {
      const formData = new FormData();
      formData.append('action', 'fetch');

      fetch('admin_pages/manage-accounts.php', {
        method: 'POST',
        body: formData
      })
        .then(response => response.text())
        .then(html => {
          accountsTableBody.innerHTML = html;
        })
        .catch(() => {
          accountsTableBody.innerHTML = `
            <tr>
              <td colspan="6" style="padding:10px; text-align:center;">
                Failed to load accounts.
              </td>
            </tr>
          `;
        });
    }

    accountForm.addEventListener('submit', function (e) {
      e.preventDefault();

      const formData = new FormData(accountForm);

      fetch('admin_pages/manage-accounts.php', {
        method: 'POST',
        body: formData
      })
        .then(response => response.text())
        .then(message => {
          alert(message);
          accountForm.reset();
          loadAccounts();
        });
    });

    accountsTableBody.addEventListener('click', function (e) {
      if (!e.target.classList.contains('deactivate-btn')) return;

      const id = e.target.dataset.id;

      if (!confirm('Deactivate this account?')) return;

      const formData = new FormData();
      formData.append('action', 'deactivate');
      formData.append('id', id);

      fetch('admin_pages/manage-accounts.php', {
        method: 'POST',
        body: formData
      })
        .then(response => response.text())
        .then(message => {
          alert(message);
          loadAccounts();
        });
    });

    loadAccounts();
  }

  function setActive(page) {
    links.forEach(l => l.classList.toggle('active', l.dataset.page === page));

    const titles = {
      dashboard: 'Dashboard',
      staff: 'Manage Staff / Employee Accounts',
      procedures: 'Manage Procedures',
      education: 'Manage Educational Content',
      beforeafter: 'Manage Before-and-After Images',
      processed: 'View Processed Images',
      processing: 'Configure Image Processing Settings',
      records: 'View Consultation / Image Records',
      reports: 'View Reports'
    };

    pageTitle.textContent = titles[page] || 'Dashboard';

    const mapping = {
      dashboard: null,
      staff: 'admin_pages/manage-accounts.html',
      procedures: 'admin_pages/manage-procedures.html',
      education: 'admin_pages/manage-education.html',
      beforeafter: 'admin_pages/manage-before-after.html',
      processed: 'admin_pages/view-processed.html',
      processing: 'admin_pages/configure-processing.html',
      records: 'admin_pages/view-records.html',
      reports: 'admin_pages/view-reports.html'
    };

    const url = mapping[page];

    if (!url) {
      pageContent.innerHTML = `
        <div class="grid">
          <div class="card">
            <h3>Overview</h3>
            <p class="muted">Quick stats and shortcuts for admins.</p>
          </div>
          <div class="card">
            <h3>Recent Activity</h3>
            <div class="placeholder">No recent activity</div>
          </div>
        </div>
        <section style="margin-top:18px">
          <div class="card placeholder">Select a menu item to manage content.</div>
        </section>
      `;
      return;
    }

    showLoading();

    fetch(url, { cache: 'no-store' })
      .then(r => {
        if (!r.ok) throw new Error('Failed to load page');
        return r.text();
      })
      .then(html => {
        const parser = new DOMParser();
        const doc = parser.parseFromString(html, 'text/html');
        const body = doc.body ? doc.body.innerHTML : html;

        pageContent.innerHTML = body;

        if (page === 'staff') {
          initManageAccounts();
        }
      })
      .catch(err => {
        pageContent.innerHTML = `<div class="card placeholder">Error loading page: ${err.message}</div>`;
      });
  }

  links.forEach(link => {
    link.addEventListener('click', function (e) {
      e.preventDefault();

      const page = this.dataset.page;

      if (location.hash !== `#${page}`) {
        location.hash = page;
      } else {
        setActive(page);
      }
    });
  });

  function handleHash() {
    const page = location.hash ? location.hash.replace('#', '') : 'dashboard';
    setActive(page);
  }

  window.addEventListener('hashchange', handleHash);

  handleHash();
});