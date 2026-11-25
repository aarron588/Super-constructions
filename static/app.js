const iconMarkup = {
  projects: '<path d="M3 20V8l9-5 9 5v12h-6v-7H9v7H3Z"/><path d="M3 9h18"/>',
  ongoing: '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
  completed: '<circle cx="12" cy="12" r="9"/><path d="m8 12 2.5 2.5L16 9"/>',
  revenue: '<path d="M4 18V6m0 12h16"/><path d="m7 14 4-4 3 3 5-6"/>',
  payments: '<path d="M3 7h18v12H3zM3 11h18"/><path d="M7 15h3"/>',
  expenses: '<rect x="3" y="5" width="18" height="14" rx="2"/><path d="M3 10h18m-13 5h4"/>',
  profit: '<path d="M4 17 9 12l4 3 7-8"/><path d="M15 7h5v5"/>',
};

function escapeHtml(value) {
  const span = document.createElement("span");
  span.textContent = value ?? "";
  return span.innerHTML.replace(/"/g, "&quot;").replace(/'/g, "&#39;");
}

function renderMetrics(metrics) {
  const container = document.querySelector("#metrics");
  container.innerHTML = metrics.map((metric) => `
    <article class="metric-card">
      <div class="metric-top">
        <span class="metric-label">${escapeHtml(metric.label)}</span>
        <span class="metric-icon tone-${escapeHtml(metric.tone)}" aria-hidden="true">
          <svg viewBox="0 0 24 24">${iconMarkup[metric.icon] || ""}</svg>
        </span>
      </div>
      <div class="metric-value">${escapeHtml(metric.value)}</div>
      <div class="metric-change">${escapeHtml(metric.change)}</div>
    </article>
  `).join("");
}

function renderProjects(projects) {
  document.querySelector("#projects").innerHTML = projects.map((project) => `
    <div class="project-row">
      <div>
        <div class="project-name">${escapeHtml(project.name)}</div>
        <div class="project-location">${escapeHtml(project.location)}</div>
      </div>
      <div>
        <div class="progress-label"><span>Progress</span><strong>${escapeHtml(project.progress)}%</strong></div>
        <div class="progress-track" role="progressbar" aria-label="${escapeHtml(project.name)} progress" aria-valuenow="${escapeHtml(project.progress)}" aria-valuemin="0" aria-valuemax="100">
          <div class="progress-bar" style="width: ${escapeHtml(project.progress)}%"></div>
        </div>
      </div>
      <span class="status status-${escapeHtml(project.tone)}">${escapeHtml(project.status)}</span>
    </div>
  `).join("");
}

function renderActivities(activities) {
  const symbols = { payment: "₹", project: "⌂", invoice: "▤", material: "◇", expense: "₹" };
  document.querySelector("#activities").innerHTML = activities.map((activity) => `
    <div class="activity-row">
      <span class="activity-icon ${escapeHtml(activity.kind)}" aria-hidden="true">${symbols[activity.kind] || "•"}</span>
      <div>
        <div class="activity-title">${escapeHtml(activity.title)}</div>
        <div class="activity-description">${escapeHtml(activity.description)}</div>
      </div>
      <time class="activity-time">${escapeHtml(activity.time)}</time>
    </div>
  `).join("");
}

async function loadDashboard() {
  const refreshButton = document.querySelector("#dashboard-refresh");
  refreshButton.disabled = true;
  refreshButton.classList.add("is-refreshing");
  try {
    const response = await fetch("/api/dashboard");
    if (!response.ok) throw new Error(`Dashboard request failed (${response.status})`);
    const data = await response.json();
    renderMetrics(data.metrics);
    renderProjects(data.projects);
    renderActivities(data.activities);
    document.querySelector("#dashboard-date").textContent = new Intl.DateTimeFormat("en-IN", {
      weekday: "long", day: "numeric", month: "long", year: "numeric",
    }).format(new Date()).toUpperCase();
  } catch (error) {
    document.querySelector("#metrics").innerHTML = '<div class="error-message">Could not load dashboard data. Check that the Python server is running, then refresh.</div>';
    document.querySelector("#projects").innerHTML = "";
    document.querySelector("#activities").innerHTML = "";
    console.error(error);
  } finally {
    refreshButton.disabled = false;
    refreshButton.classList.remove("is-refreshing");
  }
}

const sidebar = document.querySelector("#sidebar");
const menuButton = document.querySelector("#menu-button");
menuButton.addEventListener("click", () => {
  const open = sidebar.classList.toggle("open");
  menuButton.setAttribute("aria-expanded", String(open));
});

let toastTimer;
document.querySelectorAll("[data-module]").forEach((button) => {
  button.addEventListener("click", () => {
    const toast = document.querySelector("#toast");
    toast.textContent = `${button.dataset.module} will be added in a later module.`;
    toast.classList.add("visible");
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => toast.classList.remove("visible"), 2600);
  });
});

document.querySelector("#dashboard-refresh").addEventListener("click", loadDashboard);
document.addEventListener("visibilitychange", () => {
  if (!document.hidden) loadDashboard();
});
window.setInterval(() => {
  if (!document.hidden) loadDashboard();
}, 60000);

loadDashboard();
