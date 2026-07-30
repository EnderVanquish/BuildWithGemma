const PLACEHOLDER_OBSERVATIONS = [
  { observation: "Empty porch, no activity", severity: "none",
    reasoning: "No motion detected since the last observation; consistent with an unoccupied entryway." },
  { observation: "Delivery person approached, placed a package, left", severity: "low",
    reasoning: "Brief presence (8s) followed by departure matches typical delivery behavior seen in prior history." },
  { observation: "Unfamiliar person lingered near the door for 3 minutes", severity: "medium",
    reasoning: "Duration is well above the typical 10-20s dwell time seen in the last 10 observations." },
  { observation: "Same person returned a third time in 10 minutes without approaching", severity: "high",
    reasoning: "Repeated returns without approach break the pattern of every prior visitor in history; escalated given the frequency." },
];

const SEVERITY_LEVEL = { none: 0, low: 1, medium: 2, high: 3 };
const SEVERITY_COLOR = {
  none: "var(--text-muted)",
  low: "var(--status-warning)",
  medium: "var(--status-serious)",
  high: "var(--status-critical)",
};

let startTime = Date.now();
let historyCount = 0;
const severityHistory = [];

function formatUptime(ms) {
  const totalSeconds = Math.floor(ms / 1000);
  const h = String(Math.floor(totalSeconds / 3600)).padStart(2, "0");
  const m = String(Math.floor((totalSeconds % 3600) / 60)).padStart(2, "0");
  const s = String(totalSeconds % 60).padStart(2, "0");
  return `${h}:${m}:${s}`;
}

function tick() {
  const ramPct = 40 + Math.random() * 30;
  const cpuPct = 20 + Math.random() * 50;
  document.getElementById("ram-fill").value = ramPct;
  document.getElementById("ram-value").textContent = `${(ramPct / 100 * 6).toFixed(1)} / 6.0 GB`;
  document.getElementById("cpu-fill").value = cpuPct;
  document.getElementById("cpu-value").textContent = `${cpuPct.toFixed(0)} %`;
  document.getElementById("tokens-value").textContent = (8 + Math.random() * 10).toFixed(1);
  document.getElementById("uptime-value").textContent = formatUptime(Date.now() - startTime);
}

function pushObservation() {
  const sample = PLACEHOLDER_OBSERVATIONS[historyCount % PLACEHOLDER_OBSERVATIONS.length];
  historyCount += 1;
  const timestamp = new Date().toLocaleTimeString();

  document.getElementById("latest-observation").textContent = sample.observation;
  document.getElementById("latest-reasoning").textContent = sample.reasoning;
  const severityBadge = document.getElementById("latest-severity");
  severityBadge.dataset.severity = sample.severity;
  severityBadge.textContent = sample.severity === "none" ? "Normal" : sample.severity;
  document.getElementById("frame-timestamp").textContent = timestamp;

  const historyList = document.getElementById("history-list");
  const item = document.createElement("li");
  item.className = "list-row items-center";
  item.innerHTML = `
    <div class="text-sm text-base-content/60 tabular-nums w-20">${timestamp}</div>
    <div class="text-sm flex-1">${sample.observation}</div>
    <span class="badge severity-badge" data-severity="${sample.severity}">
      ${sample.severity === "none" ? "Normal" : sample.severity}
    </span>
  `;
  historyList.prepend(item);
  while (historyList.children.length > 8) {
    historyList.removeChild(historyList.lastChild);
  }

  severityHistory.push(sample.severity);
  while (severityHistory.length > 8) {
    severityHistory.shift();
  }
  renderSparkline();
}

function renderSparkline() {
  const svg = document.getElementById("severity-sparkline");
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

function askQuestion(question) {
  const answerBox = document.getElementById("ask-answer");
  answerBox.classList.remove("hidden");
  answerBox.textContent = "Thinking…";

  setTimeout(() => {
    const recent = severityHistory.slice(-3).join(", ") || "none";
    answerBox.textContent =
      `(placeholder answer — not yet wired to Gemma) Based on the last few observations ` +
      `(severities: ${recent}), nothing matching "${question}" stands out as unusual right now.`;
  }, 900);
}

document.getElementById("ask-form").addEventListener("submit", (e) => {
  e.preventDefault();
  const input = document.getElementById("ask-input");
  if (input.value.trim()) {
    askQuestion(input.value.trim());
  }
});

document.getElementById("frame-preview").src = "placeholder_frame.png";

setInterval(tick, 1000);
setInterval(pushObservation, 4000);
tick();
pushObservation();
