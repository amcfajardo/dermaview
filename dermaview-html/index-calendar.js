// Simple appointment calendar for the public home page.
// It fetches staff appointments from the same endpoint used by the admin list.

function getCurrentMonthCursor() {
  const d = new Date();
  d.setDate(1);
  d.setHours(0, 0, 0, 0);
  return d;
}

function formatMonthLabel(d) {
  return d.toLocaleDateString("en-US", { month: "long", year: "numeric" });
}

function parseMonthAppointmentsFromAdminRows(html) {
  const container = document.createElement("div");
  container.innerHTML = html;

  const rows = container.querySelectorAll("tr");
  const structured = [];

  rows.forEach((row) => {
    const title = row.getAttribute("title") || "";
    const tds = row.querySelectorAll("td");
    if (!tds || tds.length < 6) return;

    const dateStrong = tds[0]?.querySelector("strong");
    const timeSpan = tds[0]?.querySelector(".table-muted");

    const patientTd = tds[1];
    const procedureTd = tds[3];

    const statusChip = tds[4]?.querySelector(".appointment-status");
    const statusSelect = row.querySelector("select.appointment-status-select");
    const status = (statusChip?.textContent || statusSelect?.value || "").trim();

    const sourceTd = tds[5];

    const dateLabel = (dateStrong?.textContent || "").trim(); // e.g. "May 22, 2026"
    const timeLabel = (timeSpan?.textContent || "").trim(); // e.g. "9:00 AM"
    if (!dateLabel) return;

    const dayDate = new Date(dateLabel);
    if (Number.isNaN(dayDate.getTime())) return;

    // Parse timeLabel "9:00 AM".
    let hours = 0;
    let minutes = 0;
    const timeMatch = timeLabel.match(/(\d{1,2}):(\d{2})\s*(AM|PM)/i);
    if (timeMatch) {
      hours = parseInt(timeMatch[1], 10);
      minutes = parseInt(timeMatch[2], 10);
      const ap = timeMatch[3].toUpperCase();
      if (ap === "PM" && hours !== 12) hours += 12;
      if (ap === "AM" && hours === 12) hours = 0;
    }

    structured.push({
      isoDate: dayDate.toISOString().slice(0, 10),
      hours,
      minutes,
      timeLabel,
      patientName: (patientTd?.textContent || "").trim(),
      procedureName: (procedureTd?.textContent || "").trim(),
      status,
      source: (sourceTd?.textContent || "").trim(),
      notes: title,
    });
  });

  return structured;
}

function escapeHtml(text) {
  const div = document.createElement("div");
  div.textContent = text || "";
  return div.innerHTML;
}

function ensureModal() {
  if (document.getElementById("mini-cal-modal")) return;

  const modal = document.createElement("div");
  modal.id = "mini-cal-modal";
  modal.className = "mini-cal-modal";
  modal.innerHTML = `
    <div class="mini-cal-modal-content">
      <div class="mini-cal-modal-header">
        <h3 data-modal-title>Appointments</h3>
        <button type="button" class="mini-cal-modal-close" aria-label="Close">&times;</button>
      </div>
      <div class="mini-cal-modal-body" data-modal-body></div>
    </div>
  `;

  document.body.appendChild(modal);

  modal.querySelector(".mini-cal-modal-close").addEventListener("click", closeModal);
  modal.addEventListener("click", (e) => {
    if (e.target === modal) closeModal();
  });
}

function closeModal() {
  const modal = document.getElementById("mini-cal-modal");
  if (modal) modal.classList.remove("active");
}

function showAppointmentsForDay(date, appointments) {
  ensureModal();
  const modal = document.getElementById("mini-cal-modal");
  const title = modal.querySelector("[data-modal-title]");
  const body = modal.querySelector("[data-modal-body]");

  const formattedDate = date.toLocaleDateString("en-US", {
    weekday: "long",
    month: "long",
    day: "numeric",
    year: "numeric",
  });
  title.textContent = formattedDate;

  const isoDate = date.toISOString().slice(0, 10);
  const dayAppointments = appointments
    .filter((a) => a.isoDate === isoDate)
    .sort((a, b) => a.hours * 60 + a.minutes - (b.hours * 60 + b.minutes));

  if (dayAppointments.length === 0) {
    body.innerHTML = `<p class="no-appointments">No appointments scheduled for this day.</p>`;
  } else {
    body.innerHTML = dayAppointments
      .map((apt) => {
        const statusClass = apt.status ? "status-" + apt.status.toLowerCase().replace(/\s+/g, "-") : "";
        const statusHtml = apt.status
          ? `<span class="apt-status ${statusClass}">${escapeHtml(apt.status)}</span>`
          : "";

        return `
          <div class="appointment-detail-card">
            <div class="apt-time">${escapeHtml(apt.timeLabel || "")}</div>
            <div class="apt-info">
              <div class="apt-patient">${escapeHtml(apt.patientName || "")}</div>
              <div class="apt-procedure">${escapeHtml(apt.procedureName || "")}</div>
              ${statusHtml}
            </div>
          </div>
        `;
      })
      .join("");
  }

  modal.classList.add("active");
}

function renderMiniCalendar({ mount, monthDate, appointments }) {
  const year = monthDate.getFullYear();
  const month = monthDate.getMonth();

  const firstOfMonth = new Date(year, month, 1);
  const startDay = firstOfMonth.getDay(); // 0=Sun
  const todayIso = new Date().toISOString().slice(0, 10);

  const weekdays = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];

  mount.querySelector("[data-cal-month-label]").textContent = formatMonthLabel(monthDate);

  const grid = mount.querySelector("[data-cal-grid]");
  grid.innerHTML = "";

  weekdays.forEach((d) => {
    const el = document.createElement("div");
    el.textContent = d;
    el.className = "mini-cal-weekday";
    grid.appendChild(el);
  });

  // 6 rows of days
  const totalCells = 42;
  const outsideStartDate = new Date(year, month, 1 - startDay);

  const byDate = new Map();
  appointments.forEach((a) => {
    if (!byDate.has(a.isoDate)) byDate.set(a.isoDate, []);
    byDate.get(a.isoDate).push(a);
  });

  for (let i = 0; i < totalCells; i++) {
    const d = new Date(outsideStartDate);
    d.setDate(outsideStartDate.getDate() + i);

    const iso = d.toISOString().slice(0, 10);
    const isOutside = d.getMonth() !== month;
    const isToday = iso === todayIso;

    const events = byDate.get(iso) || [];
    events.sort((a, b) => a.hours * 60 + a.minutes - (b.hours * 60 + b.minutes));

    const cell = document.createElement("div");
    cell.className =
      "mini-cal-day" +
      (isOutside ? " is-outside" : "") +
      (isToday ? " is-today" : "") +
      (events.length ? " has-appointments" : "");
    cell.dataset.date = iso;

    const num = document.createElement("div");
    num.className = "mini-cal-day-num";
    num.textContent = d.getDate();

    const count = document.createElement("div");
    count.className = "mini-cal-day-count";
    count.textContent = events.length ? String(events.length) : "";

    const ev = document.createElement("div");
    ev.className = "mini-cal-day-events";
    if (events.length) {
      const top = events[0];
      ev.innerHTML = `<span>${escapeHtml(top.timeLabel || "")}</span>`;
    }

    cell.appendChild(num);
    cell.appendChild(count);
    cell.appendChild(ev);

    if (events.length > 0) {
      cell.style.cursor = "pointer";
      cell.addEventListener("click", () => showAppointmentsForDay(d, appointments));
    }

    grid.appendChild(cell);
  }
}

function initIndexCalendar() {
  const mount = document.querySelector("[data-mini-appointment-calendar]");
  if (!mount) return;

  let monthCursor = getCurrentMonthCursor();
  const prevBtn = mount.querySelector("[data-cal-prev]");
  const nextBtn = mount.querySelector("[data-cal-next]");

  let appointments = [];

  function render() {
    renderMiniCalendar({ mount, monthDate: monthCursor, appointments });
  }

  function load() {
    const formData = new FormData();
    formData.append("action", "fetch");

    fetch("admin_pages/manage-appointments.php", { method: "POST", body: formData })
      .then((r) => r.text())
      .then((html) => {
        appointments = parseMonthAppointmentsFromAdminRows(html);
        render();
      })
      .catch(() => {
        appointments = [];
        render();
      });
  }

  if (prevBtn)
    prevBtn.addEventListener("click", () => {
      monthCursor = new Date(monthCursor.getFullYear(), monthCursor.getMonth() - 1, 1);
      render();
    });

  if (nextBtn)
    nextBtn.addEventListener("click", () => {
      monthCursor = new Date(monthCursor.getFullYear(), monthCursor.getMonth() + 1, 1);
      render();
    });

  render();
  load();
}

document.addEventListener("DOMContentLoaded", initIndexCalendar);

