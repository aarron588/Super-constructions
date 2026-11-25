let projects = [];
let updates = [];
let toastTimer;

const cards = document.querySelector("#project-progress-cards");
const rows = document.querySelector("#progress-rows");
const modal = document.querySelector("#progress-modal");
const form = document.querySelector("#progress-form");
const projectFilter = document.querySelector("#progress-project-filter");

function escapeHtml(value) {
  const span = document.createElement("span");
  span.textContent = value ?? "";
  return span.innerHTML.replace(/"/g, "&quot;").replace(/'/g, "&#39;");
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

function latestUpdate(projectId) {
  return updates.filter((entry) => entry.project_id === projectId)
    .sort((a, b) => b.date.localeCompare(a.date))[0];
}

function renderSummary() {
  const month = localDateValue().slice(0, 7);
  const today = localDateValue();
  document.querySelector("#progress-project-count").textContent = projects.length;
  document.querySelector("#progress-average").textContent = projects.length
    ? `${Math.round(projects.reduce((sum, project) => sum + Number(project.progress || 0), 0) / projects.length)}%`
    : "0%";
  document.querySelector("#progress-month-updates").textContent = updates.filter((entry) => entry.date.startsWith(month)).length;
  document.querySelector("#progress-delayed-count").textContent = projects.filter((project) =>
    project.status !== "Completed" && project.expected_completion_date < today
  ).length;
}

function renderProjectCards() {
  cards.innerHTML = projects.length
    ? projects.map((project) => {
      const recent = latestUpdate(project.id);
      return `<article class="project-progress-card">
        <div class="project-progress-card-top"><div><strong>${escapeHtml(project.name)}</strong><small>${escapeHtml(project.location)} · ${escapeHtml(project.id)}</small></div><span class="project-status ${project.status === "Completed" ? "green" : project.status === "On hold" ? "orange" : "blue"}">${escapeHtml(project.status)}</span></div>
        <div class="progress-label"><span>Overall completion</span><strong>${Number(project.progress || 0)}%</strong></div>
        <div class="progress-track" role="progressbar" aria-label="${escapeHtml(project.name)} completion" aria-valuenow="${Number(project.progress || 0)}" aria-valuemin="0" aria-valuemax="100"><div class="progress-bar" style="width:${Number(project.progress || 0)}%"></div></div>
        <div class="project-progress-card-footer"><span>${recent ? `Last update ${formatDate(recent.date)}` : "No daily updates yet"}</span><button type="button" class="text-button" data-add-project-update="${escapeHtml(project.id)}">Add update →</button></div>
      </article>`;
    }).join("")
    : '<div class="empty-state">Create a project before adding progress updates.</div>';
}

function renderUpdates() {
  const selectedProject = projectFilter.value;
  const filtered = updates.filter((entry) => selectedProject === "All" || entry.project_id === selectedProject)
    .sort((a, b) => b.date.localeCompare(a.date) || b.id.localeCompare(a.id));
  rows.innerHTML = filtered.length
    ? filtered.map((entry) => `<tr>
        <td>${formatDate(entry.date)}</td><td><strong class="expense-project-name">${escapeHtml(entry.project_name)}</strong><small class="expense-project-id">${escapeHtml(entry.project_id)}</small></td>
        <td><div class="progress-label"><strong>${entry.progress}%</strong></div><div class="progress-track progress-small"><div class="progress-bar" style="width:${entry.progress}%"></div></div></td>
        <td class="progress-summary-cell"><strong>${escapeHtml(entry.summary)}</strong>${entry.notes ? `<small>${escapeHtml(entry.notes)}</small>` : ""}</td>
        <td class="task-list-cell">${entry.completed_tasks.length ? entry.completed_tasks.map((task) => `<span class="task-chip completed-task">${escapeHtml(task)}</span>`).join("") : "—"}</td>
        <td class="task-list-cell">${entry.pending_tasks.length ? entry.pending_tasks.map((task) => `<span class="task-chip">${escapeHtml(task)}</span>`).join("") : "—"}</td>
      </tr>`).join("")
    : `<tr><td colspan="6" class="empty-state">${updates.length ? "No work updates match this project." : "Daily work updates will appear here."}</td></tr>`;
}

async function loadData() {
  try {
    const [projectResponse, updateResponse] = await Promise.all([
      fetch("/api/projects"),
      fetch("/api/progress"),
    ]);
    if (!projectResponse.ok || !updateResponse.ok) throw new Error("Could not load projects and progress updates");
    projects = await projectResponse.json();
    updates = await updateResponse.json();
    const selected = projectFilter.value || "All";
    projectFilter.innerHTML = `<option value="All">All projects</option>${projects.map((project) =>
      `<option value="${escapeHtml(project.id)}">${escapeHtml(project.name)} · ${escapeHtml(project.id)}</option>`
    ).join("")}`;
    projectFilter.value = projects.some((project) => project.id === selected) || selected === "All" ? selected : "All";
    document.querySelector("#progress-project").innerHTML = `<option value="">Select a project</option>${projects.map((project) =>
      `<option value="${escapeHtml(project.id)}">${escapeHtml(project.name)} · ${escapeHtml(project.id)}</option>`
    ).join("")}`;
    document.querySelector("#add-progress").disabled = projects.length === 0;
    renderSummary();
    renderProjectCards();
    renderUpdates();
    return true;
  } catch (error) {
    cards.innerHTML = '<div class="error-message">Could not load project progress. Check the server and try again.</div>';
    rows.innerHTML = '<tr><td colspan="6" class="empty-state">Could not load work updates.</td></tr>';
    console.error(error);
    return false;
  }
}

function openModal(projectId = "") {
  form.reset();
  document.querySelector("#progress-form-error").textContent = "";
  document.querySelector("#progress-date").value = localDateValue();
  const projectIdValue = projectId || (projectFilter.value !== "All" ? projectFilter.value : "");
  const project = projects.find((item) => item.id === projectIdValue);
  document.querySelector("#progress-project").value = project?.id || "";
  document.querySelector("#progress-percent").value = project?.progress ?? 0;
  modal.classList.add("open");
  modal.setAttribute("aria-hidden", "false");
  setTimeout(() => document.querySelector("#progress-project").focus(), 100);
}

function closeModal() {
  modal.classList.remove("open");
  modal.setAttribute("aria-hidden", "true");
}

document.querySelector("#add-progress").addEventListener("click", () => openModal());
document.querySelector("#progress-modal-close").addEventListener("click", closeModal);
document.querySelector("#progress-cancel").addEventListener("click", closeModal);
modal.addEventListener("click", (event) => { if (event.target === modal) closeModal(); });
document.addEventListener("keydown", (event) => { if (event.key === "Escape") closeModal(); });
projectFilter.addEventListener("change", renderUpdates);
cards.addEventListener("click", (event) => {
  const button = event.target.closest("[data-add-project-update]");
  if (button) openModal(button.dataset.addProjectUpdate);
});

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const button = form.querySelector('button[type="submit"]');
  button.disabled = true;
  const payload = {
    project_id: document.querySelector("#progress-project").value,
    date: document.querySelector("#progress-date").value,
    progress: Number(document.querySelector("#progress-percent").value),
    summary: document.querySelector("#progress-summary").value.trim(),
    completed_tasks: document.querySelector("#progress-completed").value.split("\n").map((task) => task.trim()).filter(Boolean),
    pending_tasks: document.querySelector("#progress-pending").value.split("\n").map((task) => task.trim()).filter(Boolean),
    notes: document.querySelector("#progress-notes").value.trim(),
  };
  try {
    const response = await fetch("/api/progress", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const result = await response.json();
    if (!response.ok) throw new Error(result.error || "Could not save work update");
    closeModal();
    showToast((await loadData()) ? "Project progress updated." : "Update saved, but the page could not refresh.");
  } catch (error) {
    document.querySelector("#progress-form-error").textContent = error.message;
  } finally {
    button.disabled = false;
  }
});

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
