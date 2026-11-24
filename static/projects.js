let projects = [];
let toastTimer;

const rows = document.querySelector("#project-rows");
const modal = document.querySelector("#project-modal");
const form = document.querySelector("#project-form");
const search = document.querySelector("#project-search");
const statusFilter = document.querySelector("#project-status-filter");

function escapeHtml(value) {
  const span = document.createElement("span");
  span.textContent = value ?? "";
  return span.innerHTML;
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
    maximumFractionDigits: 0,
  }).format(Number(value) || 0);
}

function formatDate(value) {
  if (!value) return "—";
  return new Intl.DateTimeFormat("en-IN", { day: "numeric", month: "short", year: "numeric" })
    .format(new Date(`${value}T00:00:00`));
}

function updateSummary() {
  document.querySelector("#total-projects").textContent = projects.length;
  document.querySelector("#in-progress-projects").textContent = projects.filter((project) => project.status === "In progress").length;
  document.querySelector("#on-hold-projects").textContent = projects.filter((project) => project.status === "On hold").length;
  document.querySelector("#completed-projects").textContent = projects.filter((project) => project.status === "Completed").length;
}

function renderProjects() {
  const query = search.value.trim().toLowerCase();
  const selectedStatus = statusFilter.value;
  const filtered = projects.filter((project) => {
    const matchesStatus = selectedStatus === "All" || project.status === selectedStatus;
    const searchable = [project.name, project.location, project.supervisor, project.id].join(" ").toLowerCase();
    return matchesStatus && searchable.includes(query);
  });

  if (!filtered.length) {
    rows.innerHTML = '<tr><td colspan="7" class="empty-state">No projects match this view.</td></tr>';
    return;
  }

  rows.innerHTML = filtered.map((project) => {
    const statusClass = project.status === "Completed" ? "green" : project.status === "On hold" ? "orange" : project.status === "In progress" ? "blue" : "neutral";
    return `<tr>
      <td><div class="project-cell"><span class="project-avatar" aria-hidden="true">⌂</span><div><strong>${escapeHtml(project.name)}</strong><small>${escapeHtml(project.id)}</small></div></div></td>
      <td>${escapeHtml(project.location)}</td>
      <td><div class="schedule-cell"><strong>${formatDate(project.start_date)}</strong><small>to ${formatDate(project.expected_completion_date)}</small></div></td>
      <td><div class="amount-cell"><strong>${formatCurrency(project.contract_amount)}</strong><small>Budget ${formatCurrency(project.budget)}</small></div></td>
      <td><div class="project-progress"><div class="progress-label"><span>Progress</span><strong>${project.progress}%</strong></div><div class="progress-track" role="progressbar" aria-label="${escapeHtml(project.name)} progress" aria-valuenow="${project.progress}" aria-valuemin="0" aria-valuemax="100"><div class="progress-bar" style="width:${project.progress}%"></div></div></div></td>
      <td><span class="project-status ${statusClass}">${escapeHtml(project.status)}</span></td>
      <td><div class="row-actions"><button type="button" class="row-button edit" data-edit="${escapeHtml(project.id)}" aria-label="Edit ${escapeHtml(project.name)}">Edit</button><button type="button" class="row-button delete" data-delete="${escapeHtml(project.id)}" aria-label="Delete ${escapeHtml(project.name)}">Delete</button></div></td>
    </tr>`;
  }).join("");
}

async function loadProjects() {
  try {
    const response = await fetch("/api/projects");
    if (!response.ok) throw new Error("Could not load projects");
    projects = await response.json();
    updateSummary();
    renderProjects();
    return true;
  } catch (error) {
    rows.innerHTML = '<tr><td colspan="7" class="empty-state">Could not load projects. Check the server and try again.</td></tr>';
    console.error(error);
    return false;
  }
}

function openModal(project = null) {
  form.reset();
  document.querySelector("#project-form-error").textContent = "";
  document.querySelector("#project-modal-title").textContent = project ? "Edit project" : "Add project";
  document.querySelector("#project-id").value = project?.id || "";
  document.querySelector("#project-name").value = project?.name || "";
  document.querySelector("#project-location").value = project?.location || "";
  document.querySelector("#project-supervisor").value = project?.supervisor || "";
  document.querySelector("#project-start-date").value = project?.start_date || "";
  document.querySelector("#project-end-date").value = project?.expected_completion_date || "";
  document.querySelector("#project-budget").value = project?.budget ?? 0;
  document.querySelector("#project-contract").value = project?.contract_amount ?? 0;
  document.querySelector("#project-status").value = project?.status || "Planning";
  document.querySelector("#project-progress").value = project?.progress ?? 0;
  modal.classList.add("open");
  modal.setAttribute("aria-hidden", "false");
  setTimeout(() => document.querySelector("#project-name").focus(), 100);
}

function closeModal() {
  modal.classList.remove("open");
  modal.setAttribute("aria-hidden", "true");
}

document.querySelector("#add-project").addEventListener("click", () => openModal());
document.querySelector("#project-modal-close").addEventListener("click", closeModal);
document.querySelector("#project-cancel").addEventListener("click", closeModal);
modal.addEventListener("click", (event) => { if (event.target === modal) closeModal(); });
document.addEventListener("keydown", (event) => { if (event.key === "Escape") closeModal(); });

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const saveButton = form.querySelector('button[type="submit"]');
  saveButton.disabled = true;
  const id = document.querySelector("#project-id").value;
  const payload = {
    name: document.querySelector("#project-name").value.trim(),
    location: document.querySelector("#project-location").value.trim(),
    supervisor: document.querySelector("#project-supervisor").value.trim(),
    start_date: document.querySelector("#project-start-date").value,
    expected_completion_date: document.querySelector("#project-end-date").value,
    budget: Number(document.querySelector("#project-budget").value),
    contract_amount: Number(document.querySelector("#project-contract").value),
    status: document.querySelector("#project-status").value,
    progress: Number(document.querySelector("#project-progress").value),
  };
  try {
    const response = await fetch(id ? `/api/projects/${encodeURIComponent(id)}` : "/api/projects", {
      method: id ? "PUT" : "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const result = await response.json();
    if (!response.ok) throw new Error(result.error || "Could not save project");
    closeModal();
    const refreshed = await loadProjects();
    showToast(refreshed
      ? (id ? "Project updated successfully." : "Project added successfully.")
      : "Project saved, but the list could not refresh. Reload the page.");
  } catch (error) {
    document.querySelector("#project-form-error").textContent = error.message;
  } finally {
    saveButton.disabled = false;
  }
});

rows.addEventListener("click", async (event) => {
  const editButton = event.target.closest("[data-edit]");
  const deleteButton = event.target.closest("[data-delete]");
  if (editButton) {
    openModal(projects.find((project) => project.id === editButton.dataset.edit));
  }
  if (deleteButton) {
    const project = projects.find((item) => item.id === deleteButton.dataset.delete);
    if (!project || !confirm(`Delete project "${project.name}"?`)) return;
    try {
      const response = await fetch(`/api/projects/${encodeURIComponent(project.id)}`, { method: "DELETE" });
      const result = await response.json();
      if (!response.ok) throw new Error(result.error || "Could not delete project");
      const refreshed = await loadProjects();
      showToast(refreshed ? "Project deleted." : "Project deleted, but the list could not refresh. Reload the page.");
    } catch (error) {
      showToast(error.message);
    }
  }
});

search.addEventListener("input", renderProjects);
statusFilter.addEventListener("change", renderProjects);

const menuButton = document.querySelector("#menu-button");
const sidebar = document.querySelector("#sidebar");
menuButton.addEventListener("click", () => {
  const open = sidebar.classList.toggle("open");
  menuButton.setAttribute("aria-expanded", String(open));
});

document.querySelectorAll("[data-module]").forEach((button) => {
  button.addEventListener("click", () => showToast(`${button.dataset.module} will be added in a later module.`));
});

loadProjects();
