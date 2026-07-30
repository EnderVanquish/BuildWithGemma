const routinesEl = document.getElementById("routines");
const emptyEl = document.getElementById("routines-empty");
const statusEl = document.getElementById("save-status");

function addRoutineRow(routine = {}) {
  const node = document.getElementById("routine-template").content.cloneNode(true);
  const row = node.querySelector(".routine-row");
  row.querySelectorAll("[data-field]").forEach((input) => {
    input.value = routine[input.dataset.field] || "";
  });
  row.querySelector("[data-action='remove']").addEventListener("click", () => {
    row.remove();
    updateEmptyState();
  });
  routinesEl.appendChild(node);
  updateEmptyState();
}

function updateEmptyState() {
  emptyEl.classList.toggle("hidden", routinesEl.children.length > 0);
}

function collectRoutines() {
  // Rows with no label are dropped rather than saved: the backend rejects them, and a
  // blank row is much more likely to be a half-finished edit than a real routine.
  return [...routinesEl.querySelectorAll(".routine-row")]
    .map((row) => {
      const routine = {};
      row.querySelectorAll("[data-field]").forEach((input) => {
        const value = input.value.trim();
        if (value) routine[input.dataset.field] = value;
      });
      return routine;
    })
    .filter((r) => r.label);
}

function setStatus(message, kind) {
  statusEl.textContent = message;
  statusEl.className = `text-sm ${kind === "error" ? "text-error" : "text-success"}`;
  if (kind !== "error") {
    setTimeout(() => { statusEl.textContent = ""; }, 4000);
  }
}

async function load() {
  try {
    const res = await fetch("/api/config");
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || `HTTP ${res.status}`);
    document.getElementById("site-context").value = data.site_context || "";
    document.getElementById("scene-time").value = data.scene_time || "";
    routinesEl.innerHTML = "";
    (data.routines || []).forEach(addRoutineRow);
    updateEmptyState();
  } catch (err) {
    setStatus(`Couldn't load config: ${err.message}`, "error");
  }
}

async function save() {
  const button = document.getElementById("save");
  button.disabled = true;
  try {
    const res = await fetch("/api/config", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        site_context: document.getElementById("site-context").value,
        routines: collectRoutines(),
        scene_time: document.getElementById("scene-time").value,
      }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || `HTTP ${res.status}`);
    setStatus("Saved — applies from the next observation.", "ok");
  } catch (err) {
    setStatus(`Couldn't save: ${err.message}`, "error");
  } finally {
    button.disabled = false;
  }
}

document.getElementById("add-routine").addEventListener("click", () => addRoutineRow());
document.getElementById("save").addEventListener("click", save);
document.getElementById("reload").addEventListener("click", load);

load();
