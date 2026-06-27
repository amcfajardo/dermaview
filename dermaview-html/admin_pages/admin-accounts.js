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
    const confirmPasswordInput = document.getElementById('accountConfirmPassword');
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
      if (confirmPasswordInput) {
        confirmPasswordInput.required = true;
        confirmPasswordInput.closest('.accounts-field').hidden = false;
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

    accountForm.addEventListener('submit', async function (e) {
      e.preventDefault();

      const formData = new FormData(accountForm);
      const password = formData.get('password') || '';
      const confirmPassword = formData.get('confirm_password') || '';

      if (passwordInput && !passwordInput.closest('.accounts-field').hidden && window.isPasswordComplexEnough && !window.isPasswordComplexEnough(password)) {
        await DermaViewDialog.alert(window.passwordPolicyMessage, { title: 'Password Requirement' });
        return;
      }

      if (passwordInput && !passwordInput.closest('.accounts-field').hidden && password !== confirmPassword) {
        await DermaViewDialog.alert('Passwords do not match.', { title: 'Accounts' });
        confirmPasswordInput?.focus();
        return;
      }

      try {
        const response = await fetch('admin-accounts.php', {
          method: 'POST',
          cache: 'no-store',
          body: formData
        });
        const message = await response.text();
        await DermaViewDialog.alert(message, { title: 'Accounts' });
        resetFormMode();
        setFormVisible(false);
        loadAccounts();
      } catch (error) {
        await DermaViewDialog.alert('Failed to add account.', { title: 'Accounts' });
      }
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

    accountsTableBody.addEventListener('click', async function (e) {
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
        document.getElementById('accountRole').value = row.dataset.role || '';
        if (passwordInput) {
          passwordInput.value = '';
          passwordInput.required = false;
          passwordInput.closest('.accounts-field').hidden = true;
        }
        if (confirmPasswordInput) {
          confirmPasswordInput.value = '';
          confirmPasswordInput.required = false;
          confirmPasswordInput.closest('.accounts-field').hidden = true;
        }
        if (submitButton) submitButton.textContent = 'Save Changes';
        if (formTitle) formTitle.textContent = 'Edit Account';
        setFormVisible(true);
        document.getElementById('accountFirstName')?.focus();
        return;
      }

      if (isReset) {
        const id = e.target.dataset.id;
        const password = await DermaViewDialog.prompt('Enter a temporary password for this account:', {
          title: 'Reset Password',
          inputType: 'password',
          okText: 'Reset Password'
        });

        if (!id || password === false) return;

        const confirmPassword = await DermaViewDialog.prompt('Confirm the temporary password:', {
          title: 'Confirm Password',
          inputType: 'password',
          okText: 'Confirm'
        });

        if (confirmPassword === false) return;

        if (password !== confirmPassword) {
          await DermaViewDialog.alert('Passwords do not match.', { title: 'Accounts' });
          return;
        }

        if (window.isPasswordComplexEnough && !window.isPasswordComplexEnough(password)) {
          await DermaViewDialog.alert(window.passwordPolicyMessage, { title: 'Password Requirement' });
          return;
        }

        const formData = new FormData();
        formData.append('action', 'reset_password');
        formData.append('id', id);
        formData.append('password', password);
        formData.append('confirm_password', confirmPassword);

        try {
          const response = await fetch('admin-accounts.php', {
            method: 'POST',
            cache: 'no-store',
            body: formData
          });
          const message = await response.text();
          await DermaViewDialog.alert(message, { title: 'Accounts' });
          loadAccounts();
        } catch (error) {
          await DermaViewDialog.alert('Failed to reset password.', { title: 'Accounts' });
        }
        return;
      }

      if (!isDeactivate && !isReactivate) return;

      const action = isDeactivate ? 'deactivate' : 'reactivate';
      const label = isDeactivate ? 'Deactivate' : 'Reactivate';
      const id = e.target.dataset.id;

      if (!id) return;

      const shouldChangeStatus = await DermaViewDialog.confirm(`${label} this account?`, {
        title: 'Accounts',
        okText: label
      });

      if (!shouldChangeStatus) return;

      const formData = new FormData();
      formData.append('action', action);
      formData.append('id', id);

      try {
        const response = await fetch('admin-accounts.php', {
          method: 'POST',
          cache: 'no-store',
          body: formData
        });
        const message = await response.text();
        await DermaViewDialog.alert(message, { title: 'Accounts' });
        loadAccounts();
      } catch (error) {
        await DermaViewDialog.alert(`Failed to ${action} account.`, { title: 'Accounts' });
      }
    });

    loadAccounts();
  };
})();
