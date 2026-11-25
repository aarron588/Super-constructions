let materials = [];
let projects = [];
let toastTimer;

const rows = document.querySelector("#material-rows");
const materialModal = document.querySelector("#material-modal");
const materialForm = document.querySelector("#material-form");
const movementModal = document.querySelector("#movement-modal");
const movementForm = document.querySelector("#movement-form");
const historyModal = document.querySelector("#history-modal");
const search = document.querySelector("#material-search");
const categoryFilter = document.querySelector("#material-category-filter");
const stockFilter = document.querySelector("#material-stock-filter");

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

function formatQuantity(value) {
  return new Intl.NumberFormat("en-IN", { maximumFractionDigits: 3 }).format(Number(value) || 0);
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

function stockStatus(material) {
  const quantity = Number(material.quantity) || 0;
  const minimum = Number(material.minimum_stock) || 0;
  if (quantity <= 0) return "Out of stock";
  if (minimum > 0 && quantity <= minimum) return "Low stock";
  return "In stock";
}

function updateSummary() {
  document.querySelector("#material-count").textContent = materials.length;
  document.querySelector("#material-stock-value").textContent = formatCurrency(
    materials.reduce((sum, material) => sum + Number(material.quantity || 0) * Number(material.purchase_price || 0), 0)
  );
  document.querySelector("#material-low-count").textContent = materials.filter((material) => stockStatus(material) !== "In stock").length;
  document.querySelector("#material-movement-count").textContent = materials.reduce(
    (sum, material) => sum + (material.movements || []).length,
    0
  );
}

function renderMaterials() {
  const query = search.value.trim().toLowerCase();
  const selectedCategory = categoryFilter.value;
  const selectedStock = stockFilter.value;
  const filtered = materials.filter((material) => {
    const matchesCategory = selectedCategory === "All" || material.category === selectedCategory;
    const matchesStock = selectedStock === "All" || stockStatus(material) === selectedStock;
    const searchable = [material.id, material.name, material.category, material.supplier_name].join(" ").toLowerCase();
    return matchesCategory && matchesStock && searchable.includes(query);
  });

  if (!filtered.length) {
    rows.innerHTML = `<tr><td colspan="8" class="empty-state">${materials.length ? "No materials match this view." : "No materials yet. Add a material to start tracking stock."}</td></tr>`;
    return;
  }

  rows.innerHTML = filtered.map((material) => {
    const status = stockStatus(material);
    const statusClass = status === "In stock" ? "green" : status === "Low stock" ? "orange" : "neutral";
    const canDelete = Number(material.quantity) === 0 && !(material.movements || []).length;
    const deleteAction = canDelete ? `<button type="button" class="row-button delete" data-delete="${escapeHtml(material.id)}">Delete</button>` : "";
    return `<tr>
      <td><div class="project-cell"><span class="material-avatar" aria-hidden="true">▦</span><div><strong>${escapeHtml(material.name)}</strong><small>${escapeHtml(material.id)}</small></div></div></td>
      <td>${escapeHtml(material.category)}</td>
      <td><strong class="material-quantity">${formatQuantity(material.quantity)} ${escapeHtml(material.unit)}</strong></td>
      <td>${formatCurrency(material.purchase_price)}</td>
      <td>${escapeHtml(material.supplier_name || "—")}</td>
      <td>${formatQuantity(material.minimum_stock)} ${escapeHtml(material.unit)}</td>
      <td><span class="project-status ${statusClass}">${status}</span></td>
      <td><div class="row-actions">
        <button type="button" class="row-button stock-in" data-stock-in="${escapeHtml(material.id)}">Stock in</button>
        <button type="button" class="row-button stock-out" data-stock-out="${escapeHtml(material.id)}">Stock out</button>
        <button type="button" class="row-button history" data-history="${escapeHtml(material.id)}">History</button>
        <button type="button" class="row-button edit" data-edit="${escapeHtml(material.id)}">Edit</button>${deleteAction}
      </div></td>
    </tr>`;
  }).join("");
}

async function loadData() {
  try {
    const [materialsResponse, projectsResponse] = await Promise.all([
      fetch("/api/materials"),
      fetch("/api/projects"),
    ]);
    if (!materialsResponse.ok || !projectsResponse.ok) throw new Error("Could not load materials and projects");
    materials = await materialsResponse.json();
    projects = await projectsResponse.json();
    renderProjects();
    updateSummary();
    renderMaterials();
    return true;
  } catch (error) {
    rows.innerHTML = '<tr><td colspan="8" class="empty-state">Could not load materials. Check the server and try again.</td></tr>';
    console.error(error);
    return false;
  }
}

function renderProjects(selectedId = "") {
  const choices = projects.map((project) =>
    `<option value="${escapeHtml(project.id)}" ${project.id === selectedId ? "selected" : ""}>${escapeHtml(project.name)} · ${escapeHtml(project.id)}</option>`
  ).join("");
  document.querySelector("#movement-project").innerHTML = `<option value="">General / not assigned</option>${choices}`;
}

function openMaterialModal(material = null) {
  materialForm.reset();
  document.querySelector("#material-form-error").textContent = "";
  document.querySelector("#material-modal-title").textContent = material ? "Edit material" : "Add material";
  document.querySelector("#material-id").value = material?.id || "";
  document.querySelector("#material-name").value = material?.name || "";
  document.querySelector("#material-category").value = material?.category || "Cement";
  document.querySelector("#material-unit").value = material?.unit || "";
  document.querySelector("#material-price").value = material?.purchase_price ?? 0;
  document.querySelector("#material-supplier").value = material?.supplier_name || "";
  document.querySelector("#material-minimum").value = material?.minimum_stock ?? 0;
  materialModal.classList.add("open");
  materialModal.setAttribute("aria-hidden", "false");
  setTimeout(() => document.querySelector("#material-name").focus(), 100);
}

function closeMaterialModal() {
  materialModal.classList.remove("open");
  materialModal.setAttribute("aria-hidden", "true");
}

function updateMovementFields() {
  const isStockIn = document.querySelector("#movement-type").value === "Stock in";
  document.querySelector("#movement-price-field").hidden = !isStockIn;
  document.querySelector("#movement-price").disabled = !isStockIn;
  document.querySelector("#movement-supplier-field").hidden = !isStockIn;
  document.querySelector("#movement-project-field").hidden = isStockIn;
}

function openMovementModal(material, type) {
  movementForm.reset();
  document.querySelector("#movement-form-error").textContent = "";
  document.querySelector("#movement-material-id").value = material.id;
  document.querySelector("#movement-material-name").textContent = `${material.name} · ${material.id}`;
  document.querySelector("#movement-available").textContent = `${formatQuantity(material.quantity)} ${material.unit}`;
  document.querySelector("#movement-type").value = type;
  document.querySelector("#movement-quantity").value = "";
  document.querySelector("#movement-quantity").max = type === "Stock out" ? material.quantity : "";
  document.querySelector("#movement-date").value = localDateValue();
  document.querySelector("#movement-price").value = Number(material.purchase_price || 0).toFixed(2);
  document.querySelector("#movement-supplier").value = material.supplier_name || "";
  document.querySelector("#movement-note").value = "";
  renderProjects();
  updateMovementFields();
  movementModal.classList.add("open");
  movementModal.setAttribute("aria-hidden", "false");
  setTimeout(() => document.querySelector("#movement-quantity").focus(), 100);
}

function closeMovementModal() {
  movementModal.classList.remove("open");
  movementModal.setAttribute("aria-hidden", "true");
}

function openHistory(material) {
  document.querySelector("#history-modal-title").textContent = `${material.name} · Movement history`;
  const historyRows = document.querySelector("#movement-history-rows");
  const movements = [...(material.movements || [])].reverse();
  historyRows.innerHTML = movements.length
    ? movements.map((movement) => {
      const relation = movement.type === "Stock in" ? movement.supplier_name : movement.project_name;
      const movementClass = movement.type === "Stock in" ? "green" : "blue";
      return `<tr>
        <td>${formatDate(movement.date)}</td>
        <td><span class="project-status ${movementClass}">${escapeHtml(movement.type)}</span></td>
        <td>${formatQuantity(movement.quantity)} ${escapeHtml(material.unit)}</td>
        <td>${escapeHtml(relation || "—")}</td>
        <td>${formatCurrency(movement.unit_price)}</td>
        <td class="material-note">${escapeHtml(movement.note || "—")}</td>
      </tr>`;
    }).join("")
    : '<tr><td colspan="6" class="empty-state">No stock movements recorded yet.</td></tr>';
  historyModal.classList.add("open");
  historyModal.setAttribute("aria-hidden", "false");
}

function closeHistory() {
  historyModal.classList.remove("open");
  historyModal.setAttribute("aria-hidden", "true");
}

document.querySelector("#add-material").addEventListener("click", () => openMaterialModal());
document.querySelector("#material-modal-close").addEventListener("click", closeMaterialModal);
document.querySelector("#material-cancel").addEventListener("click", closeMaterialModal);
materialModal.addEventListener("click", (event) => { if (event.target === materialModal) closeMaterialModal(); });
document.querySelector("#movement-modal-close").addEventListener("click", closeMovementModal);
document.querySelector("#movement-cancel").addEventListener("click", closeMovementModal);
movementModal.addEventListener("click", (event) => { if (event.target === movementModal) closeMovementModal(); });
document.querySelector("#movement-type").addEventListener("change", updateMovementFields);
document.querySelector("#history-modal-close").addEventListener("click", closeHistory);
document.querySelector("#history-close").addEventListener("click", closeHistory);
historyModal.addEventListener("click", (event) => { if (event.target === historyModal) closeHistory(); });
document.addEventListener("keydown", (event) => {
  if (event.key === "Escape") {
    closeMaterialModal();
    closeMovementModal();
    closeHistory();
  }
});

materialForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const saveButton = materialForm.querySelector('button[type="submit"]');
  saveButton.disabled = true;
  const id = document.querySelector("#material-id").value;
  const payload = {
    name: document.querySelector("#material-name").value.trim(),
    category: document.querySelector("#material-category").value,
    unit: document.querySelector("#material-unit").value.trim(),
    purchase_price: Number(document.querySelector("#material-price").value),
    supplier_name: document.querySelector("#material-supplier").value.trim(),
    minimum_stock: Number(document.querySelector("#material-minimum").value),
  };
  try {
    const response = await fetch(id ? `/api/materials/${encodeURIComponent(id)}` : "/api/materials", {
      method: id ? "PUT" : "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const result = await response.json();
    if (!response.ok) throw new Error(result.error || "Could not save material");
    closeMaterialModal();
    const refreshed = await loadData();
    showToast(refreshed
      ? (id ? "Material updated." : "Material added.")
      : "Material saved, but the list could not refresh. Reload the page.");
  } catch (error) {
    document.querySelector("#material-form-error").textContent = error.message;
  } finally {
    saveButton.disabled = false;
  }
});

movementForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const saveButton = movementForm.querySelector('button[type="submit"]');
  saveButton.disabled = true;
  const materialId = document.querySelector("#movement-material-id").value;
  const movement = {
    type: document.querySelector("#movement-type").value,
    quantity: Number(document.querySelector("#movement-quantity").value),
    date: document.querySelector("#movement-date").value,
    unit_price: Number(document.querySelector("#movement-price").value),
    supplier_name: document.querySelector("#movement-supplier").value.trim(),
    project_id: document.querySelector("#movement-project").value,
    note: document.querySelector("#movement-note").value.trim(),
  };
  try {
    const response = await fetch(`/api/materials/${encodeURIComponent(materialId)}/movements`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ movement }),
    });
    const result = await response.json();
    if (!response.ok) throw new Error(result.error || "Could not save stock movement");
    closeMovementModal();
    const refreshed = await loadData();
    showToast(refreshed
      ? `${movement.type} recorded. Available: ${formatQuantity(result.quantity)} ${result.unit}.`
      : "Movement saved, but the list could not refresh. Reload the page.");
  } catch (error) {
    document.querySelector("#movement-form-error").textContent = error.message;
  } finally {
    saveButton.disabled = false;
  }
});

rows.addEventListener("click", async (event) => {
  const stockInButton = event.target.closest("[data-stock-in]");
  const stockOutButton = event.target.closest("[data-stock-out]");
  const historyButton = event.target.closest("[data-history]");
  const editButton = event.target.closest("[data-edit]");
  const deleteButton = event.target.closest("[data-delete]");

  if (stockInButton || stockOutButton) {
    const materialId = (stockInButton || stockOutButton).dataset.stockIn || (stockInButton || stockOutButton).dataset.stockOut;
    const material = materials.find((item) => item.id === materialId);
    if (material) openMovementModal(material, stockInButton ? "Stock in" : "Stock out");
    return;
  }
  if (historyButton) {
    const material = materials.find((item) => item.id === historyButton.dataset.history);
    if (material) openHistory(material);
    return;
  }
  if (editButton) {
    const material = materials.find((item) => item.id === editButton.dataset.edit);
    if (material) openMaterialModal(material);
    return;
  }
  if (deleteButton) {
    const material = materials.find((item) => item.id === deleteButton.dataset.delete);
    if (!material || !confirm(`Delete material "${material.name}"?`)) return;
    try {
      const response = await fetch(`/api/materials/${encodeURIComponent(material.id)}`, { method: "DELETE" });
      const result = await response.json();
      if (!response.ok) throw new Error(result.error || "Could not delete material");
      const refreshed = await loadData();
      showToast(refreshed ? "Material deleted." : "Material deleted, but the list could not refresh. Reload the page.");
    } catch (error) {
      showToast(error.message);
    }
  }
});

search.addEventListener("input", renderMaterials);
categoryFilter.addEventListener("change", renderMaterials);
stockFilter.addEventListener("change", renderMaterials);

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
