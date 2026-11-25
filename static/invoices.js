(function () {
let invoices = [];
let toastTimer;

const rows = document.querySelector("#invoice-rows");
const paymentModal = document.querySelector("#payment-modal");
const paymentForm = document.querySelector("#payment-form");
const printModal = document.querySelector("#invoice-print-modal");
const search = document.querySelector("#invoice-search");
const statusFilter = document.querySelector("#invoice-status-filter");

function escapeHtml(value) {
  const span = document.createElement("span");
  span.textContent = value ?? "";
  return span.innerHTML.replace(/"/g, "&quot;").replace(/'/g, "&#39;");
}

function showToast(message) {
  const toast = document.querySelector("#toast");
  toast.textContent = message;
  toast.classList.add("visible");
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => toast.classList.remove("visible"), 2400);
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

function localDateValue() {
  const now = new Date();
  now.setMinutes(now.getMinutes() - now.getTimezoneOffset());
  return now.toISOString().slice(0, 10);
}

function isOverdue(invoice) {
  return Number(invoice.balance) > 0 && invoice.due_date < localDateValue();
}

function displayStatus(invoice) {
  return isOverdue(invoice) ? "Overdue" : invoice.status;
}

function updateSummary() {
  document.querySelector("#invoice-total-value").textContent = formatCurrency(
    invoices.reduce((sum, invoice) => sum + Number(invoice.total || 0), 0)
  );
  document.querySelector("#invoice-paid-value").textContent = formatCurrency(
    invoices.reduce((sum, invoice) => sum + Number(invoice.paid_amount || 0), 0)
  );
  document.querySelector("#invoice-balance-value").textContent = formatCurrency(
    invoices.reduce((sum, invoice) => sum + Number(invoice.balance || 0), 0)
  );
  document.querySelector("#invoice-overdue-value").textContent = invoices.filter(isOverdue).length;
  document.querySelector("#invoice-count").textContent = `${invoices.length} invoice${invoices.length === 1 ? "" : "s"}`;
}

function renderInvoices() {
  const query = search.value.trim().toLowerCase();
  const selectedStatus = statusFilter.value;
  const filtered = invoices.filter((invoice) => {
    const status = displayStatus(invoice);
    const matchesStatus = selectedStatus === "All" || status === selectedStatus;
    const searchable = [invoice.id, invoice.project_name, invoice.project_id, invoice.estimate_id].join(" ").toLowerCase();
    return matchesStatus && searchable.includes(query);
  });

  if (!filtered.length) {
    const message = invoices.length
      ? "No invoices match this view."
      : 'No invoices yet. Accept an estimate in the Estimates tab, then convert it to an invoice.';
    rows.innerHTML = `<tr><td colspan="9" class="empty-state">${message}</td></tr>`;
    return;
  }

  rows.innerHTML = filtered.map((invoice) => {
    const status = displayStatus(invoice);
    const statusClass = status === "Paid" ? "green" : status === "Partially paid" ? "blue" : status === "Overdue" ? "orange" : "neutral";
    const paymentAction = Number(invoice.balance) > 0
      ? `<button type="button" class="row-button payment" data-payment="${escapeHtml(invoice.id)}">Record payment</button>`
      : "";
    return `<tr>
      <td><div class="project-cell"><span class="invoice-avatar" aria-hidden="true">₹</span><div><strong>${escapeHtml(invoice.id)}</strong><small>From ${escapeHtml(invoice.estimate_id)}</small></div></div></td>
      <td><strong class="estimate-project-name">${escapeHtml(invoice.project_name)}</strong><small class="estimate-project-id">${escapeHtml(invoice.project_id)}</small></td>
      <td>${formatDate(invoice.issue_date)}</td>
      <td>${formatDate(invoice.due_date)}</td>
      <td><strong class="estimate-amount">${formatCurrency(invoice.total)}</strong></td>
      <td>${formatCurrency(invoice.paid_amount)}</td>
      <td><strong class="${Number(invoice.balance) > 0 ? "balance-due" : "balance-clear"}">${formatCurrency(invoice.balance)}</strong></td>
      <td><span class="project-status ${statusClass}">${escapeHtml(status)}</span></td>
      <td><div class="row-actions">${paymentAction}<button type="button" class="row-button print" data-print="${escapeHtml(invoice.id)}">Print</button></div></td>
    </tr>`;
  }).join("");
}

async function loadInvoices() {
  try {
    const response = await fetch("/api/invoices");
    if (!response.ok) throw new Error("Could not load invoices");
    invoices = await response.json();
    updateSummary();
    renderInvoices();
    return true;
  } catch (error) {
    rows.innerHTML = '<tr><td colspan="9" class="empty-state">Could not load invoices. Check the server and try again.</td></tr>';
    console.error(error);
    return false;
  }
}
window.addEventListener("billing:invoices-updated", loadInvoices);

function openPaymentModal(invoice) {
  paymentForm.reset();
  document.querySelector("#payment-form-error").textContent = "";
  document.querySelector("#payment-invoice-id").value = invoice.id;
  document.querySelector("#payment-invoice-project").textContent = `${invoice.id} · ${invoice.project_name}`;
  document.querySelector("#payment-invoice-balance").textContent = formatCurrency(invoice.balance);
  const amount = document.querySelector("#payment-amount");
  amount.value = Number(invoice.balance).toFixed(2);
  amount.max = Number(invoice.balance).toFixed(2);
  document.querySelector("#payment-date").value = localDateValue();
  paymentModal.classList.add("open");
  paymentModal.setAttribute("aria-hidden", "false");
  setTimeout(() => amount.focus(), 100);
}

function closePaymentModal() {
  paymentModal.classList.remove("open");
  paymentModal.setAttribute("aria-hidden", "true");
}

function openPrintPreview(invoice) {
  const itemRows = invoice.items.map((item) => `<tr>
    <td>${escapeHtml(item.description)}<small>${escapeHtml(item.category)}</small></td>
    <td>${escapeHtml(item.quantity)} ${escapeHtml(item.unit)}</td>
    <td>${formatCurrency(item.unit_price)}</td>
    <td>${formatCurrency(item.amount)}</td>
  </tr>`).join("");
  const paymentRows = (invoice.payments || []).map((payment) => `<tr>
    <td>${formatDate(payment.date)}</td><td>${escapeHtml(payment.method)}</td><td>${formatCurrency(payment.amount)}</td>
  </tr>`).join("");
  const paymentHistory = paymentRows
    ? `<section class="print-payment-history"><strong>Payment history</strong><table class="print-items"><thead><tr><th>Date</th><th>Method</th><th>Amount</th></tr></thead><tbody>${paymentRows}</tbody></table></section>`
    : "";
  document.querySelector("#invoice-print-content").innerHTML = `
    <header class="print-brand"><div class="print-company"><span class="print-brand-mark" aria-hidden="true"><svg viewBox="0 0 32 32"><path d="M5 26V13l11-8 11 8v13h-7v-8h-8v8H5Z"/></svg></span><div><strong>SUPER CONSTRUCTION</strong><span>Construction Management &amp; Billing</span></div></div><div class="print-document-title"><span>TAX INVOICE</span><strong>${escapeHtml(invoice.id)}</strong></div></header>
    <div class="print-estimate-meta"><div><span>Project</span><strong>${escapeHtml(invoice.project_name)}</strong><small>${escapeHtml(invoice.project_id)}</small></div><div><span>Issue date</span><strong>${formatDate(invoice.issue_date)}</strong></div><div><span>Due date</span><strong>${formatDate(invoice.due_date)}</strong></div></div>
    <table class="print-items"><thead><tr><th>Description</th><th>Quantity</th><th>Rate</th><th>Amount</th></tr></thead><tbody>${itemRows}</tbody></table>
    <div class="print-summary"><div><span>Subtotal</span><strong>${formatCurrency(invoice.subtotal)}</strong></div><div><span>Discount (${escapeHtml(invoice.discount_percent)}%)</span><strong>− ${formatCurrency(invoice.discount_amount)}</strong></div><div><span>GST (${escapeHtml(invoice.gst_percent)}%)</span><strong>${formatCurrency(invoice.gst_amount)}</strong></div><div><span>Invoice total</span><strong>${formatCurrency(invoice.total)}</strong></div><div><span>Paid</span><strong>${formatCurrency(invoice.paid_amount)}</strong></div><div class="print-grand-total"><span>Balance due</span><strong>${formatCurrency(invoice.balance)}</strong></div></div>
    ${paymentHistory}
    ${invoice.notes ? `<section class="print-notes"><strong>Notes</strong><p>${escapeHtml(invoice.notes)}</p></section>` : ""}
    <footer class="print-footer">Thank you for your business.</footer>`;
  printModal.classList.add("open");
  printModal.setAttribute("aria-hidden", "false");
}

function closePrintPreview() {
  printModal.classList.remove("open");
  printModal.setAttribute("aria-hidden", "true");
}

document.querySelector("#payment-modal-close").addEventListener("click", closePaymentModal);
document.querySelector("#payment-cancel").addEventListener("click", closePaymentModal);
paymentModal.addEventListener("click", (event) => { if (event.target === paymentModal) closePaymentModal(); });
document.querySelector("#invoice-print-close").addEventListener("click", closePrintPreview);
document.querySelector("#invoice-print-button").addEventListener("click", () => window.print());
printModal.addEventListener("click", (event) => { if (event.target === printModal) closePrintPreview(); });
document.addEventListener("keydown", (event) => {
  if (event.key === "Escape") {
    closePaymentModal();
    closePrintPreview();
  }
});

paymentForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const saveButton = paymentForm.querySelector('button[type="submit"]');
  saveButton.disabled = true;
  const invoiceId = document.querySelector("#payment-invoice-id").value;
  const payment = {
    amount: Number(document.querySelector("#payment-amount").value),
    method: document.querySelector("#payment-method").value,
    date: document.querySelector("#payment-date").value,
  };
  try {
    const response = await fetch(`/api/invoices/${encodeURIComponent(invoiceId)}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ payment }),
    });
    const result = await response.json();
    if (!response.ok) throw new Error(result.error || "Could not record payment");
    closePaymentModal();
    await loadInvoices();
    showToast(`Payment recorded. Remaining balance: ${formatCurrency(result.balance)}.`);
  } catch (error) {
    document.querySelector("#payment-form-error").textContent = error.message;
  } finally {
    saveButton.disabled = false;
  }
});

rows.addEventListener("click", (event) => {
  const paymentButton = event.target.closest("[data-payment]");
  const printButton = event.target.closest("[data-print]");
  if (paymentButton) {
    const invoice = invoices.find((item) => item.id === paymentButton.dataset.payment);
    if (invoice) openPaymentModal(invoice);
  } else if (printButton) {
    const invoice = invoices.find((item) => item.id === printButton.dataset.print);
    if (invoice) openPrintPreview(invoice);
  }
});

search.addEventListener("input", renderInvoices);
statusFilter.addEventListener("change", renderInvoices);

if (!document.querySelector("#estimate-rows")) {
  const menuButton = document.querySelector("#menu-button");
  const sidebar = document.querySelector("#sidebar");
  menuButton.addEventListener("click", () => {
    const open = sidebar.classList.toggle("open");
    menuButton.setAttribute("aria-expanded", String(open));
  });

  document.querySelectorAll("[data-module]").forEach((button) => {
    button.addEventListener("click", () => showToast(`${button.dataset.module} will be added in a later module.`));
  });
}

loadInvoices();
})();
