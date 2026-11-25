let estimates = [];
let projects = [];
let toastTimer;

const rows = document.querySelector("#estimate-rows");
const modal = document.querySelector("#estimate-modal");
const form = document.querySelector("#estimate-form");
const itemRows = document.querySelector("#estimate-item-rows");
const printModal = document.querySelector("#estimate-print-modal");
const search = document.querySelector("#estimate-search");
const statusFilter = document.querySelector("#estimate-status-filter");

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

function updateSummary() {
  document.querySelector("#total-estimates").textContent = estimates.length;
  document.querySelector("#draft-estimates").textContent = estimates.filter((estimate) => estimate.status === "Draft").length;
  document.querySelector("#sent-estimates").textContent = estimates.filter((estimate) => estimate.status === "Sent").length;
  document.querySelector("#accepted-estimates").textContent = estimates.filter((estimate) => estimate.status === "Accepted").length;
}

function renderProjects(selectedId = "") {
  const choices = projects.map((project) =>
    `<option value="${escapeHtml(project.id)}" ${project.id === selectedId ? "selected" : ""}>${escapeHtml(project.name)} · ${escapeHtml(project.id)}</option>`
  ).join("");
  document.querySelector("#estimate-project").innerHTML = `<option value="">Select a project</option>${choices}`;
}

function renderEstimates() {
  const query = search.value.trim().toLowerCase();
  const selectedStatus = statusFilter.value;
  const filtered = estimates.filter((estimate) => {
    const matchesStatus = selectedStatus === "All" || estimate.status === selectedStatus;
    return matchesStatus && [estimate.id, estimate.project_name, estimate.project_id].join(" ").toLowerCase().includes(query);
  });

  if (!filtered.length) {
    rows.innerHTML = '<tr><td colspan="7" class="empty-state">No estimates match this view.</td></tr>';
    return;
  }

  rows.innerHTML = filtered.map((estimate) => {
    const statusClass = estimate.status === "Accepted" ? "green" : estimate.status === "Sent" ? "blue" : estimate.status === "Rejected" ? "orange" : "neutral";
    const invoiceAction = estimate.status === "Accepted"
      ? estimate.converted_invoice_id
        ? `<span class="converted-invoice">${escapeHtml(estimate.converted_invoice_id)}</span>`
        : `<button type="button" class="row-button convert" data-convert="${escapeHtml(estimate.id)}">Invoice</button>`
      : "";
    const editAction = estimate.converted_invoice_id ? "" : `<button type="button" class="row-button edit" data-edit="${escapeHtml(estimate.id)}">Edit</button>`;
    const deleteAction = estimate.converted_invoice_id ? "" : `<button type="button" class="row-button delete" data-delete="${escapeHtml(estimate.id)}">Delete</button>`;
    return `<tr>
      <td><div class="project-cell"><span class="estimate-avatar" aria-hidden="true">▤</span><div><strong>${escapeHtml(estimate.id)}</strong><small>${estimate.items.length} line item${estimate.items.length === 1 ? "" : "s"}</small></div></div></td>
      <td><strong class="estimate-project-name">${escapeHtml(estimate.project_name)}</strong><small class="estimate-project-id">${escapeHtml(estimate.project_id)}</small></td>
      <td>${formatDate(estimate.valid_until)}</td>
      <td>${estimate.items.length}</td>
      <td><strong class="estimate-amount">${formatCurrency(estimate.total)}</strong></td>
      <td><span class="project-status ${statusClass}">${escapeHtml(estimate.status)}</span></td>
      <td><div class="row-actions">${invoiceAction}<button type="button" class="row-button print" data-print="${escapeHtml(estimate.id)}">Print</button>${editAction}${deleteAction}</div></td>
    </tr>`;
  }).join("");
}

async function loadData() {
  try {
    const [estimatesResponse, projectsResponse] = await Promise.all([
      fetch("/api/estimates"),
      fetch("/api/projects"),
    ]);
    if (!estimatesResponse.ok || !projectsResponse.ok) throw new Error("Could not load estimates and projects");
    estimates = await estimatesResponse.json();
    projects = await projectsResponse.json();
    renderProjects();
    updateSummary();
    renderEstimates();
    document.querySelector("#add-estimate").disabled = projects.length === 0;
  } catch (error) {
    rows.innerHTML = '<tr><td colspan="7" class="empty-state">Could not load estimates. Check the server and try again.</td></tr>';
    console.error(error);
  }
}

function createItemRow(item = {}) {
  const row = document.createElement("tr");
  row.className = "estimate-item-row";
  row.innerHTML = `<td><input class="item-description" aria-label="Item description" required maxlength="160" placeholder="e.g. Cement, M25 concrete" value="${escapeHtml(item.description || "")}"></td>
    <td><select class="item-category" aria-label="Item category"><option ${item.category === "Material" || !item.category ? "selected" : ""}>Material</option><option ${item.category === "Labour" ? "selected" : ""}>Labour</option><option ${item.category === "Equipment" ? "selected" : ""}>Equipment</option><option ${item.category === "Transport" ? "selected" : ""}>Transport</option><option ${item.category === "Other" ? "selected" : ""}>Other</option></select></td>
    <td><input class="item-quantity" aria-label="Quantity" type="number" min="0.01" step="any" value="${escapeHtml(item.quantity ?? 1)}" required></td>
    <td><input class="item-unit" aria-label="Unit" maxlength="20" value="${escapeHtml(item.unit || "unit")}"></td>
    <td><input class="item-rate" aria-label="Rate" type="number" min="0" step="0.01" value="${escapeHtml(item.unit_price ?? 0)}" required></td>
    <td class="item-amount">${formatCurrency(Number(item.quantity || 1) * Number(item.unit_price || 0))}</td>
    <td><button class="remove-estimate-item" type="button" aria-label="Remove item">×</button></td>`;
  return row;
}

function calculateTotals() {
  let subtotal = 0;
  itemRows.querySelectorAll(".estimate-item-row").forEach((row) => {
    const quantity = Number(row.querySelector(".item-quantity").value) || 0;
    const rate = Number(row.querySelector(".item-rate").value) || 0;
    const amount = quantity * rate;
    row.querySelector(".item-amount").textContent = formatCurrency(amount);
    subtotal += amount;
  });
  const discountPercent = Math.min(100, Math.max(0, Number(document.querySelector("#estimate-discount").value) || 0));
  const gstPercent = Math.min(100, Math.max(0, Number(document.querySelector("#estimate-gst").value) || 0));
  const discount = subtotal * discountPercent / 100;
  const gst = (subtotal - discount) * gstPercent / 100;
  document.querySelector("#estimate-subtotal").textContent = formatCurrency(subtotal);
  document.querySelector("#estimate-discount-amount").textContent = `− ${formatCurrency(discount)}`;
  document.querySelector("#estimate-gst-amount").textContent = formatCurrency(gst);
  document.querySelector("#estimate-total").textContent = formatCurrency(subtotal - discount + gst);
}

function openModal(estimate = null) {
  form.reset();
  document.querySelector("#estimate-form-error").textContent = "";
  document.querySelector("#estimate-modal-title").textContent = estimate ? "Edit estimate" : "New estimate";
  document.querySelector("#estimate-id").value = estimate?.id || "";
  renderProjects(estimate?.project_id || "");
  const validUntil = document.querySelector("#estimate-valid-until");
  if (estimate) {
    validUntil.value = estimate.valid_until;
    document.querySelector("#estimate-status").value = estimate.status;
    document.querySelector("#estimate-notes").value = estimate.notes || "";
    document.querySelector("#estimate-discount").value = estimate.discount_percent;
    document.querySelector("#estimate-gst").value = estimate.gst_percent;
    itemRows.replaceChildren(...estimate.items.map(createItemRow));
  } else {
    const defaultDate = new Date();
    defaultDate.setDate(defaultDate.getDate() + 30);
    validUntil.value = defaultDate.toISOString().slice(0, 10);
    document.querySelector("#estimate-status").value = "Draft";
    document.querySelector("#estimate-notes").value = "";
    document.querySelector("#estimate-discount").value = 0;
    document.querySelector("#estimate-gst").value = 18;
    itemRows.replaceChildren(createItemRow());
  }
  calculateTotals();
  modal.classList.add("open");
  modal.setAttribute("aria-hidden", "false");
  setTimeout(() => document.querySelector("#estimate-project").focus(), 100);
}

function closeModal() {
  modal.classList.remove("open");
  modal.setAttribute("aria-hidden", "true");
}

function openPrintPreview(estimate) {
  const project = projects.find((item) => item.id === estimate.project_id);
  const itemRowsHtml = estimate.items.map((item) => `<tr>
    <td>${escapeHtml(item.description)}<small>${escapeHtml(item.category)}</small></td>
    <td>${escapeHtml(item.quantity)} ${escapeHtml(item.unit)}</td>
    <td>${formatCurrency(item.unit_price)}</td>
    <td>${formatCurrency(item.amount)}</td>
  </tr>`).join("");
  document.querySelector("#estimate-print-content").innerHTML = `
    <header class="print-brand"><div class="print-company"><span class="print-brand-mark" aria-hidden="true"><svg viewBox="0 0 32 32"><path d="M5 26V13l11-8 11 8v13h-7v-8h-8v8H5Z"/></svg></span><div><strong>SUPER CONSTRUCTION</strong><span>Construction Management &amp; Billing</span></div></div><div class="print-document-title"><span>ESTIMATE / QUOTATION</span><strong>${escapeHtml(estimate.id)}</strong></div></header>
    <div class="print-estimate-meta"><div><span>Project</span><strong>${escapeHtml(project?.name || estimate.project_name)}</strong><small>${escapeHtml(project?.location || "")}</small></div><div><span>Estimate date</span><strong>${formatDate(estimate.created_at?.slice(0, 10) || new Date().toISOString().slice(0, 10))}</strong></div><div><span>Valid until</span><strong>${formatDate(estimate.valid_until)}</strong></div></div>
    <table class="print-items"><thead><tr><th>Description</th><th>Quantity</th><th>Rate</th><th>Amount</th></tr></thead><tbody>${itemRowsHtml}</tbody></table>
    <div class="print-summary"><div><span>Subtotal</span><strong>${formatCurrency(estimate.subtotal)}</strong></div><div><span>Discount (${escapeHtml(estimate.discount_percent)}%)</span><strong>− ${formatCurrency(estimate.discount_amount)}</strong></div><div><span>GST (${escapeHtml(estimate.gst_percent)}%)</span><strong>${formatCurrency(estimate.gst_amount)}</strong></div><div class="print-grand-total"><span>Estimated total</span><strong>${formatCurrency(estimate.total)}</strong></div></div>
    ${estimate.notes ? `<section class="print-notes"><strong>Notes</strong><p>${escapeHtml(estimate.notes)}</p></section>` : ""}
    <footer class="print-footer">This estimate is valid until ${formatDate(estimate.valid_until)}. Thank you for considering Super Construction.</footer>`;
  printModal.classList.add("open");
  printModal.setAttribute("aria-hidden", "false");
}

function closePrintPreview() {
  printModal.classList.remove("open");
  printModal.setAttribute("aria-hidden", "true");
}

document.querySelector("#add-estimate").addEventListener("click", () => {
  if (!projects.length) {
    showToast("Create a project before adding an estimate.");
    return;
  }
  openModal();
});
document.querySelector("#estimate-modal-close").addEventListener("click", closeModal);
document.querySelector("#estimate-cancel").addEventListener("click", closeModal);
modal.addEventListener("click", (event) => { if (event.target === modal) closeModal(); });
document.querySelector("#estimate-print-close").addEventListener("click", closePrintPreview);
printModal.addEventListener("click", (event) => { if (event.target === printModal) closePrintPreview(); });
document.querySelector("#estimate-print-button").addEventListener("click", () => window.print());
document.addEventListener("keydown", (event) => {
  if (event.key === "Escape") {
    closeModal();
    closePrintPreview();
  }
});

document.querySelector("#add-estimate-item").addEventListener("click", () => {
  if (itemRows.children.length >= 100) {
    showToast("An estimate can have up to 100 items.");
    return;
  }
  const row = createItemRow();
  itemRows.append(row);
  row.querySelector(".item-description").focus();
});
itemRows.addEventListener("input", calculateTotals);
itemRows.addEventListener("change", calculateTotals);
itemRows.addEventListener("click", (event) => {
  const removeButton = event.target.closest(".remove-estimate-item");
  if (!removeButton) return;
  if (itemRows.children.length === 1) {
    showToast("An estimate must include at least one item.");
    return;
  }
  removeButton.closest("tr").remove();
  calculateTotals();
});
document.querySelector("#estimate-discount").addEventListener("input", calculateTotals);
document.querySelector("#estimate-gst").addEventListener("input", calculateTotals);
document.querySelector("#calculate-estimate").addEventListener("click", () => {
  calculateTotals();
  showToast("Estimate total calculated.");
});

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const saveButton = form.querySelector('button[type="submit"]');
  saveButton.disabled = true;
  const id = document.querySelector("#estimate-id").value;
  const payload = {
    project_id: document.querySelector("#estimate-project").value,
    valid_until: document.querySelector("#estimate-valid-until").value,
    status: document.querySelector("#estimate-status").value,
    discount_percent: Number(document.querySelector("#estimate-discount").value),
    gst_percent: Number(document.querySelector("#estimate-gst").value),
    notes: document.querySelector("#estimate-notes").value.trim(),
    items: [...itemRows.querySelectorAll(".estimate-item-row")].map((row) => ({
      description: row.querySelector(".item-description").value.trim(),
      category: row.querySelector(".item-category").value,
      quantity: Number(row.querySelector(".item-quantity").value),
      unit: row.querySelector(".item-unit").value.trim() || "unit",
      unit_price: Number(row.querySelector(".item-rate").value),
    })),
  };
  try {
    const response = await fetch(id ? `/api/estimates/${encodeURIComponent(id)}` : "/api/estimates", {
      method: id ? "PUT" : "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const result = await response.json();
    if (!response.ok) throw new Error(result.error || "Could not save estimate");
    closeModal();
    await loadData();
    showToast(id ? "Estimate updated." : "Estimate created.");
  } catch (error) {
    document.querySelector("#estimate-form-error").textContent = error.message;
  } finally {
    saveButton.disabled = false;
  }
});

rows.addEventListener("click", async (event) => {
  const convertButton = event.target.closest("[data-convert]");
  const printButton = event.target.closest("[data-print]");
  const editButton = event.target.closest("[data-edit]");
  const deleteButton = event.target.closest("[data-delete]");
  if (convertButton) {
    try {
      const response = await fetch(`/api/estimates/${encodeURIComponent(convertButton.dataset.convert)}/convert`, { method: "POST" });
      const result = await response.json();
      if (!response.ok) throw new Error(result.error || "Could not convert estimate");
      await loadData();
      window.dispatchEvent(new Event("billing:invoices-updated"));
      showToast(`Converted to invoice ${result.id}.`);
    } catch (error) {
      showToast(error.message);
    }
    return;
  }
  if (printButton) {
    const estimate = estimates.find((item) => item.id === printButton.dataset.print);
    if (estimate) openPrintPreview(estimate);
    return;
  }
  if (editButton) {
    const estimate = estimates.find((item) => item.id === editButton.dataset.edit);
    if (estimate) openModal(estimate);
    return;
  }
  if (deleteButton) {
    const estimate = estimates.find((item) => item.id === deleteButton.dataset.delete);
    if (!estimate || !confirm(`Delete estimate ${estimate.id}?`)) return;
    try {
      const response = await fetch(`/api/estimates/${encodeURIComponent(estimate.id)}`, { method: "DELETE" });
      const result = await response.json();
      if (!response.ok) throw new Error(result.error || "Could not delete estimate");
      await loadData();
      showToast("Estimate deleted.");
    } catch (error) {
      showToast(error.message);
    }
  }
});

search.addEventListener("input", renderEstimates);
statusFilter.addEventListener("change", renderEstimates);

function switchBillingTab(tabName, updateLocation = true) {
  const selectedTab = tabName === "invoices" ? "invoices" : "estimates";
  document.querySelectorAll("[data-billing-tab]").forEach((tab) => {
    const selected = tab.dataset.billingTab === selectedTab;
    tab.classList.toggle("active", selected);
    tab.setAttribute("aria-selected", String(selected));
    document.getElementById(tab.getAttribute("aria-controls")).hidden = !selected;
  });
  if (updateLocation && location.hash !== `#${selectedTab}`) {
    history.replaceState(null, "", `${location.pathname}#${selectedTab}`);
  }
}

document.querySelectorAll("[data-billing-tab]").forEach((tab) => {
  tab.addEventListener("click", () => switchBillingTab(tab.dataset.billingTab));
});
switchBillingTab(location.hash.slice(1), false);

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
