const $ = (id) => document.getElementById(id);
let currentPage = 1;
let selectedId = null;

async function api(path, options = {}) {
  const response = await fetch(path, options);
  if (!response.ok) {
    const body = await response.json();
    throw new Error(typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail));
  }
  return response.status === 204 ? null : response.json();
}

function jsonOptions(method, data) {
  return { method, headers: { "Content-Type": "application/json" }, body: JSON.stringify(data) };
}

async function action(task) {
  document.querySelectorAll("button").forEach((button) => { button.disabled = true; });
  $("message").textContent = "Working...";
  $("message").className = "";
  try {
    await task();
    $("message").textContent = "MongoDB operation completed successfully.";
  } catch (error) {
    $("message").textContent = error.message;
    $("message").className = "error";
  } finally {
    document.querySelectorAll("button").forEach((button) => { button.disabled = false; });
    updatePagination();
  }
}

let total = 0;
function updatePagination() {
  $("previous").disabled = currentPage <= 1;
  $("next").disabled = currentPage * 20 >= total;
  $("page").textContent = `Page ${currentPage} | ${total} saved reports`;
}

async function refresh() {
  let health;
  try {
    health = await api("/api/health");
  } catch (error) {
    $("connection").textContent = "MongoDB disconnected";
    ["database", "collection", "count"].forEach((id) => { $(id).textContent = "-"; });
    $("reports").textContent = "Database unavailable. Previously loaded data is not shown.";
    $("detail").hidden = true;
    selectedId = null;
    throw error;
  }
  $("connection").textContent = "MongoDB connected";
  $("database").textContent = health.database;
  $("collection").textContent = health.collection;
  $("count").textContent = health.document_count;
  let data = await api(`/api/reports?page=${currentPage}`);
  total = data.total;
  if (!data.items.length && currentPage > 1) {
    currentPage = Math.max(1, Math.ceil(total / 20));
    data = await api(`/api/reports?page=${currentPage}`);
  }
  $("reports").replaceChildren();
  if (!data.items.length) $("reports").textContent = "No reports yet. Analyze the sample plans to create your first MongoDB documents.";
  for (const report of data.items) {
    const card = document.createElement("article");
    card.className = "report";
    const heading = document.createElement("h3");
    heading.textContent = report.project_name;
    const badge = document.createElement("span");
    badge.className = `badge ${report.rag.toLowerCase()}`;
    badge.textContent = report.rag;
    const metadata = document.createElement("p");
    metadata.textContent = `${report.project_manager} | As of ${report.as_of} | ${report.metrics.total_tasks} tasks`;
    const id = document.createElement("code");
    id.textContent = `ObjectId: ${report._id}`;
    const view = document.createElement("button");
    view.textContent = "View document";
    view.onclick = () => action(() => showReport(report._id));
    const remove = document.createElement("button");
    remove.textContent = "Delete";
    remove.className = "danger";
    remove.onclick = () => {
      if (!confirm(`Permanently delete the saved report for ${report.project_name}?`)) return;
      action(async () => {
        await api(`/api/reports/${report._id}`, { method: "DELETE" });
        if (selectedId === report._id) {
          selectedId = null;
          $("detail").hidden = true;
        }
        await refresh();
      });
    };
    card.append(heading, badge, metadata, id, view, remove);
    $("reports").append(card);
  }
  updatePagination();
  if (selectedId) await showReport(selectedId);
}

async function showReport(id) {
  const report = await api(`/api/reports/${id}`);
  selectedId = id;
  $("detail").hidden = false;
  $("detail-title").textContent = report.project_name;
  $("reason").textContent = report.reason;
  $("notes").value = report.notes;
  $("document").textContent = JSON.stringify(report, null, 2);
  $("recommendations").replaceChildren(...report.recommendations.map((text) => {
    const item = document.createElement("li");
    item.textContent = text;
    return item;
  }));
}

function analysisDate() {
  if (!$("as-of").value) throw new Error("Choose an analysis date.");
  return $("as-of").value;
}

$("refresh").onclick = () => action(refresh);
$("samples").onclick = () => action(async () => {
  await api("/api/reports/samples", jsonOptions("POST", { as_of: analysisDate() }));
  currentPage = 1;
  await refresh();
});
$("upload-form").onsubmit = (event) => {
  event.preventDefault();
  action(async () => {
    const file = $("file").files[0];
    if (!file || file.size > 10 * 1024 * 1024) throw new Error("Select an .xlsx file smaller than 10 MB.");
    const data = new FormData();
    data.append("file", file);
    data.append("as_of", analysisDate());
    const report = await api("/api/reports/upload", { method: "POST", body: data });
    currentPage = 1;
    await refresh();
    await showReport(report._id);
  });
};
$("notes-form").onsubmit = (event) => {
  event.preventDefault();
  action(async () => {
    await api(`/api/reports/${selectedId}`, jsonOptions("PATCH", { notes: $("notes").value }));
    await showReport(selectedId);
  });
};
$("previous").onclick = () => action(async () => { currentPage -= 1; await refresh(); });
$("next").onclick = () => action(async () => { currentPage += 1; await refresh(); });
action(refresh);
