(function () {
  function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text || '';
    return div.innerHTML;
  }

  window.initManageAppointments = function () {
    const appointmentsTableBody = document.getElementById('appointmentsTableBody');
    const appointmentsSearch = document.getElementById('appointmentsSearch');
    const calendarView = document.getElementById('calendarView');
    const tableView = document.getElementById('tableView');
    const calendarGrid = document.getElementById('calendarGrid');
    const calendarMonthLabel = document.getElementById('calendarMonthLabel');
    const calendarPrev = document.getElementById('calendarPrev');
    const calendarNext = document.getElementById('calendarNext');
    const showCalendarBtn = document.getElementById('showCalendarBtn');
    const showTableBtn = document.getElementById('showTableBtn');
    const upcomingCount = document.getElementById('upcomingAppointmentsCount');
    const pendingCount = document.getElementById('pendingAppointmentsCount');
    const confirmedCount = document.getElementById('confirmedAppointmentsCount');
    const completedCount = document.getElementById('completedAppointmentsCount');
    const cancelledCount = document.getElementById('cancelledAppointmentsCount');
    const assignedStaffCount = document.getElementById('assignedStaffCount');

    if (!appointmentsTableBody) return;

    let allAppointments = [];
    let calendarMonthCursor = null;

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

    function parseAppointmentsFromRows() {
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
        const assignedTd = tds[4];
        const statusChip = tds[5]?.querySelector('.appointment-status');
        const sourceTd = tds[6];
        const statusSelect = row.querySelector('select.appointment-status-select');
        const dateLabel = (dateStrong?.textContent || '').trim();
        const timeLabel = (timeSpan?.textContent || '').trim();

        if (!dateLabel) return;

        const dayDate = new Date(dateLabel);
        if (Number.isNaN(dayDate.getTime())) return;

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

        structured.push({
          id: statusSelect?.dataset?.id ? Number(statusSelect.dataset.id) : null,
          isoDate: dayDate.toISOString().slice(0, 10),
          timeLabel,
          hours,
          minutes,
          patientName: (patientTd?.textContent || '').trim(),
          procedureName: (procedureTd?.textContent || '').trim(),
          assignedStaff: (assignedTd?.textContent || '').trim(),
          status: (statusChip?.textContent || statusSelect?.value || '').trim(),
          source: (sourceTd?.textContent || '').trim(),
          notes: title,
          phoneOrEmail: (contactTd?.textContent || '').trim()
        });
      });

      return structured;
    }

    function renderAppointmentSummary() {
      const today = new Date().toISOString().slice(0, 10);
      const upcoming = allAppointments.filter(item => item.isoDate >= today && !['Cancelled', 'Completed', 'No Show'].includes(item.status)).length;
      const pending = allAppointments.filter(item => item.status === 'Pending').length;
      const confirmed = allAppointments.filter(item => item.status === 'Confirmed').length;
      const completed = allAppointments.filter(item => item.status === 'Completed').length;
      const cancelled = allAppointments.filter(item => item.status === 'Cancelled' || item.status === 'No Show').length;
      const assigned = new Set(allAppointments.map(item => item.assignedStaff).filter(name => name && name !== 'Unassigned')).size;

      if (upcomingCount) upcomingCount.textContent = String(upcoming);
      if (pendingCount) pendingCount.textContent = String(pending);
      if (confirmedCount) confirmedCount.textContent = String(confirmed);
      if (completedCount) completedCount.textContent = String(completed);
      if (cancelledCount) cancelledCount.textContent = String(cancelled);
      if (assignedStaffCount) assignedStaffCount.textContent = String(assigned);
    }

    function closeCalendarModal() {
      document.querySelector('.accounts-calendar-modal')?.remove();
      document.body.classList.remove('calendar-modal-open');
    }

    function openCalendarDayModal(date, events) {
      closeCalendarModal();

      const title = date.toLocaleDateString('en-US', {
        weekday: 'long',
        month: 'long',
        day: 'numeric',
        year: 'numeric'
      });

      const modal = document.createElement('div');
      modal.className = 'accounts-calendar-modal';
      modal.innerHTML = `
        <div class="accounts-calendar-dialog" role="dialog" aria-modal="true" aria-label="${escapeHtml(title)} appointments">
          <div class="accounts-calendar-dialog-header">
            <div>
              <span class="section-kicker">Schedule</span>
              <h3>${escapeHtml(title)}</h3>
            </div>
            <button type="button" class="accounts-calendar-dialog-close" aria-label="Close">&times;</button>
          </div>
          <div class="accounts-calendar-dialog-list">
            ${events.length ? events.map(event => `
              <article class="accounts-calendar-dialog-event">
                <div class="accounts-calendar-dialog-time">${escapeHtml(event.timeLabel || 'No time')}</div>
                <div class="accounts-calendar-dialog-main">
                  <strong>${escapeHtml(event.patientName || 'Appointment')}</strong>
                  <span>${escapeHtml(event.procedureName || 'No procedure')}</span>
                  <small>${escapeHtml(event.assignedStaff || 'Unassigned')} &middot; ${escapeHtml(event.phoneOrEmail || 'No contact')}</small>
                </div>
                <span class="accounts-calendar-dialog-status">${escapeHtml(event.status || 'Pending')}</span>
              </article>
            `).join('') : '<p class="accounts-calendar-empty">No appointments for this date.</p>'}
          </div>
        </div>
      `;

      modal.addEventListener('click', event => {
        if (event.target === modal || event.target.closest('.accounts-calendar-dialog-close')) {
          closeCalendarModal();
        }
      });

      document.addEventListener('keydown', function handleEscape(event) {
        if (event.key === 'Escape') {
          closeCalendarModal();
          document.removeEventListener('keydown', handleEscape);
        }
      });

      document.body.appendChild(modal);
      document.body.classList.add('calendar-modal-open');
    }

    function renderCalendar({ monthDate }) {
      if (!calendarGrid) return;

      calendarMonthCursor = monthDate;
      const year = calendarMonthCursor.getFullYear();
      const month = calendarMonthCursor.getMonth();
      const firstOfMonth = new Date(year, month, 1);
      const startDay = firstOfMonth.getDay();
      const todayIso = new Date().toISOString().slice(0, 10);

      if (calendarMonthLabel) {
        calendarMonthLabel.textContent = calendarMonthCursor.toLocaleDateString('en-US', {
          month: 'long',
          year: 'numeric'
        });
      }

      const weekdays = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
      calendarGrid.innerHTML = '';

      weekdays.forEach(day => {
        const el = document.createElement('div');
        el.textContent = day;
        el.style.fontWeight = '900';
        el.style.color = 'var(--color-text-secondary)';
        el.style.fontSize = '0.9rem';
        el.style.padding = '0 4px 10px';
        calendarGrid.appendChild(el);
      });

      const query = appointmentsSearch ? appointmentsSearch.value.trim().toLowerCase() : '';
      const filtered = query
        ? allAppointments.filter(appointment => {
            const haystack = `${appointment.patientName} ${appointment.procedureName} ${appointment.status} ${appointment.source} ${appointment.notes}`.toLowerCase();
            return haystack.includes(query);
          })
        : allAppointments;

      const byDate = new Map();
      filtered.forEach(appointment => {
        if (!byDate.has(appointment.isoDate)) byDate.set(appointment.isoDate, []);
        byDate.get(appointment.isoDate).push(appointment);
      });

      const totalCells = 42;
      const outsideStartDate = new Date(year, month, 1 - startDay);

      for (let i = 0; i < totalCells; i++) {
        const date = new Date(outsideStartDate);
        date.setDate(outsideStartDate.getDate() + i);

        const iso = date.toISOString().slice(0, 10);
        const isOutside = date.getMonth() !== month;
        const isToday = iso === todayIso;
        const events = byDate.get(iso) || [];
        events.sort((a, b) => (a.hours * 60 + a.minutes) - (b.hours * 60 + b.minutes));

        const cell = document.createElement('div');
        cell.className = 'accounts-calendar-day' + (isOutside ? ' is-outside-month' : '') + (isToday ? ' is-today' : '');

        const top = document.createElement('div');
        top.className = 'accounts-calendar-day-top';

        const num = document.createElement('div');
        num.className = 'accounts-calendar-day-num';
        num.textContent = date.getDate();

        const count = document.createElement('div');
        count.className = 'accounts-calendar-count';
        count.textContent = events.length ? `${events.length} appt` : '';

        top.appendChild(num);
        top.appendChild(count);

        const eventsWrap = document.createElement('div');
        eventsWrap.className = 'accounts-calendar-events';

        events.slice(0, 1).forEach(event => {
          const eventEl = document.createElement('div');
          eventEl.className = 'accounts-calendar-event';
          eventEl.innerHTML = `<strong>${escapeHtml(event.patientName || 'Appointment')}</strong><span>${escapeHtml(event.timeLabel || '')} - ${escapeHtml(event.status || '')}</span>`;
          eventsWrap.appendChild(eventEl);
        });

        if (events.length > 1) {
          const moreEl = document.createElement('div');
          moreEl.className = 'accounts-calendar-more';
          moreEl.textContent = `View all ${events.length}`;
          eventsWrap.appendChild(moreEl);
        }

        if (events.length) {
          cell.tabIndex = 0;
          cell.setAttribute('role', 'button');
          cell.setAttribute('aria-label', `View ${events.length} appointments on ${iso}`);
          cell.addEventListener('click', () => openCalendarDayModal(date, events));
          cell.addEventListener('keydown', event => {
            if (event.key === 'Enter' || event.key === ' ') {
              event.preventDefault();
              openCalendarDayModal(date, events);
            }
          });
        }

        cell.appendChild(top);
        cell.appendChild(eventsWrap);
        calendarGrid.appendChild(cell);
      }
    }

    function loadAppointments() {
      const formData = new FormData();
      formData.append('action', 'fetch');

      fetch('admin-appointments.php', {
        method: 'POST',
        body: formData
      })
        .then(response => response.text())
        .then(html => {
          appointmentsTableBody.innerHTML = html;
          allAppointments = parseAppointmentsFromRows();
          renderAppointmentSummary();
          filterAppointments();

          if (calendarView && !calendarView.hidden) {
            renderCalendar({ monthDate: calendarMonthCursor || new Date() });
          }
        })
        .catch(() => {
          appointmentsTableBody.innerHTML = `
            <tr>
              <td colspan="8" style="padding:10px; text-align:center;">
                Failed to load appointments.
              </td>
            </tr>
          `;
          allAppointments = [];
        });
    }

    function setCalendarView(mode) {
      if (calendarView) calendarView.hidden = mode !== 'calendar';
      if (tableView) tableView.hidden = mode !== 'table';

      if (mode === 'calendar') {
        if (!calendarMonthCursor) calendarMonthCursor = new Date();
        renderCalendar({ monthDate: calendarMonthCursor });
      }
    }

    if (appointmentsSearch) {
      appointmentsSearch.addEventListener('input', function () {
        filterAppointments();
        applyCalendarFilterAndRender();
      });
    }

    appointmentsTableBody.addEventListener('change', function (e) {
      if (!e.target.classList.contains('appointment-status-select')) return;

      const formData = new FormData();
      formData.append('action', 'update_status');
      formData.append('id', e.target.dataset.id);
      formData.append('status', e.target.value);

      fetch('admin-appointments.php', {
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

    if (calendarView && tableView) {
      if (!calendarView.hidden) setCalendarView('calendar');
      else setCalendarView('table');
    }

    loadAppointments();
  };
})();
