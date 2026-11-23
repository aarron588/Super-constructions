let customers = [];

const rows = document.querySelector("#customer-rows");
const modal = document.querySelector("#customer-modal");
const form = document.querySelector("#customer-form");
const search = document.querySelector("#customer-search");
const statusFilter = document.querySelector("#status-filter");

function escapeHtml(value) {
  const span = document.createElement("span");
  span.textContent = value ?? "";
  return span.innerHTML;
}

function showToast(message) {
  const toast = document.querySelector("#toast");
  toast.textContent = message;
  toast.classList.add("visible");
  setTimeout(() => toast.classList.remove("visible"), 2400);
}

function updateSummary() {
  document.querySelector("#total-customers").textContent = customers.length;
  document.querySelector("#active-customers").textContent = customers.filter((customer) => customer.status === "Active").length;
  document.querySelector("#project-customers").textContent = customers.filter((customer) => Number(customer.projects) > 0).length;
}

function renderCustomers() {
  const query = search.value.trim().toLowerCase();
  const status = statusFilter.value;
  const filtered = customers.filter((customer) => {
    const matchesStatus = status === "All" || customer.status === status;
    const searchable = [customer.name, customer.contact, customer.email, customer.company, customer.id].join(" ").toLowerCase();
    return matchesStatus && searchable.includes(query);
  });

  if (!filtered.length) {
    rows.innerHTML = '<tr><td colspan="7" class="empty-state">No customers match this view.</td></tr>';
    return;
  }

  rows.innerHTML = filtered.map((customer) => {
    const initials = customer.name.split(" ").map((part) => part[0]).join("").slice(0, 2).toUpperCase();
    return `<tr>
      <td><div class="customer-person"><span class="customer-avatar">${escapeHtml(initials)}</span><div><strong>${escapeHtml(customer.name)}</strong><small>${escapeHtml(customer.id)} · ${escapeHtml(customer.email)}</small></div></div></td>
      <td><strong class="table-primary">${escapeHtml(customer.contact)}</strong></td>
      <td>${escapeHtml(customer.company || "—")}</td>
      <td><span class="project-count">${Number(customer.projects) || 0}</span></td>
      <td><strong class="${customer.balance === "₹0" ? "balance-clear" : "balance-due"}">${escapeHtml(customer.balance || "₹0")}</strong></td>
      <td><span class="customer-status ${customer.status === "Active" ? "active" : "inactive"}">${escapeHtml(customer.status)}</span></td>
      <td><div class="row-actions"><button type="button" class="row-button edit" data-edit="${escapeHtml(customer.id)}" aria-label="Edit ${escapeHtml(customer.name)}">Edit</button><button type="button" class="row-button delete" data-delete="${escapeHtml(customer.id)}" aria-label="Delete ${escapeHtml(customer.name)}">Delete</button></div></td>
    </tr>`;
  }).join("");
}

async function loadCustomers() {
  try {
    const response = await fetch("/api/customers");
    if (!response.ok) throw new Error("Could not load customers");
    customers = await response.json();
    updateSummary();
    renderCustomers();
  } catch (error) {
    rows.innerHTML = '<tr><td colspan="7" class="empty-state">Could not load customers.</td></tr>';
  }
}

function openModal(customer = null) {
  form.reset();
  document.querySelector("#form-error").textContent = "";
  document.querySelector("#customer-modal-title").textContent = customer ? "Edit customer" : "Add customer";
  document.querySelector("#customer-id").value = customer?.id || "";
  document.querySelector("#customer-name").value = customer?.name || "";
  document.querySelector("#customer-contact").value = customer?.contact || "";
  document.querySelector("#customer-email").value = customer?.email || "";
  document.querySelector("#customer-company").value = customer?.company || "";
  document.querySelector("#customer-status").value = customer?.status || "Active";
  document.querySelector("#customer-address").value = customer?.address || "";
  modal.classList.add("open");
  modal.setAttribute("aria-hidden", "false");
  setTimeout(() => document.querySelector("#customer-name").focus(), 100);
}

function closeModal() {
  modal.classList.remove("open");
  modal.setAttribute("aria-hidden", "true");
}

document.querySelector("#add-customer").addEventListener("click", () => openModal());
document.querySelector("#modal-close").addEventListener("click", closeModal);
document.querySelector("#modal-cancel").addEventListener("click", closeModal);
modal.addEventListener("click", (event) => { if (event.target === modal) closeModal(); });
document.addEventListener("keydown", (event) => { if (event.key === "Escape") closeModal(); });

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const id = document.querySelector("#customer-id").value;
  const payload = {
    name: document.querySelector("#customer-name").value.trim(),
    contact: document.querySelector("#customer-contact").value.trim(),
    email: document.querySelector("#customer-email").value.trim(),
    company: document.querySelector("#customer-company").value.trim(),
    status: document.querySelector("#customer-status").value,
    address: document.querySelector("#customer-address").value.trim(),
  };
  const existing = customers.find((customer) => customer.id === id);
  if (existing) Object.assign(payload, { projects: existing.projects, paid: existing.paid, balance: existing.balance });

  try {
    const response = await fetch(id ? `/api/customers/${encodeURIComponent(id)}` : "/api/customers", {
      method: id ? "PUT" : "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const result = await response.json();
    if (!response.ok) throw new Error(result.error || "Could not save customer");
    if (id) customers = customers.map((customer) => customer.id === id ? result : customer);
    else customers.push(result);
    updateSummary();
    renderCustomers();
    closeModal();
    showToast(id ? "Customer updated successfully." : "Customer added successfully.");
  } catch (error) {
    document.querySelector("#form-error").textContent = error.message;
  }
});

rows.addEventListener("click", async (event) => {
  const editButton = event.target.closest("[data-edit]");
  const deleteButton = event.target.closest("[data-delete]");
  if (editButton) {
    openModal(customers.find((customer) => customer.id === editButton.dataset.edit));
  }
  if (deleteButton) {
    const customer = customers.find((item) => item.id === deleteButton.dataset.delete);
    if (!customer || !confirm(`Delete ${customer.name}?`)) return;
    const response = await fetch(`/api/customers/${encodeURIComponent(customer.id)}`, { method: "DELETE" });
    if (response.ok) {
      customers = customers.filter((item) => item.id !== customer.id);
      updateSummary();
      renderCustomers();
      showToast("Customer deleted.");
    }
  }
});

search.addEventListener("input", renderCustomers);
statusFilter.addEventListener("change", renderCustomers);

const menuButton = document.querySelector("#menu-button");
const sidebar = document.querySelector("#sidebar");
menuButton.addEventListener("click", () => {
  const open = sidebar.classList.toggle("open");
  menuButton.setAttribute("aria-expanded", String(open));
});

document.querySelectorAll("[data-module]").forEach((button) => {
  button.addEventListener("click", () => showToast(`${button.dataset.module} will be added in a later module.`));
});

loadCustomers();
