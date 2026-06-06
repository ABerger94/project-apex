const stateUrl = "/api/state";
const runUrl = "/api/run";
const scheduleUrl = "/api/schedule";

const els = {
  currentLevel: document.querySelector("#currentLevel"),
  l3Score: document.querySelector("#l3Score"),
  l4Score: document.querySelector("#l4Score"),
  l5Score: document.querySelector("#l5Score"),
  generatedAt: document.querySelector("#generatedAt"),
  runsList: document.querySelector("#runsList"),
  commitsList: document.querySelector("#commitsList"),
  proposalsList: document.querySelector("#proposalsList"),
  hypothesis: document.querySelector("#hypothesis"),
  gitStatus: document.querySelector("#gitStatus"),
  refreshBtn: document.querySelector("#refreshBtn"),
  runBtn: document.querySelector("#runBtn"),
  intervalValue: document.querySelector("#intervalValue"),
  intervalUnit: document.querySelector("#intervalUnit"),
  startIntervalBtn: document.querySelector("#startIntervalBtn"),
  startContinuousBtn: document.querySelector("#startContinuousBtn"),
  stopScheduleBtn: document.querySelector("#stopScheduleBtn"),
  scheduleStatus: document.querySelector("#scheduleStatus"),
  nextRun: document.querySelector("#nextRun"),
  lastRun: document.querySelector("#lastRun"),
  consolePanel: document.querySelector("#consolePanel"),
  runOutput: document.querySelector("#runOutput"),
  runState: document.querySelector("#runState"),
};

function pct(value) {
  if (typeof value !== "number") return "--";
  return `${Math.round(value * 100)}%`;
}

function time(value) {
  if (!value) return "";
  return new Intl.DateTimeFormat(undefined, {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  }).format(new Date(value));
}

function escapeHtml(value) {
  return String(value || "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

function renderMetrics(latest) {
  const scores = latest?.scores || {};
  els.currentLevel.textContent = latest?.current_level || "--";
  els.l3Score.textContent = pct(scores.l3_agent);
  els.l4Score.textContent = pct(scores.l4_innovator);
  els.l5Score.textContent = pct(scores.l5_organizer);
}

function renderRuns(events) {
  if (!events.length) {
    els.runsList.innerHTML = `<p class="empty">No runs recorded yet.</p>`;
    return;
  }
  els.runsList.innerHTML = events
    .map((event) => {
      const scores = event.scores || {};
      const accepted = event.accepted ? "Accepted" : "Rejected";
      return `
        <article class="run-card">
          <div class="run-top">
            <div>
              <strong>Cycle ${escapeHtml(event.cycle)}</strong>
              <p class="muted">${time(event.timestamp)} | ${escapeHtml(event.current_level || "Unknown")}</p>
            </div>
            <span class="badge ${event.accepted ? "ok" : "fail"}">${accepted}</span>
          </div>
          <p class="gap">${escapeHtml(event.gap)}</p>
          <div class="score-row">
            <div class="score-pill">L3<strong>${pct(scores.l3_agent)}</strong></div>
            <div class="score-pill">L4<strong>${pct(scores.l4_innovator)}</strong></div>
            <div class="score-pill">L5<strong>${pct(scores.l5_organizer)}</strong></div>
          </div>
          <p class="muted">${event.commit_hash ? `Commit <span class="hash">${escapeHtml(event.commit_hash)}</span>` : "No commit"}</p>
        </article>
      `;
    })
    .join("");
}

function renderHypothesis(latest) {
  const hypothesis = latest?.hypothesis;
  if (!hypothesis) {
    els.hypothesis.innerHTML = `<p class="empty">No hypothesis yet.</p>`;
    return;
  }
  els.hypothesis.innerHTML = `
    <h3>${escapeHtml(hypothesis.title)}</h3>
    <p>${escapeHtml(hypothesis.rationale)}</p>
    <p><strong>Target:</strong> ${escapeHtml(hypothesis.target_signal)} | <strong>Expected:</strong> ${pct(hypothesis.expected_delta)}</p>
    <p class="muted">${escapeHtml(latest.proposal_path || "")}</p>
  `;
}

function renderCommits(commits) {
  if (!commits.length) {
    els.commitsList.innerHTML = `<p class="empty">No commits found.</p>`;
    return;
  }
  els.commitsList.innerHTML = commits
    .map((commit) => `
      <div class="commit">
        <span>${escapeHtml(commit.message)}</span>
        <span class="hash">${escapeHtml(commit.hash)}</span>
      </div>
    `)
    .join("");
}

function renderProposals(proposals) {
  if (!proposals.length) {
    els.proposalsList.innerHTML = `<p class="empty">No proposals yet.</p>`;
    return;
  }
  els.proposalsList.innerHTML = proposals
    .map((proposal) => `
      <article class="proposal">
        <strong>${escapeHtml(proposal.name)}</strong>
        <p class="muted">${time(proposal.modified)} | ${escapeHtml(proposal.path)}</p>
        <pre>${escapeHtml(proposal.preview)}</pre>
      </article>
    `)
    .join("");
}

function renderStatus(status) {
  els.gitStatus.textContent = status.length ? status.join("\n") : "Clean";
}

function renderScheduler(scheduler) {
  const active = scheduler?.enabled;
  const running = scheduler?.running;
  const mode = scheduler?.mode || "stopped";
  const label = running ? "Running" : active ? (mode === "continuous" ? "Continuous" : "Interval") : "Stopped";
  els.scheduleStatus.textContent = label;
  els.scheduleStatus.className = `muted schedule-state ${active ? "active" : ""}`;
  els.nextRun.textContent = `Next run: ${scheduler?.nextRunAt ? time(scheduler.nextRunAt) : "--"}`;
  els.lastRun.textContent = `Last run: ${scheduler?.lastFinishedAt ? time(scheduler.lastFinishedAt) : "--"}`;
  els.startIntervalBtn.disabled = running;
  els.startContinuousBtn.disabled = running;
  els.stopScheduleBtn.disabled = !active;
}

function render(data) {
  renderMetrics(data.latest);
  renderRuns(data.events || []);
  renderHypothesis(data.latest);
  renderCommits(data.commits || []);
  renderProposals(data.proposals || []);
  renderStatus(data.status || []);
  renderScheduler(data.scheduler || {});
  els.generatedAt.textContent = `Updated ${time(data.generatedAt)}`;
}

async function refresh() {
  const response = await fetch(stateUrl);
  render(await response.json());
}

async function runCycle() {
  els.runBtn.disabled = true;
  els.consolePanel.hidden = false;
  els.runState.textContent = "Running";
  els.runOutput.textContent = "";
  try {
    const response = await fetch(runUrl, { method: "POST" });
    const data = await response.json();
    els.runState.textContent = data.ok ? "Complete" : "Failed";
    els.runOutput.textContent = [data.command, data.stdout, data.stderr].filter(Boolean).join("\n\n");
    render(data.state);
  } catch (error) {
    els.runState.textContent = "Failed";
    els.runOutput.textContent = error.message;
  } finally {
    els.runBtn.disabled = false;
  }
}

function intervalMsFromControls() {
  const value = Math.max(1, Number(els.intervalValue.value) || 1);
  const multiplier = els.intervalUnit.value === "minutes" ? 60 * 1000 : 60 * 60 * 1000;
  return value * multiplier;
}

async function updateSchedule(payload) {
  els.consolePanel.hidden = false;
  els.runState.textContent = "Updating schedule";
  const response = await fetch(scheduleUrl, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  const data = await response.json();
  if (data.state) render(data.state);
  els.runState.textContent = data.ok ? "Schedule updated" : "Schedule failed";
  els.runOutput.textContent = JSON.stringify(data.scheduler || data, null, 2);
}

els.refreshBtn.addEventListener("click", refresh);
els.runBtn.addEventListener("click", runCycle);
els.startIntervalBtn.addEventListener("click", () => {
  updateSchedule({ action: "start", mode: "interval", intervalMs: intervalMsFromControls() });
});
els.startContinuousBtn.addEventListener("click", () => {
  updateSchedule({ action: "start", mode: "continuous" });
});
els.stopScheduleBtn.addEventListener("click", () => {
  updateSchedule({ action: "stop" });
});
refresh();
setInterval(refresh, 15000);
