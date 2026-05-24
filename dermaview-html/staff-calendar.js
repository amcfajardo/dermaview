function staffCalEscapeHtml(text) {
  const div = document.createElement('div');
  div.textContent = text || '';
  return div.innerHTML;
}

function staffCalIsoDate(date) {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, '0');
  const day = String(date.getDate()).padStart(2, '0');
  return `${year}-${month}-${day}`;
}

function staffCalEndpoint() {
  return window.location.pathname.includes('/pages/')
    ? '../admin_pages/admin-appointments.php'
    : 'admin_pages/admin-appointments.php';
}

function staffCalFromJsonRows(rows) {
  return rows.map(row => {
    const timeParts = String(row.appointment_time || '00:00:00').split(':');
    return {
      isoDate: row.appointment_date,
      hours: parseInt(timeParts[0] || '0', 10),
      minutes: parseInt(timeParts[1] || '0', 10),
      timeLabel: row.time_label || row.appointment_time || '',
      patientName: row.patient_name || '',
      contact: [row.phone || '', row.email || ''].filter(Boolean).join('\n'),
      procedureName: row.procedure_name || '',
      status: row.status || '',
      source: row.source || '',
      notes: row.notes || ''
    };
  });
}

function staffCalParseFromAdminRows(html) {
  const container = document.createElement('div');
  container.innerHTML = html;
  const rows = container.querySelectorAll('tr');

  const structured = [];

  rows.forEach(row => {
    const title = row.getAttribute('title') || '';
    const tds = row.querySelectorAll('td');
    if (!tds || tds.length < 6) return;

    const dateStrong = tds[0]?.querySelector('strong');
    const timeSpan = tds[0]?.querySelector('.table-muted');

    const patientTd = tds[1];
    const contactTd = tds[2];
    const contactMuted = contactTd?.querySelector('.table-muted');
    const procedureTd = tds[3];

    const statusChip = tds[4]?.querySelector('.appointment-status');
    const statusSelect = row.querySelector('select.appointment-status-select');
    const status = (statusChip?.textContent || statusSelect?.value || '').trim();

    const sourceTd = tds[5];

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
      isoDate: staffCalIsoDate(dayDate),
      hours,
      minutes,
      timeLabel,
      patientName: (patientTd?.textContent || '').trim(),
      contact: [
        (contactTd?.childNodes?.[0]?.textContent || '').trim(),
        (contactMuted?.textContent || '').trim()
      ].filter(Boolean).join('\n'),
      procedureName: (procedureTd?.textContent || '').trim(),
      status,
      source: (sourceTd?.textContent || '').trim(),
      notes: title
    });
  });

  return structured;
}

function staffCalAppointmentCards(appointments) {
  if (!appointments.length) {
    return '<p class="no-appointments">No appointments scheduled for this day.</p>';
  }

  return appointments.map(apt => {
    const statusKey = apt.status ? apt.status.toLowerCase().replace(/\s+/g, '-') : '';
    return `
      <div class="appointment-detail-card">
        <div class="apt-time">${staffCalEscapeHtml(apt.timeLabel || '')}</div>
        <div class="apt-info">
          <div class="apt-patient">${staffCalEscapeHtml(apt.patientName || '')}</div>
          <div class="apt-procedure">${staffCalEscapeHtml(apt.procedureName || '')}</div>
          ${apt.contact ? `<div class="apt-contact">${staffCalEscapeHtml(apt.contact)}</div>` : ''}
          ${apt.status ? `<span class="apt-status status-${statusKey}">${staffCalEscapeHtml(apt.status)}</span>` : ''}
        </div>
      </div>
    `;
  }).join('');
}

function staffCalAppointmentsForDate(appointments, isoDate) {
  return appointments
    .filter(a => a.isoDate === isoDate)
    .sort((a, b) => a.hours * 60 + a.minutes - (b.hours * 60 + b.minutes));
}

function staffCalRenderDayList({ mount, selectedDateIso, appointments }) {
  const title = mount.querySelector('[data-staffcal-list-title]');
  const list = mount.querySelector('[data-staffcal-list]');

  if (!title || !list) return;

  const selectedDate = new Date(`${selectedDateIso}T00:00:00`);
  const dayAppointments = staffCalAppointmentsForDate(appointments, selectedDateIso);

  title.textContent = selectedDate.toLocaleDateString('en-US', {
    weekday: 'long',
    month: 'long',
    day: 'numeric',
    year: 'numeric'
  });
  list.innerHTML = staffCalAppointmentCards(dayAppointments);
}

function staffCalRenderMonth({ mount, cursor, appointments, selectedDateIso, onSelectDate }) {
  const grid = mount.querySelector('[data-staffcal-grid]');
  const monthLabel = mount.querySelector('[data-staffcal-month]');

  const year = cursor.getFullYear();
  const month = cursor.getMonth();

  const firstOfMonth = new Date(year, month, 1);
  const startDay = firstOfMonth.getDay();
  const todayIso = staffCalIsoDate(new Date());

  const totalCells = 42;
  const outsideStartDate = new Date(year, month, 1 - startDay);

  monthLabel.textContent = cursor.toLocaleDateString('en-US', { month: 'long', year: 'numeric' });
  grid.innerHTML = '';

  const weekdays = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
  weekdays.forEach(d => {
    const el = document.createElement('div');
    el.className = 'staff-cal-weekday';
    el.textContent = d;
    grid.appendChild(el);
  });

  const byDate = new Map();
  appointments.forEach(a => {
    if (!byDate.has(a.isoDate)) byDate.set(a.isoDate, []);
    byDate.get(a.isoDate).push(a);
  });

  for (let i = 0; i < totalCells; i++) {
    const d = new Date(outsideStartDate);
    d.setDate(outsideStartDate.getDate() + i);

    const iso = staffCalIsoDate(d);
    const isOutside = d.getMonth() !== month;
    const isToday = iso === todayIso;
    const isSelected = iso === selectedDateIso;

    const events = byDate.get(iso) || [];
    events.sort((a, b) => a.hours * 60 + a.minutes - (b.hours * 60 + b.minutes));

    const cell = document.createElement('div');
    cell.className = 'staff-cal-day' +
      (isOutside ? ' is-outside' : '') +
      (isToday ? ' is-today' : '') +
      (isSelected ? ' is-selected' : '') +
      (events.length ? ' has-appointments' : '');
    cell.dataset.date = iso;

    const num = document.createElement('div');
    num.className = 'staff-cal-day-num';
    num.textContent = d.getDate();

    const count = document.createElement('div');
    count.className = 'staff-cal-day-count';
    count.textContent = events.length ? String(events.length) : '';

    const ev = document.createElement('div');
    ev.className = 'staff-cal-day-events';
    if (events.length) {
      ev.innerHTML = '<span>' + staffCalEscapeHtml(events[0].timeLabel || '') + '</span>';
    }

    cell.appendChild(num);
    cell.appendChild(count);
    cell.appendChild(ev);

    cell.addEventListener('click', () => onSelectDate(iso));

    grid.appendChild(cell);
  }
}

function staffCalEnsureModal() {
  if (document.getElementById('staffcal-modal')) return;

  const modal = document.createElement('div');
  modal.id = 'staffcal-modal';
  modal.className = 'staff-cal-modal';

  modal.innerHTML = `
    <div class="staff-cal-modal-content">
      <div class="staff-cal-modal-header">
        <h3 data-staffcal-modal-title>Appointments</h3>
        <button type="button" class="staff-cal-modal-close" aria-label="Close">&times;</button>
      </div>
      <div class="staff-cal-modal-body" data-staffcal-modal-body></div>
    </div>
  `;

  document.body.appendChild(modal);
  modal.querySelector('.staff-cal-modal-close').addEventListener('click', () => modal.classList.remove('active'));
  modal.addEventListener('click', (e) => {
    if (e.target === modal) modal.classList.remove('active');
  });
}

function staffCalShowDayModal({ date, appointments }) {
  staffCalEnsureModal();
  const modal = document.getElementById('staffcal-modal');
  const title = modal.querySelector('[data-staffcal-modal-title]');
  const body = modal.querySelector('[data-staffcal-modal-body]');

  title.textContent = date.toLocaleDateString('en-US', { weekday: 'long', month: 'long', day: 'numeric', year: 'numeric' });

  const isoDate = staffCalIsoDate(date);
  body.innerHTML = staffCalAppointmentCards(staffCalAppointmentsForDate(appointments, isoDate));

  modal.classList.add('active');
}

function initStaffCalendar() {
  const mount = document.querySelector('[data-staffcal]');
  if (!mount) return;

  let cursor = new Date();
  cursor.setDate(1);
  cursor.setHours(0, 0, 0, 0);

  let appointments = [];
  let selectedDateIso = staffCalIsoDate(new Date());

  const prevBtn = mount.querySelector('[data-staffcal-prev]');
  const nextBtn = mount.querySelector('[data-staffcal-next]');

  function render() {
    staffCalRenderMonth({
      mount,
      cursor,
      appointments,
      selectedDateIso,
      onSelectDate: (isoDate) => {
        selectedDateIso = isoDate;
        render();
      }
    });
    staffCalRenderDayList({ mount, selectedDateIso, appointments });
  }

  function load() {
    const fd = new FormData();
    fd.append('action', 'fetch_json');

    fetch(staffCalEndpoint(), { method: 'POST', body: fd })
      .then(r => r.json())
      .then(data => {
        appointments = staffCalFromJsonRows(data.appointments || []);
        render();
      })
      .catch(() => {
        appointments = [];
        render();
      });
  }

  if (prevBtn) prevBtn.addEventListener('click', () => {
    cursor = new Date(cursor.getFullYear(), cursor.getMonth() - 1, 1);
    render();
  });

  if (nextBtn) nextBtn.addEventListener('click', () => {
    cursor = new Date(cursor.getFullYear(), cursor.getMonth() + 1, 1);
    render();
  });

  render();
  load();
}

document.addEventListener('DOMContentLoaded', initStaffCalendar);

