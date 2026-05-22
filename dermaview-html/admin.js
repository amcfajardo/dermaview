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
    const showAccountForm = document.getElementById('showAccountForm');
    const cancelAccountForm = document.getElementById('cancelAccountForm');
    const accountsSearch = document.getElementById('accountsSearch');

    if (!accountForm || !accountsTableBody) return;

    function setFormVisible(isVisible) {
      accountForm.hidden = !isVisible;

      if (showAccountForm) {
        showAccountForm.hidden = isVisible;
      }
    }

    function filterAccounts() {
      if (!accountsSearch) return;

      const query = accountsSearch.value.trim().toLowerCase();
      const rows = accountsTableBody.querySelectorAll('tr');

      rows.forEach(row => {
        row.hidden = query !== '' && !row.textContent.toLowerCase().includes(query);
      });
    }

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
          filterAccounts();
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

    if (accountsSearch) {
      accountsSearch.addEventListener('input', filterAccounts);
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
          setFormVisible(false);
          loadAccounts();
        })
        .catch(() => {
          alert('Failed to add account.');
        });
    });

    if (showAccountForm) {
      showAccountForm.addEventListener('click', function () {
        setFormVisible(true);
        document.getElementById('accountFirstName')?.focus();
      });
    }

    if (cancelAccountForm) {
      cancelAccountForm.addEventListener('click', function () {
        accountForm.reset();
        setFormVisible(false);
      });
    }

    accountsTableBody.addEventListener('click', function (e) {
      const isDeactivate = e.target.classList.contains('deactivate-btn');
      const isReactivate = e.target.classList.contains('reactivate-btn');

      if (!isDeactivate && !isReactivate) return;

      const action = isDeactivate ? 'deactivate' : 'reactivate';
      const label = isDeactivate ? 'Deactivate' : 'Reactivate';
      const id = e.target.dataset.id;

      if (!id || !confirm(`${label} this account?`)) return;

      const formData = new FormData();
      formData.append('action', action);
      formData.append('id', id);

      fetch('admin_pages/manage-accounts.php', {
        method: 'POST',
        body: formData
      })
        .then(response => response.text())
        .then(message => {
          alert(message);
          loadAccounts();
        })
        .catch(() => {
          alert(`Failed to ${action} account.`);
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

    fetch(`${url}?v=${Date.now()}`, { cache: 'no-store' })
      .then(r => {
        if (!r.ok) throw new Error('Failed to load page');
        return r.text();
      })
      .then(html => {
        const parser = new DOMParser();
        const doc = parser.parseFromString(html, 'text/html');
        const styles = Array.from(doc.head.querySelectorAll('style'))
          .map(style => style.outerHTML)
          .join('');
        const body = doc.body ? doc.body.innerHTML : html;

        pageContent.innerHTML = styles + body;

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
