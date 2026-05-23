(function () {
  window.initManageAccounts = function () {
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
  };
})();
