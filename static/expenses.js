let expenses = [];
let projects = [];
let toastTimer;

const rows = document.querySelector("#expense-rows");
const projectRows = document.querySelector("#project-expense-rows");
const expenseModal = document.querySelector("#expense-modal");
const expenseForm = document.querySelector("#expense-form");
const search = document.querySelector("#expense-search");
const categoryFilter = document.querySelector("#expense-category-filter");
const projectFilter = document.querySelector("#expense-project-filter");

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

function localDateValue() {
  const now = new Date();
  now.setMinutes(now.getMinutes() - now.getTimezoneOffset());
  return now.toISOString().slice(0, 10);
}

function showToast(message) {
  const toast = document.querySelector("#toast");
  toast.textContent = message;
  toast.classList.add("visible");
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => toast.classList.remove("visible"), 2400);
}

function updateSummary() {
  const currentMonth = localDateValue().slice(0, 7);
  const total = expenses.reduce((sum, expense) => sum + Number(expense.amount || 0), 0);
  const monthly = expenses
    .filter((expense) => expense.date.startsWith(currentMonth))
    .reduce((sum, expense) => sum + Number(expense.amount || 0), 0);
  const projectTotal = expenses
    .filter((expense) => expense.project_id)
    .reduce((sum, expense) => sum + Number(expense.amount || 0), 0);
  const categories = new Set(expenses.map((expense) => expense.category));

  document.querySelector("#expense-total-value").textContent = formatCurrency(total);
  document.querySelector("#expense-month-value").textContent = formatCurrency(monthly);
  document.querySelector("#expense-project-value").textContent = formatCurrency(projectTotal);
  document.querySelector("#expense-count").textContent = expenses.length;
  document.querySelector("#expense-category-count").textContent = `${categories.size} ${categories.size === 1 ? "category" : "categories"} used`;
  document.querySelector("#expense-month-label").textContent = new Intl.DateTimeFormat("en-IN", {
    month: "long",
    year: "numeric",
  }).format(new Date(`${currentMonth}-01T00:00:00`));
}

function renderProjectOptions(selectedId = "") {
  const options = projects.map((project) =>
    `<option value="${escapeHtml(project.id)}" ${project.id === selectedId ? "selected" : ""}>${escapeHtml(project.name)} · ${escapeHtml(project.id)}</option>`
  ).join("");
  document.querySelector("#expense-project").innerHTML = `<option value="">General / not assigned</option>${options}`;

  const selectedFilter = projectFilter.value;
  projectFilter.innerHTML = `<option value="All">All projects</option><option value="">General / not assigned</option>${options}`;
  if (selectedFilter === "All" || selectedFilter === "" || projects.some((project) => project.id === selectedFilter)) {
    projectFilter.value = selectedFilter;
  }
}

function renderProjectSummary() {
  const groups = new Map();
  expenses.forEach((expense) => {
    const key = expense.project_id || "";
    const group = groups.get(key) || {
      name: expense.project_name || "General / not assigned",
      id: key,
      count: 0,
      amount: 0,
    };
    group.count += 1;
    group.amount += Number(expense.amount || 0);
    groups.set(key, group);
  });

  const sortedGroups = [...groups.values()].sort((a, b) => b.amount - a.amount);
  projectRows.innerHTML = sortedGroups.length
    ? sortedGroups.map((group) => `<tr>
        <td><strong class="expense-project-name">${escapeHtml(group.name)}</strong><small class="expense-project-id">${escapeHtml(group.id || "Business expense")}</small></td>
        <td>${group.count}</td>
        <td><strong class="expense-amount">${formatCurrency(group.amount)}</strong></td>
      </tr>`).join("")
    : '<tr><td colspan="3" class="empty-state">Project totals will appear after you record an expense.</td></tr>';
}

function renderExpenses() {
  const query = search.value.trim().toLowerCase();
  const selectedCategory = categoryFilter.value;
  const selectedProject = projectFilter.value;
  const filtered = expenses.filter((expense) => {
    const matchesCategory = selectedCategory === "All" || expense.category === selectedCategory;
    const matchesProject = selectedProject === "All"
      || (selectedProject === "" && !expense.project_id)
      || expense.project_id === selectedProject;
    const searchable = [
      expense.id, expense.description, expense.category, expense.project_name,
      expense.vendor, expense.payment_method, expense.notes,
    ].join(" ").toLowerCase();
    return matchesCategory && matchesProject && searchable.includes(query);
  }).sort((a, b) => b.date.localeCompare(a.date) || b.id.localeCompare(a.id));

  rows.innerHTML = filtered.length
    ? filtered.map((expense) => `<tr>
        <td>${formatDate(expense.date)}</td>
        <td><div class="expense-description"><strong>${escapeHtml(expense.description)}</strong><small>${escapeHtml(expense.id)}</small></div></td>
        <td><span class="expense-category">${escapeHtml(expense.category)}</span></td>
        <td><div class="expense-project"><strong>${escapeHtml(expense.project_name || "General / not assigned")}</strong>${expense.project_id ? `<small>${escapeHtml(expense.project_id)}</small>` : ""}</div></td>
        <td>${escapeHtml(expense.vendor || "—")}</td>
        <td>${escapeHtml(expense.payment_method)}</td>
        <td><strong class="expense-amount">${formatCurrency(expense.amount)}</strong></td>
        <td><div class="row-actions">
          <button type="button" class="row-button edit" data-edit="${escapeHtml(expense.id)}">Edit</button>
          <button type="button" class="row-button delete" data-delete="${escapeHtml(expense.id)}">Delete</button>
        </div></td>
      </tr>`).join("")
    : `<tr><td colspan="8" class="empty-state">${expenses.length ? "No expenses match these filters." : "No expenses yet. Add an expense to start tracking costs."}</td></tr>`;
}

async function loadData() {
  try {
    const [expensesResponse, projectsResponse] = await Promise.all([
      fetch("/api/expenses"),
      fetch("/api/projects"),
    ]);
    if (!expensesResponse.ok || !projectsResponse.ok) throw new Error("Could not load expenses and projects");
    expenses = await expensesResponse.json();
    projects = await projectsResponse.json();
    renderProjectOptions();
    updateSummary();
    renderProjectSummary();
    renderExpenses();
    return true;
  } catch (error) {
    rows.innerHTML = '<tr><td colspan="8" class="empty-state">Could not load expenses. Check the server and try again.</td></tr>';
    projectRows.innerHTML = '<tr><td colspan="3" class="empty-state">Could not load project totals.</td></tr>';
    console.error(error);
    return false;
  }
}

function openExpenseModal(expense = null) {
  expenseForm.reset();
  document.querySelector("#expense-form-error").textContent = "";
  document.querySelector("#expense-modal-title").textContent = expense ? "Edit expense" : "Add expense";
  document.querySelector("#expense-id").value = expense?.id || "";
  document.querySelector("#expense-date").value = expense?.date || localDateValue();
  document.querySelector("#expense-category").value = expense?.category || "Material";
  document.querySelector("#expense-description").value = expense?.description || "";
  document.querySelector("#expense-amount").value = expense?.amount ?? "";
  document.querySelector("#expense-vendor").value = expense?.vendor || "";
  document.querySelector("#expense-payment-method").value = expense?.payment_method || "Cash";
  document.querySelector("#expense-notes").value = expense?.notes || "";
  renderProjectOptions(expense?.project_id || "");
  expenseModal.classList.add("open");
  expenseModal.setAttribute("aria-hidden", "false");
  setTimeout(() => document.querySelector("#expense-description").focus(), 100);
}

function closeExpenseModal() {
  expenseModal.classList.remove("open");
  expenseModal.setAttribute("aria-hidden", "true");
}

document.querySelector("#add-expense").addEventListener("click", () => openExpenseModal());
document.querySelector("#expense-modal-close").addEventListener("click", closeExpenseModal);
document.querySelector("#expense-cancel").addEventListener("click", closeExpenseModal);
expenseModal.addEventListener("click", (event) => {
  if (event.target === expenseModal) closeExpenseModal();
});
document.addEventListener("keydown", (event) => {
  if (event.key === "Escape") closeExpenseModal();
});

expenseForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const saveButton = expenseForm.querySelector('button[type="submit"]');
  saveButton.disabled = true;
  const id = document.querySelector("#expense-id").value;
  const payload = {
    date: document.querySelector("#expense-date").value,
    category: document.querySelector("#expense-category").value,
    description: document.querySelector("#expense-description").value.trim(),
    amount: Number(document.querySelector("#expense-amount").value),
    project_id: document.querySelector("#expense-project").value,
    vendor: document.querySelector("#expense-vendor").value.trim(),
    payment_method: document.querySelector("#expense-payment-method").value,
    notes: document.querySelector("#expense-notes").value.trim(),
  };
  try {
    const response = await fetch(id ? `/api/expenses/${encodeURIComponent(id)}` : "/api/expenses", {
      method: id ? "PUT" : "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const result = await response.json();
    if (!response.ok) throw new Error(result.error || "Could not save expense");
    closeExpenseModal();
    const refreshed = await loadData();
    showToast(refreshed
      ? (id ? "Expense updated." : "Expense added.")
      : "Expense saved, but the list could not refresh. Reload the page.");
  } catch (error) {
    document.querySelector("#expense-form-error").textContent = error.message;
  } finally {
    saveButton.disabled = false;
  }
});

rows.addEventListener("click", async (event) => {
  const editButton = event.target.closest("[data-edit]");
  const deleteButton = event.target.closest("[data-delete]");
  if (editButton) {
    const expense = expenses.find((item) => item.id === editButton.dataset.edit);
    if (expense) openExpenseModal(expense);
    return;
  }
  if (deleteButton) {
    const expense = expenses.find((item) => item.id === deleteButton.dataset.delete);
    if (!expense || !confirm(`Delete expense "${expense.description}"?`)) return;
    try {
      const response = await fetch(`/api/expenses/${encodeURIComponent(expense.id)}`, { method: "DELETE" });
      const result = await response.json();
      if (!response.ok) throw new Error(result.error || "Could not delete expense");
      const refreshed = await loadData();
      showToast(refreshed ? "Expense deleted." : "Expense deleted, but the list could not refresh. Reload the page.");
    } catch (error) {
      showToast(error.message);
    }
  }
});

search.addEventListener("input", renderExpenses);
categoryFilter.addEventListener("change", renderExpenses);
projectFilter.addEventListener("change", renderExpenses);

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
