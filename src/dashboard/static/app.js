const SEVERITY_LEVEL = { none: 0, low: 1, medium: 2, high: 3 };
const SEVERITY_COLOR = {
  none: "var(--text-muted)",
  low: "var(--status-warning)",
  medium: "var(--status-serious)",
  high: "var(--status-critical)",
};

let severityHistory = [];
let lastFrameId = -1;

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

  // Only refetch the frame when a new one has actually been reasoned about.
  if (snapshot.frame_id > 0 && snapshot.frame_id > lastFrameId) {
    lastFrameId = snapshot.frame_id;
    const img = document.getElementById("frame-preview");
    img.src = `/api/frame?v=${snapshot.frame_id}`;
    img.classList.remove("hidden");
    document.getElementById("frame-empty").classList.add("hidden");
  }

  const latest = snapshot.latest_observation;
  if (latest) {
    document.getElementById("latest-observation").textContent = latest.observation;
    document.getElementById("latest-reasoning").textContent = latest.reasoning;
    const badge = document.getElementById("latest-severity");
    badge.dataset.severity = latest.severity;
    badge.textContent = severityLabel(latest.severity);
    document.getElementById("frame-timestamp").textContent = latest.timestamp;
  }

  const historyList = document.getElementById("history-list");
  historyList.innerHTML = snapshot.history
    .slice()
    .reverse()
    .map((o) => `
      <li class="list-row items-center history-row">
        <div class="text-sm text-base-content/60 tabular-nums w-24">${o.timestamp}</div>
        <div class="text-sm flex-1">${o.observation}</div>
        <span class="badge severity-badge" data-severity="${o.severity}">
          ${severityLabel(o.severity)}
        </span>
      </li>`)
    .join("");

  severityHistory = snapshot.history.map((o) => o.severity);
  renderSparkline();
}

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

const events = new EventSource("/api/stream");
events.onmessage = (e) => render(JSON.parse(e.data));
events.onerror = () => {
  const badge = document.getElementById("network-badge");
  badge.dataset.status = "critical";
  document.getElementById("network-label").textContent = "BACKEND DISCONNECTED";
};
