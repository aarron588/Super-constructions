let employees = [];
let projects = [];
let toastTimer;

const employeeRows = document.querySelector("#employee-rows");
const attendanceRows = document.querySelector("#attendance-rows");
const employeeModal = document.querySelector("#employee-modal");
const employeeForm = document.querySelector("#employee-form");
const attendanceModal = document.querySelector("#attendance-modal");
const attendanceForm = document.querySelector("#attendance-form");
const search = document.querySelector("#employee-search");
const statusFilter = document.querySelector("#employee-status-filter");

function escapeHtml(value) {
  const span = document.createElement("span");
  span.textContent = value ?? "";
  return span.innerHTML.replace(/"/g, "&quot;").replace(/'/g, "&#39;");
}

function formatCurrency(value) {
  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: 2,
  }).format(Number(value) || 0);
}

function localDateValue() {
  const now = new Date();
  now.setMinutes(now.getMinutes() - now.getTimezoneOffset());
  return now.toISOString().slice(0, 10);
}

function formatDate(value) {
  if (!value) return "—";
  return new Intl.DateTimeFormat("en-IN", { day: "numeric", month: "short", year: "numeric" })
    .format(new Date(`${value}T00:00:00`));
}

function showToast(message) {
  const toast = document.querySelector("#toast");
  toast.textContent = message;
  toast.classList.add("visible");
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => toast.classList.remove("visible"), 2400);
}

function payroll(employee, month) {
  const records = (employee.attendance || []).filter((entry) => entry.date.startsWith(month));
  const days = records.reduce((sum, entry) =>
    sum + (entry.status === "Present" ? 1 : entry.status === "Half day" ? 0.5 : 0), 0);
  const earned = records.reduce((sum, entry) =>
    sum + (entry.status === "Present" ? 1 : entry.status === "Half day" ? 0.5 : 0)
      * Number(entry.daily_wage ?? employee.daily_wage), 0);
  const paid = (employee.salary_payments || [])
    .filter((payment) => payment.month === month)
    .reduce((sum, payment) => sum + Number(payment.amount || 0), 0);
  return { days, earned, paid, due: Math.max(0, earned - paid) };
}

function renderSummary() {
  const today = localDateValue();
  const month = today.slice(0, 7);
  const active = employees.filter((employee) => employee.status === "Active");
  const present = new Set(active.flatMap((employee) =>
    (employee.attendance || [])
      .filter((entry) => entry.date === today && entry.status !== "Absent")
      .map(() => employee.id)
  ));
  const totals = active.reduce((summary, employee) => {
    const current = payroll(employee, month);
    summary.earned += current.earned;
    summary.due += current.due;
    return summary;
  }, { earned: 0, due: 0 });
  document.querySelector("#employee-active-count").textContent = active.length;
  document.querySelector("#employee-present-count").textContent = present.size;
  document.querySelector("#payroll-earned").textContent = formatCurrency(totals.earned);
  document.querySelector("#payroll-due").textContent = formatCurrency(totals.due);
  document.querySelector("#payroll-month-label").textContent = new Intl.DateTimeFormat("en-IN", {
    month: "long",
    year: "numeric",
  }).format(new Date(`${month}-01T00:00:00`));
}

function renderEmployees() {
  const query = search.value.trim().toLowerCase();
  const status = statusFilter.value;
  const month = localDateValue().slice(0, 7);
  const filtered = employees.filter((employee) => {
    const matchesStatus = status === "All" || employee.status === status;
    const searchable = [employee.id, employee.name, employee.phone, employee.role].join(" ").toLowerCase();
    return matchesStatus && searchable.includes(query);
  });
  employeeRows.innerHTML = filtered.length
    ? filtered.map((employee) => {
      const current = payroll(employee, month);
      const statusClass = employee.status === "Active" ? "green" : "neutral";
      const payAction = current.due > 0
        ? `<a class="row-button payment" href="/payments?type=Salary&employee_id=${encodeURIComponent(employee.id)}&month=${encodeURIComponent(month)}">Pay salary</a>`
        : "";
      return `<tr>
        <td><div class="project-cell"><span class="employee-avatar" aria-hidden="true">${escapeHtml(employee.name.slice(0, 1).toUpperCase())}</span><div><strong>${escapeHtml(employee.name)}</strong><small>${escapeHtml(employee.id)} · ${escapeHtml(employee.phone || "No phone")}</small></div></div></td>
        <td>${escapeHtml(employee.role)}</td><td>${formatCurrency(employee.daily_wage)}</td><td>${current.days}</td>
        <td>${formatCurrency(current.earned)}</td><td>${formatCurrency(current.paid)}</td><td><strong class="${current.due > 0 ? "balance-due" : "balance-clear"}">${formatCurrency(current.due)}</strong></td>
        <td><span class="project-status ${statusClass}">${escapeHtml(employee.status)}</span></td>
        <td><div class="row-actions">${payAction}<button type="button" class="row-button attendance" data-attendance="${escapeHtml(employee.id)}">Mark attendance</button><button type="button" class="row-button edit" data-edit="${escapeHtml(employee.id)}">Edit</button><button type="button" class="row-button delete" data-delete="${escapeHtml(employee.id)}">Delete</button></div></td>
      </tr>`;
    }).join("")
    : `<tr><td colspan="9" class="empty-state">${employees.length ? "No employees match this filter." : "No employees yet. Add a worker or employee to begin."}</td></tr>`;
}

function renderAttendance() {
  const records = employees.flatMap((employee) => (employee.attendance || []).map((entry) => ({ employee, entry })))
    .sort((a, b) => b.entry.date.localeCompare(a.entry.date))
    .slice(0, 100);
  attendanceRows.innerHTML = records.length
    ? records.map(({ employee, entry }) => `<tr>
        <td>${formatDate(entry.date)}</td><td><strong class="expense-project-name">${escapeHtml(employee.name)}</strong><small class="expense-project-id">${escapeHtml(employee.id)}</small></td>
        <td>${escapeHtml(entry.project_name || "General / not assigned")}</td>
        <td><span class="project-status ${entry.status === "Present" ? "green" : entry.status === "Half day" ? "orange" : "neutral"}">${escapeHtml(entry.status)}</span></td>
        <td>${escapeHtml(entry.notes || "—")}</td>
        <td><div class="row-actions"><button type="button" class="row-button edit" data-edit-attendance="${escapeHtml(employee.id)}|${escapeHtml(entry.id)}">Edit</button><button type="button" class="row-button delete" data-delete-attendance="${escapeHtml(employee.id)}|${escapeHtml(entry.id)}">Delete</button></div></td>
      </tr>`).join("")
    : '<tr><td colspan="6" class="empty-state">Attendance records will appear after you mark a work day.</td></tr>';
}

async function loadData() {
  try {
    const [employeeResponse, projectResponse] = await Promise.all([
      fetch("/api/employees"),
      fetch("/api/projects"),
    ]);
    if (!employeeResponse.ok || !projectResponse.ok) throw new Error("Could not load employees and projects");
    employees = await employeeResponse.json();
    projects = await projectResponse.json();
    document.querySelector("#attendance-project").innerHTML = `<option value="">General / not assigned</option>${projects.map((project) =>
      `<option value="${escapeHtml(project.id)}">${escapeHtml(project.name)} · ${escapeHtml(project.id)}</option>`
    ).join("")}`;
    renderSummary();
    renderEmployees();
    renderAttendance();
    return true;
  } catch (error) {
    employeeRows.innerHTML = '<tr><td colspan="9" class="empty-state">Could not load employees. Check the server and try again.</td></tr>';
    attendanceRows.innerHTML = '<tr><td colspan="6" class="empty-state">Could not load attendance.</td></tr>';
    console.error(error);
    return false;
  }
}

function openEmployeeModal(employee = null) {
  employeeForm.reset();
  document.querySelector("#employee-form-error").textContent = "";
  document.querySelector("#employee-modal-title").textContent = employee ? "Edit employee" : "Add employee";
  document.querySelector("#employee-id").value = employee?.id || "";
  document.querySelector("#employee-name").value = employee?.name || "";
  document.querySelector("#employee-phone").value = employee?.phone || "";
  document.querySelector("#employee-role").value = employee?.role || "";
  document.querySelector("#employee-wage").value = employee?.daily_wage ?? "";
  document.querySelector("#employee-joined").value = employee?.joined_on || localDateValue();
  document.querySelector("#employee-status").value = employee?.status || "Active";
  employeeModal.classList.add("open");
  employeeModal.setAttribute("aria-hidden", "false");
  setTimeout(() => document.querySelector("#employee-name").focus(), 100);
}

function closeEmployeeModal() {
  employeeModal.classList.remove("open");
  employeeModal.setAttribute("aria-hidden", "true");
}

function openAttendanceModal(employee, entry = null) {
  attendanceForm.reset();
  document.querySelector("#attendance-form-error").textContent = "";
  document.querySelector("#attendance-modal-title").textContent = entry ? "Edit attendance" : "Record attendance";
  document.querySelector("#attendance-employee-id").value = employee.id;
  document.querySelector("#attendance-id").value = entry?.id || "";
  document.querySelector("#attendance-employee-name").textContent = `${employee.name} · ${employee.role}`;
  document.querySelector("#attendance-date").value = entry?.date || localDateValue();
  document.querySelector("#attendance-status").value = entry?.status || "Present";
  document.querySelector("#attendance-project").value = entry?.project_id || "";
  document.querySelector("#attendance-notes").value = entry?.notes || "";
  attendanceModal.classList.add("open");
  attendanceModal.setAttribute("aria-hidden", "false");
}

function closeAttendanceModal() {
  attendanceModal.classList.remove("open");
  attendanceModal.setAttribute("aria-hidden", "true");
}

document.querySelector("#add-employee").addEventListener("click", () => openEmployeeModal());
document.querySelector("#employee-modal-close").addEventListener("click", closeEmployeeModal);
document.querySelector("#employee-cancel").addEventListener("click", closeEmployeeModal);
employeeModal.addEventListener("click", (event) => { if (event.target === employeeModal) closeEmployeeModal(); });
document.querySelector("#attendance-modal-close").addEventListener("click", closeAttendanceModal);
document.querySelector("#attendance-cancel").addEventListener("click", closeAttendanceModal);
attendanceModal.addEventListener("click", (event) => { if (event.target === attendanceModal) closeAttendanceModal(); });
document.addEventListener("keydown", (event) => {
  if (event.key === "Escape") {
    closeEmployeeModal();
    closeAttendanceModal();
  }
});

employeeForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const button = employeeForm.querySelector('button[type="submit"]');
  button.disabled = true;
  const id = document.querySelector("#employee-id").value;
  const payload = {
    name: document.querySelector("#employee-name").value.trim(),
    phone: document.querySelector("#employee-phone").value.trim(),
    role: document.querySelector("#employee-role").value.trim(),
    daily_wage: Number(document.querySelector("#employee-wage").value),
    joined_on: document.querySelector("#employee-joined").value,
    status: document.querySelector("#employee-status").value,
  };
  try {
    const response = await fetch(id ? `/api/employees/${encodeURIComponent(id)}` : "/api/employees", {
      method: id ? "PUT" : "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const result = await response.json();
    if (!response.ok) throw new Error(result.error || "Could not save employee");
    closeEmployeeModal();
    showToast((await loadData()) ? (id ? "Employee updated." : "Employee added.") : "Employee saved, but the list could not refresh.");
  } catch (error) {
    document.querySelector("#employee-form-error").textContent = error.message;
  } finally {
    button.disabled = false;
  }
});

attendanceForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const button = attendanceForm.querySelector('button[type="submit"]');
  button.disabled = true;
  const employeeId = document.querySelector("#attendance-employee-id").value;
  const attendanceId = document.querySelector("#attendance-id").value;
  const payload = {
    date: document.querySelector("#attendance-date").value,
    status: document.querySelector("#attendance-status").value,
    project_id: document.querySelector("#attendance-project").value,
    notes: document.querySelector("#attendance-notes").value.trim(),
  };
  try {
    const response = await fetch(`/api/employees/${encodeURIComponent(employeeId)}/attendance${attendanceId ? `/${encodeURIComponent(attendanceId)}` : ""}`, {
      method: attendanceId ? "PUT" : "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const result = await response.json();
    if (!response.ok) throw new Error(result.error || "Could not save attendance");
    closeAttendanceModal();
    showToast((await loadData()) ? "Attendance saved." : "Attendance saved, but the list could not refresh.");
  } catch (error) {
    document.querySelector("#attendance-form-error").textContent = error.message;
  } finally {
    button.disabled = false;
  }
});

employeeRows.addEventListener("click", async (event) => {
  const attendanceButton = event.target.closest("[data-attendance]");
  const editButton = event.target.closest("[data-edit]");
  const deleteButton = event.target.closest("[data-delete]");
  if (attendanceButton) {
    const employee = employees.find((item) => item.id === attendanceButton.dataset.attendance);
    if (employee) openAttendanceModal(employee);
    return;
  }
  if (editButton) {
    const employee = employees.find((item) => item.id === editButton.dataset.edit);
    if (employee) openEmployeeModal(employee);
    return;
  }
  if (deleteButton) {
    const employee = employees.find((item) => item.id === deleteButton.dataset.delete);
    if (!employee || !confirm(`Delete employee "${employee.name}"?`)) return;
    try {
      const response = await fetch(`/api/employees/${encodeURIComponent(employee.id)}`, { method: "DELETE" });
      const result = await response.json();
      if (!response.ok) throw new Error(result.error || "Could not delete employee");
      showToast((await loadData()) ? "Employee deleted." : "Employee deleted, but the list could not refresh.");
    } catch (error) {
      showToast(error.message);
    }
  }
});

attendanceRows.addEventListener("click", async (event) => {
  const editButton = event.target.closest("[data-edit-attendance]");
  const deleteButton = event.target.closest("[data-delete-attendance]");
  if (editButton) {
    const [employeeId, attendanceId] = editButton.dataset.editAttendance.split("|");
    const employee = employees.find((item) => item.id === employeeId);
    const entry = employee?.attendance.find((item) => item.id === attendanceId);
    if (employee && entry) openAttendanceModal(employee, entry);
    return;
  }
  if (deleteButton) {
    const [employeeId, attendanceId] = deleteButton.dataset.deleteAttendance.split("|");
    const employee = employees.find((item) => item.id === employeeId);
    const entry = employee?.attendance.find((item) => item.id === attendanceId);
    if (!employee || !entry || !confirm(`Delete attendance for ${employee.name} on ${formatDate(entry.date)}?`)) return;
    try {
      const response = await fetch(`/api/employees/${encodeURIComponent(employeeId)}/attendance/${encodeURIComponent(attendanceId)}`, { method: "DELETE" });
      const result = await response.json();
      if (!response.ok) throw new Error(result.error || "Could not delete attendance");
      showToast((await loadData()) ? "Attendance deleted." : "Attendance deleted, but the list could not refresh.");
    } catch (error) {
      showToast(error.message);
    }
  }
});

search.addEventListener("input", renderEmployees);
statusFilter.addEventListener("change", renderEmployees);
const menuButton = document.querySelector("#menu-button");
const sidebar = document.querySelector("#sidebar");
menuButton.addEventListener("click", () => {
  const open = sidebar.classList.toggle("open");
  menuButton.setAttribute("aria-expanded", String(open));
});
document.querySelectorAll("[data-module]").forEach((button) => {
  button.addEventListener("click", () => showToast(`${button.dataset.module} will be added in a later module.`));
});

loadData();
