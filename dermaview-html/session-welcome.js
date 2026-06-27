(function () {
  let lastSession = null;

  function roleLabel(role) {
    const normalized = String(role || '').trim().toLowerCase().replace(/[\s_-]+/g, '');
    if (normalized === 'superadmin') return 'Super Admin';
    if (normalized === 'admin') return 'Admin';
    if (normalized === 'staff') return 'Staff';
    return role || 'User';
  }

  function render(target, session) {
    lastSession = session;
    const firstName = String(session.user_name || '').trim().split(/\s+/)[0] || 'User';
    const employeeNumber = session.employee_number || 'No employee number';
    target.innerHTML = `
      <strong>Welcome, ${firstName} - ${employeeNumber}</strong>
      <span>${roleLabel(session.role)}</span>
    `;
    target.hidden = false;
  }

  function findTarget() {
    return document.getElementById('sessionWelcome');
  }

  function withTarget(callback, attempts = 20) {
    const target = findTarget();
    if (target) {
      callback(target);
      return;
    }

    if (attempts <= 0) return;
    window.setTimeout(() => withTarget(callback, attempts - 1), 50);
  }

  function renderSavedSession() {
    if (!lastSession || lastSession.status !== 'ok') return;

    const target = findTarget();
    if (target && target.hidden) {
      render(target, lastSession);
    }
  }

  fetch('get-session.php', { cache: 'no-store' })
    .then(response => response.json())
    .then(session => {
      withTarget(target => {
        if (!session || session.status !== 'ok') {
          target.hidden = true;
          return;
        }

        render(target, session);
      });

      const observer = new MutationObserver(renderSavedSession);
      observer.observe(document.body, { childList: true, subtree: true });
    })
    .catch(() => {
      withTarget(target => {
        target.hidden = true;
      });
    });
})();
