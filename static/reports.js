let toastTimer;

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

function formatDate(value) {
  if (!value) return "—";
  return new Intl.DateTimeFormat("en-IN", { day: "numeric", month: "short", year: "numeric" })
    .format(new Date(`${value}T00:00:00`));
}

function localMonthValue() {
  const now = new Date();
  now.setMinutes(now.getMinutes() - now.getTimezoneOffset());
  return now.toISOString().slice(0, 7);
}

function showToast(message) {
  const toast = document.querySelector("#toast");
  toast.textContent = message;
  toast.classList.add("visible");
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => toast.classList.remove("visible"), 2400);
}

function renderRows(selector, rows, emptyMessage, columns, renderRow) {
  document.querySelector(selector).innerHTML = rows.length
    ? rows.map(renderRow).join("")
    : `<tr><td colspan="${columns}" class="empty-state">${emptyMessage}</td></tr>`;
}

function renderReport(report) {
  const summary = report.summary;
  const outstanding = summary.invoice_outstanding + summary.supplier_outstanding + summary.payroll_outstanding;
  document.querySelector("#report-revenue").textContent = formatCurrency(summary.revenue);
  document.querySelector("#report-collected").textContent = formatCurrency(summary.collected);
  document.querySelector("#report-expenses").textContent = formatCurrency(summary.expenses);
  document.querySelector("#report-purchases").textContent = formatCurrency(summary.supplier_purchases);
  document.querySelector("#report-material-usage").textContent = formatCurrency(summary.material_usage);
  document.querySelector("#report-payroll").textContent = formatCurrency(summary.payroll_accrued);
  document.querySelector("#report-gst").textContent = formatCurrency(summary.gst_collected);
  document.querySelector("#report-outstanding").textContent = formatCurrency(outstanding);

  renderRows("#report-project-rows", report.project_profit_loss, "No project profit and loss data yet.", 7, (project) => `
    <tr><td><strong class="expense-project-name">${escapeHtml(project.project_name)}</strong><small class="expense-project-id">${escapeHtml(project.project_id)}</small></td>
      <td>${formatCurrency(project.revenue)}</td><td>${formatCurrency(project.expenses)}</td><td>${formatCurrency(project.supplier_purchases)}</td>
      <td>${formatCurrency(project.material_usage)}</td><td>${formatCurrency(project.payroll)}</td>
      <td><strong class="${project.profit >= 0 ? "balance-clear" : "balance-due"}">${formatCurrency(project.profit)}</strong></td></tr>
  `);
  renderRows("#report-expense-rows", report.expenses_by_category, "No expenses recorded this month.", 2, (item) => `
    <tr><td>${escapeHtml(item.category)}</td><td><strong>${formatCurrency(item.amount)}</strong></td></tr>
  `);
  renderRows("#report-material-rows", report.material_purchases, "No stock purchases recorded this month.", 2, (item) => `
    <tr><td>${escapeHtml(item.material)}</td><td><strong>${formatCurrency(item.amount)}</strong></td></tr>
  `);
  renderRows("#report-payroll-rows", report.payroll, "No attendance or salary records for this month.", 5, (employee) => `
    <tr><td><strong class="expense-project-name">${escapeHtml(employee.employee_name)}</strong><small class="expense-project-id">${escapeHtml(employee.role)}</small></td>
      <td>${employee.attendance_days}</td><td>${formatCurrency(employee.earned)}</td><td>${formatCurrency(employee.paid)}</td><td><strong class="${employee.balance > 0 ? "balance-due" : "balance-clear"}">${formatCurrency(employee.balance)}</strong></td></tr>
  `);
  renderRows("#report-payment-rows", report.payments, "No payments recorded this month.", 5, (payment) => `
    <tr><td>${formatDate(payment.date)}</td><td><span class="payment-direction ${payment.direction === "Incoming" ? "incoming" : "outgoing"}">${escapeHtml(payment.direction)}</span></td>
      <td>${escapeHtml(payment.party_name)}</td><td>${escapeHtml(payment.kind)}</td><td><strong>${formatCurrency(payment.amount)}</strong></td></tr>
  `);
}

async function loadReport() {
  const month = document.querySelector("#report-month").value || localMonthValue();
  try {
    const response = await fetch(`/api/reports?month=${encodeURIComponent(month)}`);
    const result = await response.json();
    if (!response.ok) throw new Error(result.error || "Could not load reports");
    renderReport(result);
  } catch (error) {
    document.querySelector("#report-project-rows").innerHTML = `<tr><td colspan="7" class="empty-state">${escapeHtml(error.message)}</td></tr>`;
    console.error(error);
    showToast(error.message);
  }
}

document.querySelector("#report-month").value = localMonthValue();
document.querySelector("#report-month").addEventListener("change", loadReport);
const menuButton = document.querySelector("#menu-button");
const sidebar = document.querySelector("#sidebar");
menuButton.addEventListener("click", () => {
  const open = sidebar.classList.toggle("open");
  menuButton.setAttribute("aria-expanded", String(open));
});
document.querySelectorAll("[data-module]").forEach((button) => {
  button.addEventListener("click", () => showToast(`${button.dataset.module} will be added in a later module.`));
});

loadReport();
