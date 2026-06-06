const { spawn } = require("node:child_process");
const fs = require("node:fs");
const http = require("node:http");
const path = require("node:path");
const url = require("node:url");

const root = path.resolve(__dirname, "..");
const publicDir = path.join(__dirname, "public");
const port = Number(process.env.APEX_DASHBOARD_PORT || 4177);
const minIntervalMs = 60 * 1000;
const continuousCooldownMs = Number(process.env.APEX_CONTINUOUS_COOLDOWN_MS || minIntervalMs);
const maxDashboardItems = Number(process.env.APEX_DASHBOARD_MAX_ITEMS || 50);

const scheduler = {
  enabled: false,
  mode: "stopped",
  intervalMs: 60 * 60 * 1000,
  timer: null,
  running: false,
  lastStartedAt: null,
  lastFinishedAt: null,
  nextRunAt: null,
  lastResult: null,
};

function sendJson(res, status, data) {
  res.writeHead(status, { "Content-Type": "application/json" });
  res.end(JSON.stringify(data, null, 2));
}

function sendText(res, status, text, contentType = "text/plain") {
  res.writeHead(status, { "Content-Type": contentType });
  res.end(text);
}

function safeRead(filePath, fallback = "") {
  try {
    return fs.readFileSync(filePath, "utf8");
  } catch {
    return fallback;
  }
}

function run(command, args, options = {}) {
  return new Promise((resolve) => {
    const child = spawn(command, args, {
      cwd: root,
      shell: false,
      windowsHide: true,
      ...options,
    });
    let stdout = "";
    let stderr = "";
    child.stdout.on("data", (chunk) => {
      stdout += chunk.toString();
    });
    child.stderr.on("data", (chunk) => {
      stderr += chunk.toString();
    });
    child.on("close", (code) => resolve({ code, stdout, stderr }));
    child.on("error", (error) => resolve({ code: 1, stdout, stderr: error.message }));
  });
}

function readBody(req) {
  return new Promise((resolve) => {
    let body = "";
    req.on("data", (chunk) => {
      body += chunk.toString();
    });
    req.on("end", () => {
      if (!body.trim()) return resolve({});
      try {
        resolve(JSON.parse(body));
      } catch {
        resolve({});
      }
    });
  });
}

function pythonCommand() {
  const candidates = [
    process.env.PYTHON,
    path.join(process.env.LOCALAPPDATA || "", "Programs", "Python", "Python312", "python.exe"),
    "py",
    "python",
  ].filter(Boolean);

  for (const candidate of candidates) {
    if (candidate.endsWith(".exe") && fs.existsSync(candidate)) return { command: candidate, argsPrefix: [] };
    if (candidate === "py") return { command: "py", argsPrefix: ["-3"] };
    if (candidate === "python") return { command: "python", argsPrefix: [] };
  }
  return { command: "python", argsPrefix: [] };
}

function readEvents() {
  const file = path.join(root, "memory", "episodic_log.jsonl");
  return safeRead(file)
    .split(/\r?\n/)
    .filter(Boolean)
    .map((line) => {
      try {
        return JSON.parse(line);
      } catch {
        return null;
      }
    })
    .filter(Boolean)
    .reverse();
}

function readProposals() {
  const dir = path.join(root, "self_edit", "proposals");
  if (!fs.existsSync(dir)) return [];
  return fs.readdirSync(dir)
    .filter((name) => name.endsWith(".md"))
    .map((name) => {
      const filePath = path.join(dir, name);
      const stat = fs.statSync(filePath);
      const content = safeRead(filePath);
      return {
        name,
        path: path.relative(root, filePath),
        modified: stat.mtime.toISOString(),
        preview: content.split(/\r?\n/).slice(0, 8).join("\n"),
      };
    })
    .sort((a, b) => b.modified.localeCompare(a.modified));
}

function readSourceSummary() {
  const files = [
    "apex_loop.py",
    "config.py",
    "metrics.py",
    "core/oracle.py",
    "self_edit/engine.py",
    "levels/l3_agent.py",
  ];
  return files.map((relativePath) => {
    const content = safeRead(path.join(root, relativePath));
    return {
      path: relativePath,
      preview: content.split(/\r?\n/).slice(0, 80).join("\n"),
    };
  });
}

async function gitCommits() {
  const result = await run("git", ["log", "--oneline", "--decorate", "-12"]);
  return result.stdout
    .split(/\r?\n/)
    .filter(Boolean)
    .map((line) => {
      const [hash, ...rest] = line.split(" ");
      return { hash, message: rest.join(" ") };
    });
}

async function gitStatus() {
  const result = await run("git", ["status", "--short"]);
  return result.stdout.split(/\r?\n/).filter(Boolean);
}

async function dashboardState() {
  const events = readEvents().slice(0, maxDashboardItems);
  const latest = events[0] || null;
  return {
    latest,
    events,
    proposals: readProposals().slice(0, maxDashboardItems),
    commits: await gitCommits(),
    status: await gitStatus(),
    scheduler: schedulerState(),
    generatedAt: new Date().toISOString(),
  };
}

async function knowledgePack() {
  const state = await dashboardState();
  return {
    latest: state.latest,
    recentEvents: state.events.slice(0, 8),
    proposals: state.proposals.slice(0, 8),
    commits: state.commits,
    status: state.status,
    scheduler: state.scheduler,
    source: readSourceSummary(),
  };
}

function schedulerState() {
  return {
    enabled: scheduler.enabled,
    mode: scheduler.mode,
    intervalMs: scheduler.intervalMs,
    intervalHours: scheduler.intervalMs / (60 * 60 * 1000),
    running: scheduler.running,
    lastStartedAt: scheduler.lastStartedAt,
    lastFinishedAt: scheduler.lastFinishedAt,
    nextRunAt: scheduler.nextRunAt,
    lastResult: scheduler.lastResult,
  };
}

async function executeApexCycle(trigger = "manual") {
  if (scheduler.running) {
    return {
      ok: false,
      skipped: true,
      reason: "A cycle is already running.",
      state: await dashboardState(),
    };
  }

  scheduler.running = true;
  scheduler.lastStartedAt = new Date().toISOString();
  const { command, argsPrefix } = pythonCommand();
  const result = await run(command, [...argsPrefix, "apex_loop.py", "--cycles", "1"]);
  scheduler.running = false;
  scheduler.lastFinishedAt = new Date().toISOString();
  scheduler.lastResult = {
    ok: result.code === 0,
    trigger,
    finishedAt: scheduler.lastFinishedAt,
  };

  if (scheduler.enabled && scheduler.mode === "continuous") {
    scheduleNextRun(Math.max(minIntervalMs, continuousCooldownMs));
  } else if (scheduler.enabled && scheduler.mode === "interval") {
    scheduleNextRun(scheduler.intervalMs);
  }

  const state = await dashboardState();
  return {
    ok: result.code === 0,
    skipped: false,
    trigger,
    command: [command, ...argsPrefix, "apex_loop.py", "--cycles", "1"].join(" "),
    stdout: result.stdout,
    stderr: result.stderr,
    state,
  };
}

function clearSchedulerTimer() {
  if (scheduler.timer) {
    clearTimeout(scheduler.timer);
    scheduler.timer = null;
  }
  scheduler.nextRunAt = null;
}

function scheduleNextRun(delayMs) {
  clearSchedulerTimer();
  if (!scheduler.enabled) return;

  const safeDelay = Math.max(0, delayMs);
  scheduler.nextRunAt = new Date(Date.now() + safeDelay).toISOString();
  scheduler.timer = setTimeout(async () => {
    scheduler.timer = null;
    scheduler.nextRunAt = null;
    await executeApexCycle("scheduler");
  }, safeDelay);
}

function startScheduler(mode, intervalMs) {
  scheduler.enabled = true;
  scheduler.mode = mode;
  if (mode === "interval") {
    scheduler.intervalMs = Math.max(minIntervalMs, Number(intervalMs) || scheduler.intervalMs);
    scheduleNextRun(scheduler.intervalMs);
  } else {
    scheduler.mode = "continuous";
    scheduleNextRun(0);
  }
}

function stopScheduler() {
  scheduler.enabled = false;
  scheduler.mode = "stopped";
  clearSchedulerTimer();
}

async function runApexCycle(req, res) {
  const payload = await executeApexCycle("manual");
  sendJson(res, payload.ok || payload.skipped ? 200 : 500, payload);
}

async function updateSchedule(req, res) {
  const body = await readBody(req);
  const action = String(body.action || "").toLowerCase();
  const mode = String(body.mode || "interval").toLowerCase();
  const intervalMs = Number(body.intervalMs);

  if (action === "stop") {
    stopScheduler();
    return sendJson(res, 200, { ok: true, scheduler: schedulerState(), state: await dashboardState() });
  }

  if (action === "start") {
    startScheduler(mode === "continuous" ? "continuous" : "interval", intervalMs);
    return sendJson(res, 200, { ok: true, scheduler: schedulerState(), state: await dashboardState() });
  }

  sendJson(res, 400, { ok: false, error: "Unknown schedule action." });
}

function answerLocally(question, context) {
  const normalized = question.toLowerCase();
  const latest = context.latest;
  const scores = latest?.scores || {};
  const lines = [];

  if (!latest) {
    return "I do not have any recorded APEX runs yet. Run a cycle first, then ask again.";
  }

  if (normalized.includes("thought") || normalized.includes("thinking") || normalized.includes("process") || normalized.includes("hypothesis")) {
    lines.push(`Latest hypothesis: ${latest.hypothesis?.title || "unknown"}.`);
    lines.push(`Rationale: ${latest.hypothesis?.rationale || "not recorded"}.`);
    lines.push(`The current target signal is ${latest.hypothesis?.target_signal || "unknown"} with expected delta ${latest.hypothesis?.expected_delta ?? "unknown"}.`);
  } else if (normalized.includes("log") || normalized.includes("run") || normalized.includes("history")) {
    lines.push(`I have ${context.recentEvents.length} recent run records loaded.`);
    for (const event of context.recentEvents.slice(0, 5)) {
      lines.push(`Cycle ${event.cycle} at ${event.timestamp}: ${event.accepted ? "accepted" : "rejected"}, level ${event.current_level}, gap ${event.gap}, commit ${event.commit_hash || "none"}.`);
    }
  } else if (normalized.includes("commit") || normalized.includes("change")) {
    lines.push("Recent commits:");
    for (const commit of context.commits.slice(0, 8)) {
      lines.push(`${commit.hash}: ${commit.message}`);
    }
  } else if (normalized.includes("schedule") || normalized.includes("interval") || normalized.includes("continuous")) {
    const schedulerInfo = context.scheduler;
    lines.push(`Scheduler mode: ${schedulerInfo.mode}. Enabled: ${schedulerInfo.enabled}. Running: ${schedulerInfo.running}.`);
    lines.push(`Interval: ${schedulerInfo.intervalMs} ms. Next run: ${schedulerInfo.nextRunAt || "none"}. Last finish: ${schedulerInfo.lastFinishedAt || "none"}.`);
  } else if (normalized.includes("score") || normalized.includes("level") || normalized.includes("gap")) {
    lines.push(`Current level: ${latest.current_level}.`);
    lines.push(`Scores: L3 ${scores.l3_agent}, L4 ${scores.l4_innovator}, L5 ${scores.l5_organizer}.`);
    lines.push(`Largest gap: ${latest.gap}.`);
  } else {
    lines.push(`Current level is ${latest.current_level}; largest gap is ${latest.gap}.`);
    lines.push(`Latest hypothesis is "${latest.hypothesis?.title || "unknown"}".`);
    lines.push(`Latest accepted commit is ${latest.commit_hash || "none"}.`);
    lines.push("Ask about thoughts, logs, commits, scheduler, scores, proposals, or source modules for a narrower answer.");
  }

  if (context.status.length) {
    lines.push(`Working tree has ${context.status.length} pending item(s): ${context.status.join("; ")}`);
  } else {
    lines.push("Working tree is clean.");
  }

  return lines.join("\n");
}

async function answerWithBase44(question, context) {
  const appId = process.env.BASE44_APP_ID || process.env.VITE_BASE44_APP_ID;
  if (!appId || process.env.APEX_CHAT_PROVIDER !== "base44") return null;

  const prompt = [
    "You are the APEX Command Center assistant.",
    "Answer only from the provided APEX context. If information is not present, say so.",
    "Be concise and operational. Distinguish recorded state from inference.",
    "",
    `Question: ${question}`,
    "",
    `APEX context:\n${JSON.stringify(context, null, 2)}`,
  ].join("\n");

  const schema = {
    answer: "string",
    citations: "array of strings naming files, logs, commits, or state fields used",
  };
  const script = [
    "const { createClient } = require('@base44/sdk');",
    "const input = JSON.parse(process.argv[1]);",
    "const client = createClient({ appId: process.env.BASE44_APP_ID || process.env.VITE_BASE44_APP_ID, token: process.env.BASE44_ACCESS_TOKEN, serverUrl: '', requiresAuth: false });",
    "client.integrations.Core.InvokeLLM({ prompt: input.prompt, response_json_schema: input.schema })",
    ".then(r => console.log(JSON.stringify(r)))",
    ".catch(e => { console.error(e.message || String(e)); process.exit(2); });",
  ].join("");

  const result = await run("node", ["-e", script, JSON.stringify({ prompt, schema })], {
    env: process.env,
  });
  if (result.code !== 0) {
    return {
      answer: `Base44 chat failed, so I am using local context instead.\n\n${answerLocally(question, context)}`,
      citations: ["dashboard/server.js", "local fallback"],
      provider: "local-fallback",
      error: result.stderr,
    };
  }

  try {
    const data = JSON.parse(result.stdout);
    return {
      answer: String(data.answer || ""),
      citations: Array.isArray(data.citations) ? data.citations : [],
      provider: "base44",
    };
  } catch {
    return {
      answer: result.stdout.trim() || answerLocally(question, context),
      citations: ["Base44 raw response"],
      provider: "base44",
    };
  }
}

async function answerWithGroq(question, context) {
  const apiKey = process.env.GROQ_API_KEY;
  if (!apiKey || process.env.APEX_CHAT_PROVIDER !== "groq") return null;

  const model = process.env.GROQ_MODEL || "llama-3.3-70b-versatile";
  const prompt = [
    "You are the APEX Command Center assistant.",
    "Answer only from the provided APEX context. If information is not present, say so.",
    "Be concise and operational. Distinguish recorded state from inference.",
    "Return plain text. Do not invent hidden thoughts; describe recorded hypotheses, logs, and state.",
    "",
    `Question: ${question}`,
    "",
    `APEX context:\n${JSON.stringify(context, null, 2)}`,
  ].join("\n");

  try {
    const response = await fetch("https://api.groq.com/openai/v1/chat/completions", {
      method: "POST",
      headers: {
        "Authorization": `Bearer ${apiKey}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        model,
        messages: [
          {
            role: "system",
            content: "You answer questions about APEX from supplied context only.",
          },
          {
            role: "user",
            content: prompt,
          },
        ],
        temperature: 0.2,
      }),
    });

    const data = await response.json();
    if (!response.ok) {
      return {
        answer: `Groq chat failed, so I am using local context instead.\n\n${answerLocally(question, context)}`,
        citations: ["dashboard/server.js", "local fallback"],
        provider: "local-fallback",
        error: data.error?.message || response.statusText,
      };
    }

    return {
      answer: String(data.choices?.[0]?.message?.content || "").trim() || answerLocally(question, context),
      citations: ["Groq chat completion", "memory/episodic_log.jsonl", "git log", "scheduler state", "self_edit/proposals"],
      provider: "groq",
      model,
    };
  } catch (error) {
    return {
      answer: `Groq chat failed, so I am using local context instead.\n\n${answerLocally(question, context)}`,
      citations: ["dashboard/server.js", "local fallback"],
      provider: "local-fallback",
      error: error.message,
    };
  }
}

async function chat(req, res) {
  const body = await readBody(req);
  const question = String(body.message || body.question || "").trim();
  if (!question) return sendJson(res, 400, { ok: false, error: "Message is required." });

  const context = await knowledgePack();
  const llmAnswer = await answerWithGroq(question, context) || await answerWithBase44(question, context);
  const payload = llmAnswer || {
    answer: answerLocally(question, context),
    citations: ["memory/episodic_log.jsonl", "git log", "scheduler state", "self_edit/proposals"],
    provider: "local",
  };

  sendJson(res, 200, {
    ok: true,
    question,
    ...payload,
    contextStats: {
      runs: context.recentEvents.length,
      proposals: context.proposals.length,
      commits: context.commits.length,
      sourceFiles: context.source.length,
    },
  });
}

function serveStatic(req, res) {
  const requestPath = url.parse(req.url).pathname;
  const fileName = requestPath === "/" ? "index.html" : requestPath.slice(1);
  const filePath = path.normalize(path.join(publicDir, fileName));
  if (!filePath.startsWith(publicDir)) return sendText(res, 403, "Forbidden");
  if (!fs.existsSync(filePath)) return sendText(res, 404, "Not found");

  const ext = path.extname(filePath).toLowerCase();
  const types = {
    ".html": "text/html",
    ".css": "text/css",
    ".js": "text/javascript",
    ".svg": "image/svg+xml",
  };
  sendText(res, 200, fs.readFileSync(filePath), types[ext] || "application/octet-stream");
}

const server = http.createServer(async (req, res) => {
  if (req.method === "GET" && req.url.startsWith("/api/state")) {
    return sendJson(res, 200, await dashboardState());
  }
  if (req.method === "POST" && req.url.startsWith("/api/schedule")) {
    return updateSchedule(req, res);
  }
  if (req.method === "POST" && req.url.startsWith("/api/chat")) {
    return chat(req, res);
  }
  if (req.method === "POST" && req.url.startsWith("/api/run")) {
    return runApexCycle(req, res);
  }
  return serveStatic(req, res);
});

server.listen(port, () => {
  console.log(`APEX command center running at http://localhost:${port}`);
});
