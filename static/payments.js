let payments = [];
let invoices = [];
let suppliers = [];
let employees = [];
let projects = [];
let toastTimer;

const rows = document.querySelector("#payment-rows");
const modal = document.querySelector("#payment-editor-modal");
const form = document.querySelector("#payment-editor-form");
const search = document.querySelector("#payment-search");
const directionFilter = document.querySelector("#payment-direction-filter");
const kindFilter = document.querySelector("#payment-kind-filter");

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

function payroll(employee, month) {
  const attendance = (employee.attendance || []).filter((entry) => entry.date.startsWith(month));
  const earned = attendance.reduce((sum, entry) =>
    sum + (entry.status === "Present" ? 1 : entry.status === "Half day" ? 0.5 : 0)
      * Number(entry.daily_wage ?? employee.daily_wage), 0);
  const paid = (employee.salary_payments || []).filter((payment) => payment.month === month)
    .reduce((sum, payment) => sum + Number(payment.amount || 0), 0);
  return Math.max(0, earned - paid);
}

function supplierBillBalance(bill) {
  return Math.max(0, Number(bill.amount || 0) - Number(bill.paid_amount || 0));
}

function renderSummary() {
  const incoming = payments.filter((payment) => payment.direction === "Incoming")
    .reduce((sum, payment) => sum + Number(payment.amount || 0), 0);
  const outgoing = payments.filter((payment) => payment.direction === "Outgoing")
    .reduce((sum, payment) => sum + Number(payment.amount || 0), 0);
  const invoiceDue = invoices.reduce((sum, invoice) => sum + Number(invoice.balance || 0), 0);
  const supplierDue = suppliers.reduce((sum, supplier) => sum + (supplier.bills || [])
    .reduce((billSum, bill) => billSum + supplierBillBalance(bill), 0), 0);
  document.querySelector("#payments-incoming").textContent = formatCurrency(incoming);
  document.querySelector("#payments-outgoing").textContent = formatCurrency(outgoing);
  document.querySelector("#payments-invoice-due").textContent = formatCurrency(invoiceDue);
  document.querySelector("#payments-supplier-due").textContent = formatCurrency(supplierDue);
}

function renderPayments() {
  const query = search.value.trim().toLowerCase();
  const direction = directionFilter.value;
  const kind = kindFilter.value;
  const filtered = payments.filter((payment) => {
    const matchesDirection = direction === "All" || payment.direction === direction;
    const matchesKind = kind === "All" || payment.kind === kind;
    const searchable = [
      payment.id, payment.party_name, payment.reference, payment.project_name,
      payment.kind, payment.category, payment.method, payment.direction,
    ].join(" ").toLowerCase();
    return matchesDirection && matchesKind && searchable.includes(query);
  });
  rows.innerHTML = filtered.length
    ? filtered.map((payment) => `<tr>
        <td>${formatDate(payment.date)}</td><td><span class="payment-direction ${payment.direction === "Incoming" ? "incoming" : "outgoing"}">${payment.direction}</span></td>
        <td>${escapeHtml(payment.kind)}${payment.category ? `<small class="payment-category">${escapeHtml(payment.category)}</small>` : ""}</td>
        <td><strong class="expense-project-name">${escapeHtml(payment.party_name)}</strong><small class="expense-project-id">${escapeHtml(payment.id)}</small></td>
        <td>${escapeHtml(payment.reference || "—")}</td><td>${escapeHtml(payment.project_name || "—")}</td><td>${escapeHtml(payment.method)}</td>
        <td><strong class="payment-amount ${payment.direction === "Incoming" ? "balance-clear" : "balance-due"}">${payment.direction === "Incoming" ? "+" : "−"} ${formatCurrency(payment.amount)}</strong></td>
      </tr>`).join("")
    : `<tr><td colspan="8" class="empty-state">${payments.length ? "No payments match these filters." : "No payments recorded yet. Start by collecting an invoice or paying a supplier."}</td></tr>`;
}

async function loadData() {
  try {
    const [paymentResponse, invoiceResponse, supplierResponse, employeeResponse, projectResponse] = await Promise.all([
      fetch("/api/payments"),
      fetch("/api/invoices"),
      fetch("/api/suppliers"),
      fetch("/api/employees"),
      fetch("/api/projects"),
    ]);
    if ([paymentResponse, invoiceResponse, supplierResponse, employeeResponse, projectResponse].some((response) => !response.ok)) {
      throw new Error("Could not load payment records");
    }
    [payments, invoices, suppliers, employees, projects] = await Promise.all([
      paymentResponse.json(), invoiceResponse.json(), supplierResponse.json(), employeeResponse.json(), projectResponse.json(),
    ]);
    renderSummary();
    renderPayments();
    renderPaymentOptions();
    return true;
  } catch (error) {
    rows.innerHTML = '<tr><td colspan="8" class="empty-state">Could not load payment records. Check the server and try again.</td></tr>';
    console.error(error);
    return false;
  }
}

function renderPaymentOptions() {
  const invoiceOptions = invoices.filter((invoice) => Number(invoice.balance) > 0).map((invoice) =>
    `<option value="${escapeHtml(invoice.id)}">${escapeHtml(invoice.id)} · ${escapeHtml(invoice.project_name)} · ${formatCurrency(invoice.balance)} due</option>`
  ).join("");
  document.querySelector("#payment-invoice").innerHTML = invoiceOptions || '<option value="">No unpaid invoices</option>';

  const billOptions = suppliers.flatMap((supplier) => (supplier.bills || [])
    .filter((bill) => supplierBillBalance(bill) > 0)
    .map((bill) => `<option value="${escapeHtml(supplier.id)}|${escapeHtml(bill.id)}">${escapeHtml(supplier.name)} · ${escapeHtml(bill.invoice_number || bill.id)} · ${formatCurrency(supplierBillBalance(bill))} due</option>`))
    .join("");
  document.querySelector("#payment-bill").innerHTML = billOptions || '<option value="">No unpaid supplier bills</option>';

  const month = document.querySelector("#payment-payroll-month").value || localDateValue().slice(0, 7);
  const employeeOptions = employees.map((employee) => {
    const due = payroll(employee, month);
    return due > 0
      ? `<option value="${escapeHtml(employee.id)}|${escapeHtml(month)}">${escapeHtml(employee.name)} · ${escapeHtml(month)} · ${formatCurrency(due)} due</option>`
      : "";
  }).join("");
  document.querySelector("#payment-employee").innerHTML = employeeOptions || '<option value="">No earned salary due this month</option>';
  document.querySelector("#payment-project").innerHTML = `<option value="">General / not assigned</option>${projects.map((project) =>
    `<option value="${escapeHtml(project.id)}">${escapeHtml(project.name)} · ${escapeHtml(project.id)}</option>`
  ).join("")}`;
}

function showField(id, visible) {
  document.querySelector(id).hidden = !visible;
}

function selectedBalance(kind) {
  if (kind === "Invoice") {
    const invoice = invoices.find((item) => item.id === document.querySelector("#payment-invoice").value);
    return invoice ? Number(invoice.balance) : 0;
  }
  if (kind === "Supplier") {
    const [supplierId, billId] = document.querySelector("#payment-bill").value.split("|");
    const supplier = suppliers.find((item) => item.id === supplierId);
    const bill = supplier?.bills.find((item) => item.id === billId);
    return bill ? supplierBillBalance(bill) : 0;
  }
  if (kind === "Salary") {
    const [employeeId, month] = document.querySelector("#payment-employee").value.split("|");
    const employee = employees.find((item) => item.id === employeeId);
    return employee ? payroll(employee, month) : 0;
  }
  return 0;
}

function updatePaymentFields(resetAmount = false) {
  const kind = document.querySelector("#payment-kind").value;
  showField("#payment-invoice-field", kind === "Invoice");
  showField("#payment-supplier-field", kind === "Supplier");
  showField("#payment-payroll-month-field", kind === "Salary");
  showField("#payment-employee-field", kind === "Salary");
  showField("#payment-other-direction-field", kind === "Other");
  showField("#payment-other-party-field", kind === "Other");
  showField("#payment-other-category-field", kind === "Other");
  showField("#payment-project-field", kind === "Other");
  showField("#payment-reference-field", kind === "Other");
  showField("#payment-notes-field", kind === "Other");
  const balance = selectedBalance(kind);
  const amount = document.querySelector("#payment-amount");
  amount.max = balance > 0 ? balance.toFixed(2) : "";
  if (resetAmount) amount.value = balance > 0 ? balance.toFixed(2) : "";
  document.querySelector("#payment-balance-hint").textContent = balance > 0
    ? `Remaining balance: ${formatCurrency(balance)}`
    : (kind === "Other" ? "This transaction is not matched to an invoice, supplier bill, or payroll balance." : "No balance is currently available for this payment type.");
}

function openModal() {
  form.reset();
  document.querySelector("#payment-editor-error").textContent = "";
  document.querySelector("#payment-date").value = localDateValue();
  document.querySelector("#payment-payroll-month").value = localDateValue().slice(0, 7);
  renderPaymentOptions();
  const params = new URLSearchParams(location.search);
  const requestedKind = params.get("type");
  const kind = requestedKind === "Salary" || requestedKind === "Supplier" || requestedKind === "Other"
    ? requestedKind
    : "Invoice";
  document.querySelector("#payment-kind").value = kind;
  if (kind === "Supplier" && params.get("supplier_id") && params.get("bill_id")) {
    document.querySelector("#payment-bill").value = `${params.get("supplier_id")}|${params.get("bill_id")}`;
  }
  if (kind === "Salary") {
    const month = params.get("month") || localDateValue().slice(0, 7);
    document.querySelector("#payment-payroll-month").value = month;
    renderPaymentOptions();
    document.querySelector("#payment-employee").value = `${params.get("employee_id") || ""}|${month}`;
  }
  if (kind === "Invoice" && params.get("invoice_id")) {
    document.querySelector("#payment-invoice").value = params.get("invoice_id");
  }
  updatePaymentFields(true);
  modal.classList.add("open");
  modal.setAttribute("aria-hidden", "false");
}

function closeModal() {
  modal.classList.remove("open");
  modal.setAttribute("aria-hidden", "true");
}

document.querySelector("#add-payment").addEventListener("click", openModal);
document.querySelector("#payment-editor-close").addEventListener("click", closeModal);
document.querySelector("#payment-editor-cancel").addEventListener("click", closeModal);
modal.addEventListener("click", (event) => { if (event.target === modal) closeModal(); });
document.addEventListener("keydown", (event) => { if (event.key === "Escape") closeModal(); });
document.querySelector("#payment-kind").addEventListener("change", () => updatePaymentFields(true));
document.querySelector("#payment-invoice").addEventListener("change", () => updatePaymentFields(true));
document.querySelector("#payment-bill").addEventListener("change", () => updatePaymentFields(true));
document.querySelector("#payment-employee").addEventListener("change", () => updatePaymentFields(true));
document.querySelector("#payment-payroll-month").addEventListener("change", () => {
  renderPaymentOptions();
  updatePaymentFields(true);
});

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const button = form.querySelector('button[type="submit"]');
  button.disabled = true;
  const kind = document.querySelector("#payment-kind").value;
  const base = {
    kind,
    amount: Number(document.querySelector("#payment-amount").value),
    method: document.querySelector("#payment-method").value,
    date: document.querySelector("#payment-date").value,
  };
  let payload = base;
  if (kind === "Invoice") {
    payload = { ...base, invoice_id: document.querySelector("#payment-invoice").value };
  } else if (kind === "Supplier") {
    const [supplier_id, bill_id] = document.querySelector("#payment-bill").value.split("|");
    payload = { ...base, supplier_id, bill_id };
  } else if (kind === "Salary") {
    const [employee_id, month] = document.querySelector("#payment-employee").value.split("|");
    payload = { ...base, employee_id, month: document.querySelector("#payment-payroll-month").value || month };
  } else {
    payload = {
      ...base,
      direction: document.querySelector("#payment-other-direction").value,
      party_name: document.querySelector("#payment-party").value.trim(),
      category: document.querySelector("#payment-category").value.trim(),
      project_id: document.querySelector("#payment-project").value,
      reference: document.querySelector("#payment-reference").value.trim(),
      notes: document.querySelector("#payment-notes").value.trim(),
    };
  }
  try {
    const response = await fetch("/api/payments", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const result = await response.json();
    if (!response.ok) throw new Error(result.error || "Could not record payment");
    closeModal();
    showToast((await loadData()) ? "Payment recorded." : "Payment saved, but the list could not refresh.");
  } catch (error) {
    document.querySelector("#payment-editor-error").textContent = error.message;
  } finally {
    button.disabled = false;
  }
});

search.addEventListener("input", renderPayments);
directionFilter.addEventListener("change", renderPayments);
kindFilter.addEventListener("change", renderPayments);
const menuButton = document.querySelector("#menu-button");
const sidebar = document.querySelector("#sidebar");
menuButton.addEventListener("click", () => {
  const open = sidebar.classList.toggle("open");
  menuButton.setAttribute("aria-expanded", String(open));
});
document.querySelectorAll("[data-module]").forEach((button) => {
  button.addEventListener("click", () => showToast(`${button.dataset.module} will be added in a later module.`));
});

loadData().then(() => {
  const params = new URLSearchParams(location.search);
  if (params.get("type") || params.get("bill_id") || params.get("employee_id")) openModal();
});
