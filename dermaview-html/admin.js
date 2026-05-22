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

  function initManageAppointments() {
    const appointmentForm = document.getElementById('appointmentForm');
    const appointmentsTableBody = document.getElementById('appointmentsTableBody');
    const showAppointmentForm = document.getElementById('showAppointmentForm');
    const cancelAppointmentForm = document.getElementById('cancelAppointmentForm');
    const appointmentsSearch = document.getElementById('appointmentsSearch');

    const calendarView = document.getElementById('calendarView');
    const tableView = document.getElementById('tableView');
    const calendarGrid = document.getElementById('calendarGrid');
    const calendarMonthLabel = document.getElementById('calendarMonthLabel');
    const calendarPrev = document.getElementById('calendarPrev');
    const calendarNext = document.getElementById('calendarNext');
    const showCalendarBtn = document.getElementById('showCalendarBtn');
    const showTableBtn = document.getElementById('showTableBtn');

    if (!appointmentForm || !appointmentsTableBody) return;


    function setFormVisible(isVisible) {
      appointmentForm.hidden = !isVisible;

      if (showAppointmentForm) {
        showAppointmentForm.hidden = isVisible;
      }
    }

    function filterAppointments() {
      if (!appointmentsSearch) return;

      const query = appointmentsSearch.value.trim().toLowerCase();
      const rows = appointmentsTableBody.querySelectorAll('tr');

      rows.forEach(row => {
        row.hidden = query !== '' && !row.textContent.toLowerCase().includes(query);
      });
    }

    function applyCalendarFilterAndRender() {
      if (!calendarView || calendarView.hidden) return;
      if (!calendarMonthCursor) calendarMonthCursor = new Date();
      renderCalendar({ monthDate: calendarMonthCursor });
    }

    let allAppointments = [];

    let calendarMonthCursor = null; // Date pointing at current month

    function parseAppointmentsFromRows() {
      // Re-parse the HTML table rows returned by manage-appointments.php
      // to build a structured list for the calendar.
      // Expected row: <tr title='notes'> ... <td><strong>Date</strong><br><span>$time</span></td> ... select exists in last td
      const rows = appointmentsTableBody.querySelectorAll('tr');
      const structured = [];

      rows.forEach(row => {
        const title = row.getAttribute('title') || '';

        const tds = row.querySelectorAll('td');
        if (!tds || tds.length < 6) return;

        const dateStrong = tds[0]?.querySelector('strong');
        const timeSpan = tds[0]?.querySelector('.table-muted');

        const patientTd = tds[1];
        const contactTd = tds[2];
        const procedureTd = tds[3];
        const statusChip = tds[4]?.querySelector('.appointment-status');
        const sourceTd = tds[5];
        const statusSelect = row.querySelector('select.appointment-status-select');

        // manage-appointments.php uses a formatted date label (M j, Y) so we need to keep
        // the raw text and convert back.
        const dateLabel = (dateStrong?.textContent || '').trim();
        const timeLabel = (timeSpan?.textContent || '').trim();
        if (!dateLabel) return;

        // Convert date label to ISO date using Date parsing
        const dayDate = new Date(dateLabel);
        if (Number.isNaN(dayDate.getTime())) return;

        // Parse timeLabel like "9:00 AM" back into HH:mm:ss-ish.
        // If parsing fails, we still place the event on the correct day.
        let hours = 0;
        let minutes = 0;
        const timeMatch = timeLabel.match(/(\d{1,2}):(\d{2})\s*(AM|PM)/i);
        if (timeMatch) {
          hours = parseInt(timeMatch[1], 10);
          minutes = parseInt(timeMatch[2], 10);
          const ap = timeMatch[3].toUpperCase();
          if (ap === 'PM' && hours !== 12) hours += 12;
          if (ap === 'AM' && hours === 12) hours = 0;
        }

        const isoDate = dayDate.toISOString().slice(0, 10);

        const patientName = (patientTd?.textContent || '').trim();
        const procedureName = (procedureTd?.textContent || '').trim();
        const status = (statusChip?.textContent || statusSelect?.value || '').trim();
        const source = (sourceTd?.textContent || '').trim();
        const phoneOrEmail = (contactTd?.textContent || '').trim();

        const id = statusSelect?.dataset?.id;

        structured.push({
          id: id ? Number(id) : null,
          isoDate,
          timeLabel,
          hours,
          minutes,
          patientName,
          procedureName,
          status,
          source,
          notes: title,
          phoneOrEmail
        });
      });

      return structured;
    }

    function renderCalendar({ monthDate }) {
      if (!calendarGrid) return;

      // Normalize cursor
      calendarMonthCursor = monthDate;
      const year = calendarMonthCursor.getFullYear();
      const month = calendarMonthCursor.getMonth();

      const firstOfMonth = new Date(year, month, 1);
      const startDay = firstOfMonth.getDay(); // 0=Sun
      const daysInMonth = new Date(year, month + 1, 0).getDate();

      const today = new Date();
      const todayIso = today.toISOString().slice(0, 10);

      if (calendarMonthLabel) {
        const label = calendarMonthCursor.toLocaleDateString('en-US', { month: 'long', year: 'numeric' });
        calendarMonthLabel.textContent = label;
      }

      // Weekday header
      const weekdays = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
      calendarGrid.innerHTML = `
        <div class="accounts-calendar-weekdays" style="grid-column: 1 / -1; display:grid;">` +
        weekdays.map(d => `<div>${d}</div>`).join('') +
        `</div>
        `;

      // We place weekday header using grid-column trick, but need day cells in same grid.
      // Easier: clear and rebuild properly.
      calendarGrid.innerHTML = '';

      weekdays.forEach(d => {
        const el = document.createElement('div');
        el.textContent = d;
        el.style.fontWeight = '900';
        el.style.color = 'var(--color-text-secondary)';
        el.style.fontSize = '0.9rem';
        el.style.padding = '0 4px 10px';
        el.style.gridColumn = 'auto';
        calendarGrid.appendChild(el);
      });

      // Now append 42 day cells (6 weeks)
      const totalCells = 42;
      const outsideStartDate = new Date(year, month, 1 - startDay);

      // Filtered appointments based on current search
      const query = appointmentsSearch ? appointmentsSearch.value.trim().toLowerCase() : '';
      const filtered = query
        ? allAppointments.filter(a => {
          const hay = `${a.patientName} ${a.procedureName} ${a.status} ${a.source} ${a.notes}`.toLowerCase();
          return hay.includes(query);
        })
        : allAppointments;

      const byDate = new Map();
      filtered.forEach(a => {
        const key = a.isoDate;
        if (!byDate.has(key)) byDate.set(key, []);
        byDate.get(key).push(a);
      });

      for (let i = 0; i < totalCells; i++) {
        const d = new Date(outsideStartDate);
        d.setDate(outsideStartDate.getDate() + i);

        const iso = d.toISOString().slice(0, 10);
        const isOutside = d.getMonth() !== month;
        const isToday = iso === todayIso;

        const events = byDate.get(iso) || [];
        // Sort by time
        events.sort((a, b) => (a.hours * 60 + a.minutes) - (b.hours * 60 + b.minutes));

        const cell = document.createElement('div');
        cell.className = 'accounts-calendar-day' + (isOutside ? ' is-outside-month' : '') + (isToday ? ' is-today' : '');

        const top = document.createElement('div');
        top.className = 'accounts-calendar-day-top';
        const num = document.createElement('div');
        num.className = 'accounts-calendar-day-num';
        num.textContent = d.getDate();
        const count = document.createElement('div');
        count.className = 'accounts-calendar-count';
        count.textContent = events.length ? `${events.length} appt` : '';

        top.appendChild(num);
        top.appendChild(count);

        const evWrap = document.createElement('div');
        evWrap.className = 'accounts-calendar-events';

        // Limit displayed items per day
        events.slice(0, 3).forEach(ev => {
          const evEl = document.createElement('div');
          evEl.className = 'accounts-calendar-event';
          evEl.innerHTML = `<strong>${ev.patientName || 'Appointment'}</strong><span>${ev.timeLabel || ''} • ${ev.status || ''}</span>`;
          evWrap.appendChild(evEl);
        });

        cell.appendChild(top);
        cell.appendChild(evWrap);
        calendarGrid.appendChild(cell);
      }

    }


    function loadAppointments() {
      const formData = new FormData();
      formData.append('action', 'fetch');

      fetch('admin_pages/manage-appointments.php', {
        method: 'POST',
        body: formData
      })
        .then(response => response.text())
        .then(html => {
          appointmentsTableBody.innerHTML = html;
          allAppointments = parseAppointmentsFromRows();
          filterAppointments();
          if (calendarView && !calendarView.hidden) {
            renderCalendar({ monthDate: calendarMonthCursor || new Date() });
          }
        })
        .catch(() => {
          appointmentsTableBody.innerHTML = `
            <tr>
              <td colspan="7" style="padding:10px; text-align:center;">
                Failed to load appointments.
              </td>
            </tr>
          `;
          allAppointments = [];
        });
    }


    if (appointmentsSearch) {
      appointmentsSearch.addEventListener('input', function () {
        filterAppointments();
        // If calendar is visible, refresh it with the same filter
        applyCalendarFilterAndRender();
      });
    }


    if (showAppointmentForm) {
      showAppointmentForm.addEventListener('click', function () {
        setFormVisible(true);
        document.getElementById('appointmentProcedure')?.focus();
      });
    }

    if (cancelAppointmentForm) {
      cancelAppointmentForm.addEventListener('click', function () {
        appointmentForm.reset();
        setFormVisible(false);
      });
    }

    appointmentForm.addEventListener('submit', function (e) {
      e.preventDefault();

      const formData = new FormData(appointmentForm);

      fetch('admin_pages/manage-appointments.php', {
        method: 'POST',
        body: formData
      })
        .then(response => response.text())
        .then(message => {
          alert(message);
          appointmentForm.reset();
          setFormVisible(false);
          loadAppointments();
        })
        .catch(() => {
          alert('Failed to save appointment.');
        });
    });

    appointmentsTableBody.addEventListener('change', function (e) {
      if (!e.target.classList.contains('appointment-status-select')) return;


      const id = e.target.dataset.id;
      const status = e.target.value;
      const formData = new FormData();
      formData.append('action', 'update_status');
      formData.append('id', id);
      formData.append('status', status);

      fetch('admin_pages/manage-appointments.php', {
        method: 'POST',
        body: formData
      })
        .then(response => response.text())
        .then(message => {
          alert(message);
          loadAppointments();
        })
        .catch(() => {
          alert('Failed to update appointment status.');
          loadAppointments();
        });
    });

    // Calendar navigation + view toggles
    function setCalendarView(mode) {
      if (calendarView) calendarView.hidden = mode !== 'calendar';
      if (tableView) tableView.hidden = mode !== 'table';

      if (mode === 'calendar') {
        if (!calendarMonthCursor) calendarMonthCursor = new Date();
        renderCalendar({ monthDate: calendarMonthCursor });
      }
    }

    if (calendarPrev) {
      calendarPrev.addEventListener('click', function () {
        if (!calendarMonthCursor) calendarMonthCursor = new Date();
        calendarMonthCursor = new Date(calendarMonthCursor.getFullYear(), calendarMonthCursor.getMonth() - 1, 1);
        renderCalendar({ monthDate: calendarMonthCursor });
      });
    }

    if (calendarNext) {
      calendarNext.addEventListener('click', function () {
        if (!calendarMonthCursor) calendarMonthCursor = new Date();
        calendarMonthCursor = new Date(calendarMonthCursor.getFullYear(), calendarMonthCursor.getMonth() + 1, 1);
        renderCalendar({ monthDate: calendarMonthCursor });
      });
    }

    if (showCalendarBtn) {
      showCalendarBtn.addEventListener('click', function () {
        setCalendarView('calendar');
      });
    }

    if (showTableBtn) {
      showTableBtn.addEventListener('click', function () {
        setCalendarView('table');
      });
    }

    // Default mode: calendar visible if it exists
    // (depends on markup hidden state)
    if (calendarView && tableView) {
      if (!calendarView.hidden) setCalendarView('calendar');
      else setCalendarView('table');
    }

    loadAppointments();
  }


  function setActive(page) {
    links.forEach(l => l.classList.toggle('active', l.dataset.page === page));

    const titles = {
      dashboard: 'Dashboard',
      staff: 'Manage Staff / Employee Accounts',
      appointments: 'Schedules / Appointments',
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
      appointments: 'admin_pages/manage-appointments.html',
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

        if (page === 'appointments') {
          initManageAppointments();
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
