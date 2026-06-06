const { spawn } = require("node:child_process");
const fs = require("node:fs");
const http = require("node:http");
const path = require("node:path");
const url = require("node:url");

const root = path.resolve(__dirname, "..");
const publicDir = path.join(__dirname, "public");
const port = Number(process.env.APEX_DASHBOARD_PORT || 4177);

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
  const events = readEvents();
  const latest = events[0] || null;
  return {
    latest,
    events,
    proposals: readProposals(),
    commits: await gitCommits(),
    status: await gitStatus(),
    generatedAt: new Date().toISOString(),
  };
}

async function runApexCycle(req, res) {
  const { command, argsPrefix } = pythonCommand();
  const result = await run(command, [...argsPrefix, "apex_loop.py", "--cycles", "1"]);
  const state = await dashboardState();
  sendJson(res, result.code === 0 ? 200 : 500, {
    ok: result.code === 0,
    command: [command, ...argsPrefix, "apex_loop.py", "--cycles", "1"].join(" "),
    stdout: result.stdout,
    stderr: result.stderr,
    state,
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
  if (req.method === "POST" && req.url.startsWith("/api/run")) {
    return runApexCycle(req, res);
  }
  return serveStatic(req, res);
});

server.listen(port, () => {
  console.log(`APEX command center running at http://localhost:${port}`);
});
