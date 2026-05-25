(function () {
  window.initManageAccounts = function () {
    const accountForm = document.getElementById('accountForm');
    const accountsTableBody = document.getElementById('accountsTableBody');
    const showAccountForm = document.getElementById('showAccountForm');
    const cancelAccountForm = document.getElementById('cancelAccountForm');
    const accountsSearch = document.getElementById('accountsSearch');
    const panel = document.querySelector('.accounts-panel[data-account-scope]');
    const scope = panel ? panel.dataset.accountScope : 'all';
    const actionInput = accountForm ? accountForm.querySelector('input[name="action"]') : null;
    const idInput = accountForm ? accountForm.querySelector('input[name="id"]') : null;
    const passwordInput = document.getElementById('accountPassword');
    const submitButton = document.getElementById('accountSubmitButton');
    const formTitle = accountForm ? accountForm.querySelector('.accounts-form-title h4') : null;

    if (!accountForm || !accountsTableBody) return;

    function setFormVisible(isVisible) {
      accountForm.hidden = !isVisible;
      document.body.classList.toggle('accounts-modal-open', isVisible);

      if (showAccountForm) {
        showAccountForm.hidden = isVisible;
      }
    }

    function resetFormMode() {
      accountForm.reset();
      if (actionInput) actionInput.value = 'add';
      if (idInput) idInput.value = '';
      if (passwordInput) {
        passwordInput.required = true;
        passwordInput.closest('.accounts-field').hidden = false;
      }
      if (submitButton) submitButton.textContent = scope === 'admin' ? 'Add Admin' : 'Add Account';
      if (formTitle) formTitle.textContent = scope === 'admin' ? 'Create Admin Account' : 'Create Account';
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
      formData.append('scope', scope);

      fetch('admin-accounts.php', {
        method: 'POST',
        cache: 'no-store',
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

      fetch('admin-accounts.php', {
        method: 'POST',
        cache: 'no-store',
        body: formData
      })
        .then(response => response.text())
        .then(message => {
          alert(message);
          resetFormMode();
          setFormVisible(false);
          loadAccounts();
        })
        .catch(() => {
          alert('Failed to add account.');
        });
    });

    if (showAccountForm) {
      showAccountForm.addEventListener('click', function () {
        resetFormMode();
        setFormVisible(true);
        document.getElementById('accountFirstName')?.focus();
      });
    }

    if (cancelAccountForm) {
      cancelAccountForm.addEventListener('click', function () {
        resetFormMode();
        setFormVisible(false);
      });
    }

    document.addEventListener('keydown', function (event) {
      if (event.key !== 'Escape' || accountForm.hidden) return;
      resetFormMode();
      setFormVisible(false);
    });

    accountsTableBody.addEventListener('click', function (e) {
      const isDeactivate = e.target.classList.contains('deactivate-btn');
      const isReactivate = e.target.classList.contains('reactivate-btn');
      const isEdit = e.target.classList.contains('edit-account-btn');
      const isReset = e.target.classList.contains('reset-password-btn');

      if (isEdit) {
        const row = e.target.closest('tr');
        if (!row) return;

        if (actionInput) actionInput.value = 'update';
        if (idInput) idInput.value = row.dataset.id || '';
        document.getElementById('accountFirstName').value = row.dataset.firstName || '';
        document.getElementById('accountLastName').value = row.dataset.lastName || '';
        document.getElementById('accountEmail').value = row.dataset.email || '';
        document.getElementById('accountEmployeeNumber').value = row.dataset.employeeNumber || '';
        document.getElementById('accountRole').value =
          row.dataset.role === 'superadmin' ? 'super_admin' : (row.dataset.role || '');
        if (passwordInput) {
          passwordInput.value = '';
          passwordInput.required = false;
          passwordInput.closest('.accounts-field').hidden = true;
        }
        if (submitButton) submitButton.textContent = 'Save Changes';
        if (formTitle) formTitle.textContent = 'Edit Account';
        setFormVisible(true);
        document.getElementById('accountFirstName')?.focus();
        return;
      }

      if (isReset) {
        const id = e.target.dataset.id;
        const password = prompt('Enter a temporary password for this account:');

        if (!id || password === null) return;

        const formData = new FormData();
        formData.append('action', 'reset_password');
        formData.append('id', id);
        formData.append('password', password);

        fetch('admin-accounts.php', {
          method: 'POST',
          cache: 'no-store',
          body: formData
        })
          .then(response => response.text())
          .then(message => {
            alert(message);
            loadAccounts();
          })
          .catch(() => {
            alert('Failed to reset password.');
          });
        return;
      }

      if (!isDeactivate && !isReactivate) return;

      const action = isDeactivate ? 'deactivate' : 'reactivate';
      const label = isDeactivate ? 'Deactivate' : 'Reactivate';
      const id = e.target.dataset.id;

      if (!id || !confirm(`${label} this account?`)) return;

      const formData = new FormData();
      formData.append('action', action);
      formData.append('id', id);

      fetch('admin-accounts.php', {
        method: 'POST',
        cache: 'no-store',
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
