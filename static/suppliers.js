let suppliers = [];
let projects = [];
let toastTimer;

const supplierRows = document.querySelector("#supplier-rows");
const billRows = document.querySelector("#supplier-bill-rows");
const supplierModal = document.querySelector("#supplier-modal");
const supplierForm = document.querySelector("#supplier-form");
const billModal = document.querySelector("#supplier-bill-modal");
const billForm = document.querySelector("#supplier-bill-form");
const search = document.querySelector("#supplier-search");

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

function billBalance(bill) {
  return Math.max(0, Number(bill.amount || 0) - Number(bill.paid_amount || 0));
}

function renderSummary() {
  const bills = suppliers.flatMap((supplier) => supplier.bills || []);
  const today = localDateValue();
  document.querySelector("#supplier-count").textContent = suppliers.length;
  document.querySelector("#supplier-outstanding").textContent = formatCurrency(
    bills.reduce((sum, bill) => sum + billBalance(bill), 0)
  );
  document.querySelector("#supplier-overdue").textContent = bills.filter(
    (bill) => billBalance(bill) > 0 && bill.due_date < today
  ).length;
}

function renderSuppliers() {
  const query = search.value.trim().toLowerCase();
  const filtered = suppliers.filter((supplier) => [
    supplier.id, supplier.name, supplier.contact_number, supplier.email,
    supplier.gst_number, ...(supplier.materials_supplied || []),
  ].join(" ").toLowerCase().includes(query));
  supplierRows.innerHTML = filtered.length
    ? filtered.map((supplier) => {
      const bills = supplier.bills || [];
      const balance = bills.reduce((sum, bill) => sum + billBalance(bill), 0);
      return `<tr>
        <td><div class="project-cell"><span class="supplier-avatar" aria-hidden="true">▣</span><div><strong>${escapeHtml(supplier.name)}</strong><small>${escapeHtml(supplier.id)}${supplier.gst_number ? ` · GST ${escapeHtml(supplier.gst_number)}` : ""}</small></div></div></td>
        <td><div class="employee-contact"><strong>${escapeHtml(supplier.contact_number || "—")}</strong><small>${escapeHtml(supplier.email || "")}</small></div></td>
        <td class="supplier-materials">${escapeHtml((supplier.materials_supplied || []).join(", ") || "—")}</td>
        <td>${Number(supplier.payment_terms_days || 0)} days</td>
        <td>${bills.length}</td>
        <td><strong class="${balance > 0 ? "balance-due" : "balance-clear"}">${formatCurrency(balance)}</strong></td>
        <td><div class="row-actions"><button type="button" class="row-button payment" data-add-bill="${escapeHtml(supplier.id)}">Add bill</button><button type="button" class="row-button edit" data-edit="${escapeHtml(supplier.id)}">Edit</button><button type="button" class="row-button delete" data-delete="${escapeHtml(supplier.id)}">Delete</button></div></td>
      </tr>`;
    }).join("")
    : `<tr><td colspan="7" class="empty-state">${suppliers.length ? "No suppliers match this search." : "No suppliers yet. Add a supplier to start tracking purchases."}</td></tr>`;
}

function renderBills() {
  const bills = suppliers.flatMap((supplier) => (supplier.bills || []).map((bill) => ({ supplier, bill })))
    .sort((a, b) => b.bill.date.localeCompare(a.bill.date));
  const today = localDateValue();
  billRows.innerHTML = bills.length
    ? bills.map(({ supplier, bill }) => {
      const balance = billBalance(bill);
      const status = balance <= 0 ? "Paid" : bill.due_date < today ? "Overdue" : "Unpaid";
      const statusClass = status === "Paid" ? "green" : status === "Overdue" ? "orange" : "blue";
      const payAction = balance > 0
        ? `<a class="row-button payment" href="/payments?type=Supplier&supplier_id=${encodeURIComponent(supplier.id)}&bill_id=${encodeURIComponent(bill.id)}">Pay</a>`
        : "";
      return `<tr>
        <td><div class="expense-description"><strong>${escapeHtml(supplier.name)}</strong><small>${escapeHtml(bill.invoice_number || bill.id)} · ${escapeHtml(bill.description)}</small></div></td>
        <td>${escapeHtml(bill.project_name || "General / not assigned")}</td>
        <td>${formatDate(bill.date)}</td><td>${formatDate(bill.due_date)}</td>
        <td>${formatCurrency(bill.amount)}</td><td><strong class="${balance > 0 ? "balance-due" : "balance-clear"}">${formatCurrency(balance)}</strong></td>
        <td><span class="project-status ${statusClass}">${status}</span></td><td>${payAction}</td>
      </tr>`;
    }).join("")
    : '<tr><td colspan="8" class="empty-state">Supplier purchase bills will appear here when recorded.</td></tr>';
}

async function loadData() {
  try {
    const [supplierResponse, projectResponse] = await Promise.all([
      fetch("/api/suppliers"),
      fetch("/api/projects"),
    ]);
    if (!supplierResponse.ok || !projectResponse.ok) throw new Error("Could not load suppliers and projects");
    suppliers = await supplierResponse.json();
    projects = await projectResponse.json();
    document.querySelector("#bill-project").innerHTML = `<option value="">General / not assigned</option>${projects.map((project) =>
      `<option value="${escapeHtml(project.id)}">${escapeHtml(project.name)} · ${escapeHtml(project.id)}</option>`
    ).join("")}`;
    renderSummary();
    renderSuppliers();
    renderBills();
    return true;
  } catch (error) {
    supplierRows.innerHTML = '<tr><td colspan="7" class="empty-state">Could not load suppliers. Check the server and try again.</td></tr>';
    billRows.innerHTML = '<tr><td colspan="8" class="empty-state">Could not load supplier bills.</td></tr>';
    console.error(error);
    return false;
  }
}

function openSupplierModal(supplier = null) {
  supplierForm.reset();
  document.querySelector("#supplier-form-error").textContent = "";
  document.querySelector("#supplier-modal-title").textContent = supplier ? "Edit supplier" : "Add supplier";
  document.querySelector("#supplier-id").value = supplier?.id || "";
  document.querySelector("#supplier-name").value = supplier?.name || "";
  document.querySelector("#supplier-phone").value = supplier?.contact_number || "";
  document.querySelector("#supplier-email").value = supplier?.email || "";
  document.querySelector("#supplier-gst").value = supplier?.gst_number || "";
  document.querySelector("#supplier-terms").value = supplier?.payment_terms_days ?? 0;
  document.querySelector("#supplier-materials").value = (supplier?.materials_supplied || []).join("\n");
  document.querySelector("#supplier-address").value = supplier?.address || "";
  supplierModal.classList.add("open");
  supplierModal.setAttribute("aria-hidden", "false");
  setTimeout(() => document.querySelector("#supplier-name").focus(), 100);
}

function closeSupplierModal() {
  supplierModal.classList.remove("open");
  supplierModal.setAttribute("aria-hidden", "true");
}

function openBillModal(supplier) {
  billForm.reset();
  document.querySelector("#supplier-bill-error").textContent = "";
  document.querySelector("#bill-supplier-id").value = supplier.id;
  document.querySelector("#supplier-bill-title").textContent = `Add bill · ${supplier.name}`;
  document.querySelector("#bill-date").value = localDateValue();
  const due = new Date(`${localDateValue()}T00:00:00Z`);
  due.setUTCDate(due.getUTCDate() + Number(supplier.payment_terms_days || 0));
  document.querySelector("#bill-due-date").value = due.toISOString().slice(0, 10);
  billModal.classList.add("open");
  billModal.setAttribute("aria-hidden", "false");
  setTimeout(() => document.querySelector("#bill-description").focus(), 100);
}

function closeBillModal() {
  billModal.classList.remove("open");
  billModal.setAttribute("aria-hidden", "true");
}

document.querySelector("#add-supplier").addEventListener("click", () => openSupplierModal());
document.querySelector("#supplier-modal-close").addEventListener("click", closeSupplierModal);
document.querySelector("#supplier-cancel").addEventListener("click", closeSupplierModal);
supplierModal.addEventListener("click", (event) => { if (event.target === supplierModal) closeSupplierModal(); });
document.querySelector("#supplier-bill-close").addEventListener("click", closeBillModal);
document.querySelector("#supplier-bill-cancel").addEventListener("click", closeBillModal);
billModal.addEventListener("click", (event) => { if (event.target === billModal) closeBillModal(); });
document.addEventListener("keydown", (event) => {
  if (event.key === "Escape") {
    closeSupplierModal();
    closeBillModal();
  }
});

supplierForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const button = supplierForm.querySelector('button[type="submit"]');
  button.disabled = true;
  const id = document.querySelector("#supplier-id").value;
  const payload = {
    name: document.querySelector("#supplier-name").value.trim(),
    contact_number: document.querySelector("#supplier-phone").value.trim(),
    email: document.querySelector("#supplier-email").value.trim(),
    gst_number: document.querySelector("#supplier-gst").value.trim(),
    payment_terms_days: Number(document.querySelector("#supplier-terms").value),
    materials_supplied: document.querySelector("#supplier-materials").value.split("\n").map((item) => item.trim()).filter(Boolean),
    address: document.querySelector("#supplier-address").value.trim(),
  };
  try {
    const response = await fetch(id ? `/api/suppliers/${encodeURIComponent(id)}` : "/api/suppliers", {
      method: id ? "PUT" : "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const result = await response.json();
    if (!response.ok) throw new Error(result.error || "Could not save supplier");
    closeSupplierModal();
    showToast((await loadData()) ? (id ? "Supplier updated." : "Supplier added.") : "Supplier saved, but the list could not refresh.");
  } catch (error) {
    document.querySelector("#supplier-form-error").textContent = error.message;
  } finally {
    button.disabled = false;
  }
});

billForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const button = billForm.querySelector('button[type="submit"]');
  button.disabled = true;
  const supplierId = document.querySelector("#bill-supplier-id").value;
  const payload = {
    description: document.querySelector("#bill-description").value.trim(),
    invoice_number: document.querySelector("#bill-invoice-number").value.trim(),
    date: document.querySelector("#bill-date").value,
    due_date: document.querySelector("#bill-due-date").value,
    amount: Number(document.querySelector("#bill-amount").value),
    project_id: document.querySelector("#bill-project").value,
  };
  try {
    const response = await fetch(`/api/suppliers/${encodeURIComponent(supplierId)}/bills`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const result = await response.json();
    if (!response.ok) throw new Error(result.error || "Could not save supplier bill");
    closeBillModal();
    showToast((await loadData()) ? "Supplier bill recorded." : "Bill saved, but the list could not refresh.");
  } catch (error) {
    document.querySelector("#supplier-bill-error").textContent = error.message;
  } finally {
    button.disabled = false;
  }
});

supplierRows.addEventListener("click", async (event) => {
  const edit = event.target.closest("[data-edit]");
  const addBill = event.target.closest("[data-add-bill]");
  const remove = event.target.closest("[data-delete]");
  if (edit) {
    openSupplierModal(suppliers.find((supplier) => supplier.id === edit.dataset.edit));
    return;
  }
  if (addBill) {
    const supplier = suppliers.find((item) => item.id === addBill.dataset.addBill);
    if (supplier) openBillModal(supplier);
    return;
  }
  if (remove) {
    const supplier = suppliers.find((item) => item.id === remove.dataset.delete);
    if (!supplier || !confirm(`Delete supplier "${supplier.name}"?`)) return;
    try {
      const response = await fetch(`/api/suppliers/${encodeURIComponent(supplier.id)}`, { method: "DELETE" });
      const result = await response.json();
      if (!response.ok) throw new Error(result.error || "Could not delete supplier");
      showToast((await loadData()) ? "Supplier deleted." : "Supplier deleted, but the list could not refresh.");
    } catch (error) {
      showToast(error.message);
    }
  }
});

search.addEventListener("input", renderSuppliers);
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
