const SEVERITY_LEVEL = { none: 0, low: 1, medium: 2, high: 3 };
const SEVERITY_COLOR = {
  none: "var(--text-muted)",
  low: "var(--status-warning)",
  medium: "var(--status-serious)",
  high: "var(--status-critical)",
};

let severityHistory = [];
let lastFrameId = -1;
// When the user clicks a history row we pin the preview to that row's snapshot.
// Live updates stop overwriting the image until they click "Back to live" — otherwise
// the next sample would yank the frame away mid-inspection.
let pinnedFrameRef = null;
// Full observation record per frame_ref, so clicking a history row can restore the
// reasoning that went with that snapshot — not just the image.
let recordsByRef = new Map();

// Four severity levels collapse to three lights: the dot is meant to be read at a
// glance, and "low vs medium" is a distinction you read the text for.
const SEVERITY_LIGHT = { none: "green", low: "yellow", medium: "yellow", high: "red" };
const SEVERITY_WORD = {
  none: "All clear",
  low: "Worth a look",
  medium: "Suspicious",
  high: "Alert",
};

function formatUptime(seconds) {
  const h = String(Math.floor(seconds / 3600)).padStart(2, "0");
  const m = String(Math.floor((seconds % 3600) / 60)).padStart(2, "0");
  const s = String(seconds % 60).padStart(2, "0");
  return `${h}:${m}:${s}`;
}

function severityLabel(severity) {
  return severity === "none" ? "Normal" : severity;
}

function render(snapshot) {
  const ramPct = snapshot.ram_total_gb
    ? (snapshot.ram_used_gb / snapshot.ram_total_gb) * 100
    : 0;
  document.getElementById("ram-fill").value = ramPct;
  document.getElementById("ram-value").textContent =
    `${snapshot.ram_used_gb.toFixed(1)} / ${snapshot.ram_total_gb.toFixed(1)} GB`;
  document.getElementById("cpu-fill").value = snapshot.cpu_pct;
  document.getElementById("cpu-value").textContent = `${snapshot.cpu_pct.toFixed(0)} %`;
  const coresNote = document.getElementById("cpu-cores");
  if (coresNote) {
    const cores = snapshot.cpu_cores;
    coresNote.textContent = cores
      ? `${Number.isInteger(cores) ? cores : cores.toFixed(1)} cores`
      : "—";
  }
  document.getElementById("tokens-value").textContent =
    snapshot.tokens_per_sec === null ? "--" : snapshot.tokens_per_sec.toFixed(1);
  document.getElementById("uptime-value").textContent = formatUptime(snapshot.uptime_seconds);

  // Surfaces whether the RAM figure is a real container cap (cgroup) or the dev
  // host's memory, so the demo never implies a cap that isn't actually enforced.
  const sourceNote = document.getElementById("stats-source");
  if (sourceNote) {
    sourceNote.textContent = snapshot.stats_source === "cgroup"
      ? "container cap"
      : "host (uncapped dev)";
  }

  // Only refetch the frame when a new one has actually been reasoned about, and
  // never while the user is inspecting a pinned past snapshot.
  if (pinnedFrameRef === null && snapshot.frame_id > 0 && snapshot.frame_id > lastFrameId) {
    lastFrameId = snapshot.frame_id;
    showFrame(snapshot.frame_id);
  }

  const latest = snapshot.latest_observation;
  if (latest) {
    renderStatus(snapshot.history, latest);
    if (pinnedFrameRef === null) {
      document.getElementById("frame-timestamp").textContent = latest.timestamp;
    }
  }

  snapshot.history.forEach((o) => recordsByRef.set(o.frame_ref, o));

  const historyList = document.getElementById("history-list");
  historyList.innerHTML = snapshot.history
    .slice()
    .reverse()
    .map((o) => `
      <li class="list-row items-center history-row cursor-pointer"
          data-frame-ref="${o.frame_ref}" data-timestamp="${o.timestamp}"
          title="Show the frame this verdict was based on">
        <div class="text-sm text-base-content/60 tabular-nums w-24">${o.timestamp}</div>
        <div class="text-sm flex-1">${o.observation}</div>
        <span class="badge severity-badge" data-severity="${o.severity}">
          ${severityLabel(o.severity)}
        </span>
      </li>`)
    .join("");
  markPinnedRow();

  severityHistory = snapshot.history.map((o) => o.severity);
  renderSparkline();
}

function renderStatus(history, latest) {
  // The headline status reflects the whole recent window, not just the newest frame.
  // A "high" three samples ago still means something is wrong at this camera — letting
  // one quiet frame reset the light back to green is exactly how a real incident gets
  // missed. The worst severity in the window drives the light; the newest observation
  // still supplies the summary line so the text stays current.
  const worst = history.reduce(
    (acc, o) => (SEVERITY_LEVEL[o.severity] > SEVERITY_LEVEL[acc] ? o.severity : acc),
    "none",
  );
  const flagged = history.filter((o) => o.severity !== "none").length;

  document.getElementById("status-light").dataset.level = SEVERITY_LIGHT[worst];
  document.getElementById("status-word").textContent = SEVERITY_WORD[worst];
  document.getElementById("status-time").textContent = latest.timestamp;

  const summary = document.getElementById("status-summary");
  const context = flagged === 0
    ? `Nothing flagged in the last ${history.length} observation${history.length === 1 ? "" : "s"}.`
    : `${flagged} of the last ${history.length} observations flagged` +
      (worst !== latest.severity ? `, peaking at ${severityLabel(worst)}.` : ".");
  summary.textContent = `${latest.observation} ${context}`;
}

function showFrame(frameRef) {
  const img = document.getElementById("frame-preview");
  img.src = `/api/frame/${frameRef}`;
  img.classList.remove("hidden");
  document.getElementById("frame-empty").classList.add("hidden");
}

function markPinnedRow() {
  document.querySelectorAll("#history-list .history-row").forEach((row) => {
    row.classList.toggle(
      "history-row-active",
      pinnedFrameRef !== null && Number(row.dataset.frameRef) === pinnedFrameRef,
    );
  });
}

function renderSelected(record) {
  const body = document.getElementById("selected-body");
  const empty = document.getElementById("selected-empty");
  if (!record) {
    body.classList.add("hidden");
    body.classList.remove("flex");
    empty.classList.remove("hidden");
    document.getElementById("selected-time").textContent = "";
    return;
  }
  empty.classList.add("hidden");
  body.classList.remove("hidden");
  body.classList.add("flex");
  document.getElementById("selected-time").textContent = record.timestamp;
  document.getElementById("selected-light").dataset.level = SEVERITY_LIGHT[record.severity];
  const badge = document.getElementById("selected-severity");
  badge.dataset.severity = record.severity;
  badge.textContent = severityLabel(record.severity);
  document.getElementById("selected-observation").textContent = record.observation;
  document.getElementById("selected-reasoning").textContent = record.reasoning;
}

function pinFrame(frameRef, timestamp) {
  pinnedFrameRef = frameRef;
  showFrame(frameRef);
  document.getElementById("frame-timestamp").textContent = `${timestamp} (past snapshot)`;
  document.getElementById("frame-live-btn").classList.remove("hidden");
  renderSelected(recordsByRef.get(frameRef));
  markPinnedRow();
}

function unpinFrame() {
  pinnedFrameRef = null;
  document.getElementById("frame-live-btn").classList.add("hidden");
  // Force the next snapshot to repaint the live frame even if frame_id hasn't moved.
  lastFrameId = -1;
  renderSelected(null);
  markPinnedRow();
}

document.getElementById("history-list").addEventListener("click", (e) => {
  const row = e.target.closest(".history-row");
  if (!row) return;
  const frameRef = Number(row.dataset.frameRef);
  // Clicking the already-pinned row toggles back to live.
  if (frameRef === pinnedFrameRef) {
    unpinFrame();
  } else if (frameRef > 0) {
    pinFrame(frameRef, row.dataset.timestamp);
  }
});

document.getElementById("frame-live-btn").addEventListener("click", unpinFrame);

function renderSparkline() {
  const svg = document.getElementById("severity-sparkline");
  if (severityHistory.length === 0) {
    svg.innerHTML = "";
    return;
  }
  const points = severityHistory.length > 1 ? severityHistory : [...severityHistory, ...severityHistory];
  const stepX = 380 / (points.length - 1 || 1);
  const y = (severity) => 50 - (SEVERITY_LEVEL[severity] / 3) * 40;
  const coords = points.map((s, i) => [10 + i * stepX, y(s)]);

  const baseline = `<line x1="10" y1="50" x2="390" y2="50" stroke="var(--gridline, #e1e0d9)" stroke-width="1"/>`;
  const line = `<polyline points="${coords.map(([x, yy]) => `${x},${yy}`).join(" ")}"
    fill="none" stroke="var(--text-secondary, #52514e)" stroke-width="2"/>`;
  const dots = coords
    .map(([x, yy], i) => `<circle cx="${x}" cy="${yy}" r="4" fill="${SEVERITY_COLOR[points[i]]}"><title>${points[i]}</title></circle>`)
    .join("");

  svg.innerHTML = baseline + line + dots;
}

async function askQuestion(question) {
  const answerBox = document.getElementById("ask-answer");
  const button = document.getElementById("ask-button");
  const input = document.getElementById("ask-input");

  answerBox.classList.remove("hidden");
  answerBox.innerHTML = `<span class="loading loading-dots loading-sm align-middle"></span>
    <span class="ml-2 text-base-content/60">Reasoning over the log&hellip;</span>`;
  button.disabled = true;
  input.disabled = true;

  try {
    const res = await fetch("/api/ask", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || `HTTP ${res.status}`);
    answerBox.textContent = data.answer;
  } catch (err) {
    answerBox.innerHTML = `<span class="text-error">Couldn't answer: ${err.message}</span>`;
  } finally {
    button.disabled = false;
    input.disabled = false;
  }
}

document.getElementById("ask-form").addEventListener("submit", (e) => {
  e.preventDefault();
  const input = document.getElementById("ask-input");
  if (input.value.trim()) {
    askQuestion(input.value.trim());
  }
});

function setSync(synced) {
  const dot = document.getElementById("sync-dot");
  dot.dataset.status = synced ? "synced" : "stale";
  dot.title = synced
    ? "Live — receiving updates from the reasoning loop"
    : "Not synced — no updates from the backend";
}

// A dropped SSE connection fires onerror, but a backend that hangs without closing
// the socket does not — so treat "no tick for a while" as unsynced too. Ticks are 1Hz.
const SYNC_TIMEOUT_MS = 5000;
let syncTimer = null;

function noteTick() {
  setSync(true);
  clearTimeout(syncTimer);
  syncTimer = setTimeout(() => setSync(false), SYNC_TIMEOUT_MS);
}

const events = new EventSource("/api/stream");
events.onmessage = (e) => {
  noteTick();
  render(JSON.parse(e.data));
};
events.onerror = () => setSync(false);
