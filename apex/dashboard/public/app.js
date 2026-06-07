const stateUrl = "/api/state";
const phases = [
  ["context-intake", "Context intake"],
  ["self-read", "Self-read"],
  ["plan-proposal", "Plan proposal"],
  ["human-review", "Human review"],
  ["execute", "Execute"],
  ["test", "Test"],
  ["commit-or-rollback", "Commit / rollback"],
];

const els = {
  refreshBtn: document.querySelector("#refreshBtn"),
  suggestGoalsBtn: document.querySelector("#suggestGoalsBtn"),
  generatePlanBtn: document.querySelector("#generatePlanBtn"),
  dryRunPlanBtn: document.querySelector("#dryRunPlanBtn"),
  runPlanBtn: document.querySelector("#runPlanBtn"),
  clearPlanBtn: document.querySelector("#clearPlanBtn"),
  goalInput: document.querySelector("#goalInput"),
  commandMessage: document.querySelector("#commandMessage"),
  phaseLabel: document.querySelector("#phaseLabel"),
  pendingPlan: document.querySelector("#pendingPlan"),
  targetLevel: document.querySelector("#targetLevel"),
  branch: document.querySelector("#branch"),
  trackedFiles: document.querySelector("#trackedFiles"),
  workingTree: document.querySelector("#workingTree"),
  plannerModel: document.querySelector("#plannerModel"),
  plannerDetails: document.querySelector("#plannerDetails"),
  suggestedGoals: document.querySelector("#suggestedGoals"),
  stateSource: document.querySelector("#stateSource"),
  objectiveText: document.querySelector("#objectiveText"),
  levelList: document.querySelector("#levelList"),
  cycleCount: document.querySelector("#cycleCount"),
  cycles: document.querySelector("#cycles"),
  events: document.querySelector("#events"),
  commits: document.querySelector("#commits"),
  status: document.querySelector("#status"),
};

let activePhase = null;
let pendingPlan = null;

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

function renderPlanner(planner) {
  if (!planner) {
    els.plannerModel.textContent = "--";
    els.plannerDetails.innerHTML = "";
    return;
  }
  els.plannerModel.textContent = planner.resolved_model || planner.configured_model || "--";
  const available = planner.available_models?.length ? planner.available_models.join(", ") : "not listed";
  els.plannerDetails.innerHTML = `
    <div><dt>Endpoint</dt><dd>${escapeHtml(planner.endpoint || "--")}</dd></div>
    <div><dt>Configured</dt><dd>${escapeHtml(planner.configured_model || "--")}</dd></div>
    <div><dt>Resolved</dt><dd>${escapeHtml(planner.resolved_model || "--")}</dd></div>
    <div><dt>Timeout</dt><dd>${escapeHtml(planner.timeout_seconds || "--")}s</dd></div>
    <div><dt>Local Models</dt><dd>${escapeHtml(available)}</dd></div>
  `;
}

function setActivePhase(phase) {
  activePhase = phase;
  document.querySelectorAll(".phase-node").forEach((node) => {
    node.classList.toggle("active", node.dataset.phase === phase);
    node.classList.toggle("complete", phase && phaseIndex(node.dataset.phase) < phaseIndex(phase));
  });
  const found = phases.find(([key]) => key === phase);
  els.phaseLabel.textContent = found ? found[1] : "Idle";
}

function phaseIndex(phase) {
  return phases.findIndex(([key]) => key === phase);
}

function setBusy(isBusy) {
  els.suggestGoalsBtn.disabled = isBusy;
  els.generatePlanBtn.disabled = isBusy;
  els.dryRunPlanBtn.disabled = isBusy || !pendingPlan;
  els.runPlanBtn.disabled = isBusy || !pendingPlan;
  els.clearPlanBtn.disabled = isBusy || !pendingPlan;
}

function renderSuggestedGoals(goalState) {
  if (!goalState || goalState.error) {
    els.suggestedGoals.innerHTML = "";
    return;
  }
  const goals = goalState.goals || [];
  if (!goals.length) {
    els.suggestedGoals.innerHTML = "";
    return;
  }
  if (!els.goalInput.value.trim()) {
    els.goalInput.value = goals[0].goal;
  }
  els.suggestedGoals.innerHTML = `
    <div class="suggestion-head">
      <strong>Suggested Goals</strong>
      <span class="muted">Top option prefilled</span>
    </div>
    ${goals.map((goal) => `
      <button class="goal-suggestion" type="button" data-goal="${escapeHtml(goal.goal)}">
        <span>${escapeHtml(goal.priority || "")}</span>
        <div>
          <strong>${escapeHtml(goal.goal)}</strong>
          <p>${escapeHtml(goal.rationale)}</p>
        </div>
      </button>
    `).join("")}
  `;
  els.suggestedGoals.querySelectorAll(".goal-suggestion").forEach((button) => {
    button.addEventListener("click", () => {
      els.goalInput.value = button.dataset.goal || "";
      els.commandMessage.textContent = "Suggested goal loaded. Generate a plan when ready.";
    });
  });
}

function renderPendingPlan(planState) {
  pendingPlan = planState;
  els.dryRunPlanBtn.disabled = !pendingPlan;
  els.runPlanBtn.disabled = !pendingPlan;
  els.clearPlanBtn.disabled = !pendingPlan;
  if (!pendingPlan) {
    els.pendingPlan.innerHTML = `<p class="empty">No generated plan is waiting for approval.</p>`;
    return;
  }
  if (pendingPlan.error) {
    els.pendingPlan.innerHTML = `<p class="error">${escapeHtml(pendingPlan.error)}</p>`;
    return;
  }
  const plan = pendingPlan.plan || {};
  const operations = plan.operations || [];
  const preview = pendingPlan.preview || {};
  const previewFiles = preview.files || [];
  const previewErrors = preview.errors || [];
  els.pendingPlan.innerHTML = `
    <article>
      <div class="pending-head">
        <div>
          <strong>${escapeHtml(plan.title || "Untitled plan")}</strong>
          <p class="muted">${escapeHtml(pendingPlan.goal || "")}</p>
        </div>
        <span class="badge">Pending Approval</span>
      </div>
      <p>${escapeHtml(plan.rationale || "")}</p>
      <div class="changed-files">
        ${operations.length ? operations.map((operation) => `<span>${escapeHtml(operation.kind)}: ${escapeHtml(operation.path)}</span>`).join("") : `<span>No operations</span>`}
      </div>
      <div class="diff-preview">
        <strong>Diff Preview</strong>
        ${previewFiles.length ? previewFiles.map((file) => `
          <section>
            <span>${escapeHtml(file.path)}</span>
            <pre>${escapeHtml(file.diff || "No textual diff.")}</pre>
          </section>
        `).join("") : `<p class="empty">No preview available.</p>`}
        ${previewErrors.length ? previewErrors.map((item) => `<p class="error">${escapeHtml(item.path || "preview")}: ${escapeHtml(item.error)}</p>`).join("") : ""}
      </div>
      <pre>${escapeHtml(JSON.stringify(plan, null, 2))}</pre>
    </article>
  `;
}

function renderCycles(cycles) {
  els.cycleCount.textContent = `${cycles.length} recorded`;
  if (!cycles.length) {
    els.cycles.innerHTML = `<p class="empty">No manual cycles recorded yet. Run a strict JSON plan to populate this panel.</p>`;
    return;
  }
  els.cycles.innerHTML = cycles.map((cycle) => {
    const changed = cycle.changed_paths || [];
    const diffSummary = cycle.diff_summary || [];
    const preflight = cycle.preflight || {};
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
        <p class="muted">Preflight: ${escapeHtml(preflight.reason || "not recorded")}</p>
        ${diffSummary.length ? `<pre>${escapeHtml(diffSummary.join("\n"))}</pre>` : ""}
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
  renderPlanner(data.planner);
  renderSuggestedGoals(data.suggested_goals);
  renderPendingPlan(data.pending_plan);
  renderCycles(data.cycles || []);
  renderEvents(data.events || []);
  if (data.pending_plan && !activePhase) {
    setActivePhase("human-review");
  }
}

async function suggestGoals() {
  setBusy(true);
  els.commandMessage.textContent = "Reading memory and proposing next goals...";
  setActivePhase("context-intake");
  window.setTimeout(() => setActivePhase("self-read"), 350);
  try {
    const data = await postJson("/api/suggest-goals");
    renderSuggestedGoals(data.suggested_goals);
    renderRepo(data.state.repo, data.state.generated_from);
    renderPlanner(data.state.planner);
    renderEvents(data.state.events || []);
    setActivePhase("plan-proposal");
    els.commandMessage.textContent = "Goal suggestions generated. Top goal is prefilled.";
  } catch (error) {
    els.commandMessage.textContent = error.message;
    setActivePhase(null);
  } finally {
    setBusy(false);
  }
}

async function postJson(url, payload = {}) {
  const response = await fetch(url, {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify(payload),
  });
  const data = await response.json();
  if (!response.ok) {
    throw new Error(data.error || `Request failed with HTTP ${response.status}`);
  }
  return data;
}

async function generatePlan() {
  const goal = els.goalInput.value.trim();
  if (!goal) {
    els.commandMessage.textContent = "Enter a cycle goal first.";
    return;
  }
  setBusy(true);
  els.commandMessage.textContent = "Reading repository context and asking Ollama for a strict plan...";
  setActivePhase("context-intake");
  window.setTimeout(() => setActivePhase("self-read"), 350);
  window.setTimeout(() => setActivePhase("plan-proposal"), 700);
  try {
    const data = await postJson("/api/generate-plan", {goal});
    renderPendingPlan(data.pending_plan);
    renderObjective(data.state.objective);
    renderRepo(data.state.repo, data.state.generated_from);
    renderPlanner(data.state.planner);
    renderCycles(data.state.cycles || []);
    renderEvents(data.state.events || []);
    setActivePhase("human-review");
    els.commandMessage.textContent = "Plan generated. Review it before approving execution.";
  } catch (error) {
    els.commandMessage.textContent = error.message;
    setActivePhase(null);
  } finally {
    setBusy(false);
  }
}

async function runPendingPlan() {
  if (!pendingPlan) return;
  setBusy(true);
  els.commandMessage.textContent = "Applying approved plan and running verification...";
  setActivePhase("execute");
  window.setTimeout(() => setActivePhase("test"), 500);
  try {
    const data = await postJson("/api/run-pending-plan");
    renderPendingPlan(data.state.pending_plan);
    renderRepo(data.state.repo, data.state.generated_from);
    renderPlanner(data.state.planner);
    renderCycles(data.state.cycles || []);
    renderEvents(data.state.events || []);
    setActivePhase("commit-or-rollback");
    const attemptCount = data.attempts?.length || 1;
    els.commandMessage.textContent = data.result.accepted
      ? `Accepted after ${attemptCount} attempt(s) and committed ${data.result.commit_hash || ""}`.trim()
      : `Rejected after ${attemptCount} attempt(s): ${data.result.evaluation.reason}`;
  } catch (error) {
    els.commandMessage.textContent = error.message;
  } finally {
    setBusy(false);
  }
}

async function dryRunPendingPlan() {
  if (!pendingPlan) return;
  setBusy(true);
  els.commandMessage.textContent = "Running approved plan in a temporary copy...";
  setActivePhase("execute");
  window.setTimeout(() => setActivePhase("test"), 500);
  try {
    const data = await postJson("/api/dry-run-pending-plan");
    renderPendingPlan(data.state.pending_plan);
    renderRepo(data.state.repo, data.state.generated_from);
    renderPlanner(data.state.planner);
    renderCycles(data.state.cycles || []);
    renderEvents(data.state.events || []);
    setActivePhase("human-review");
    els.commandMessage.textContent = data.result.accepted
      ? "Dry run accepted without mutating the repository."
      : `Dry run rejected: ${data.result.reason}`;
  } catch (error) {
    els.commandMessage.textContent = error.message;
  } finally {
    setBusy(false);
  }
}

async function clearPendingPlan() {
  setBusy(true);
  try {
    const data = await postJson("/api/clear-pending-plan");
    renderPendingPlan(data.state.pending_plan);
    renderEvents(data.state.events || []);
    setActivePhase(null);
    els.commandMessage.textContent = "Pending plan cleared.";
  } catch (error) {
    els.commandMessage.textContent = error.message;
  } finally {
    setBusy(false);
  }
}

els.refreshBtn.addEventListener("click", refresh);
els.suggestGoalsBtn.addEventListener("click", suggestGoals);
els.generatePlanBtn.addEventListener("click", generatePlan);
els.dryRunPlanBtn.addEventListener("click", dryRunPendingPlan);
els.runPlanBtn.addEventListener("click", runPendingPlan);
els.clearPlanBtn.addEventListener("click", clearPendingPlan);
setActivePhase(null);
refresh();
setInterval(refresh, 15000);
