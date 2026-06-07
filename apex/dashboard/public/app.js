const stateUrl = "/api/state";

const els = {
  refreshBtn: document.querySelector("#refreshBtn"),
  targetLevel: document.querySelector("#targetLevel"),
  branch: document.querySelector("#branch"),
  trackedFiles: document.querySelector("#trackedFiles"),
  workingTree: document.querySelector("#workingTree"),
  stateSource: document.querySelector("#stateSource"),
  objectiveText: document.querySelector("#objectiveText"),
  levelList: document.querySelector("#levelList"),
  cycleCount: document.querySelector("#cycleCount"),
  cycles: document.querySelector("#cycles"),
  events: document.querySelector("#events"),
  commits: document.querySelector("#commits"),
  status: document.querySelector("#status"),
};

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

function fmtTime(value) {
  if (!value) return "--";
  return new Intl.DateTimeFormat(undefined, {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
    second: "2-digit",
  }).format(new Date(value));
}

function renderObjective(objective) {
  els.targetLevel.textContent = `L${objective.target_level}`;
  els.objectiveText.textContent = objective.target_objective;
  els.levelList.innerHTML = objective.levels.map((level) => `
    <article class="level ${level.level === objective.target_level ? "target" : ""}">
      <span>L${escapeHtml(level.level)}</span>
      <div>
        <strong>${escapeHtml(level.name)}</strong>
        <p>${escapeHtml(level.description)}</p>
      </div>
    </article>
  `).join("");
}

function renderRepo(repo, generatedFrom) {
  els.branch.textContent = repo.branch || "--";
  els.trackedFiles.textContent = repo.tracked_file_count;
  els.workingTree.textContent = repo.status.length ? `${repo.status.length} item(s)` : "clean";
  els.stateSource.textContent = generatedFrom || "";
  els.status.textContent = repo.status.length ? repo.status.join("\n") : "Clean";
  els.commits.innerHTML = repo.recent_commits.length
    ? repo.recent_commits.map((commit) => `<div class="commit">${escapeHtml(commit)}</div>`).join("")
    : `<p class="empty">No commits yet.</p>`;
}

function renderCycles(cycles) {
  els.cycleCount.textContent = `${cycles.length} recorded`;
  if (!cycles.length) {
    els.cycles.innerHTML = `<p class="empty">No manual cycles recorded yet. Run a strict JSON plan to populate this panel.</p>`;
    return;
  }
  els.cycles.innerHTML = cycles.map((cycle) => {
    const changed = cycle.changed_paths || [];
    return `
      <article class="cycle ${cycle.accepted ? "accepted" : "rejected"}">
        <div class="cycle-top">
          <div>
            <strong>${escapeHtml(cycle.title)}</strong>
            <p class="muted">${fmtTime(cycle.finished_at)} | ${escapeHtml(cycle.reason || "unknown")}</p>
          </div>
          <span class="badge">${cycle.accepted ? "Accepted" : "Rejected"}</span>
        </div>
        <p>${cycle.commit_hash ? `Commit <span class="hash">${escapeHtml(cycle.commit_hash)}</span>` : "No commit"}</p>
        <div class="changed-files">
          ${changed.length ? changed.map((path) => `<span>${escapeHtml(path)}</span>`).join("") : `<span>No changed paths recorded</span>`}
        </div>
      </article>
    `;
  }).join("");
}

function renderEvents(events) {
  if (!events.length) {
    els.events.innerHTML = `<p class="empty">No events recorded yet.</p>`;
    return;
  }
  els.events.innerHTML = events.slice().reverse().map((event) => `
    <article class="event">
      <div>
        <strong>${escapeHtml(event.event_type)}</strong>
        <span class="muted">${fmtTime(event.timestamp)}</span>
      </div>
      <pre>${escapeHtml(JSON.stringify(event.data, null, 2))}</pre>
    </article>
  `).join("");
}

async function refresh() {
  const response = await fetch(stateUrl);
  const data = await response.json();
  renderObjective(data.objective);
  renderRepo(data.repo, data.generated_from);
  renderCycles(data.cycles || []);
  renderEvents(data.events || []);
}

els.refreshBtn.addEventListener("click", refresh);
refresh();
setInterval(refresh, 15000);

