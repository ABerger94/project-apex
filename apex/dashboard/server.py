from __future__ import annotations

import json
import mimetypes
from dataclasses import asdict
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from apex.dashboard.state import dashboard_state
from apex.core.memory import EventMemory
from apex.core.plan_loader import plan_from_dict
from apex.core.planner import OllamaPlanner
from apex.run_cycle import run_manual_cycle


ROOT = Path(__file__).resolve().parents[2]
PUBLIC_DIR = Path(__file__).resolve().parent / "public"
DEFAULT_PORT = 4188


class DashboardHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/api/state":
            self._send_json(dashboard_state(ROOT))
            return
        self._serve_static(parsed.path)

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/api/generate-plan":
            self._generate_plan()
            return
        if parsed.path == "/api/run-pending-plan":
            self._run_pending_plan()
            return
        if parsed.path == "/api/clear-pending-plan":
            self._clear_pending_plan()
            return
        self._send_json({"error": "not found"}, status=404)

    def log_message(self, format: str, *args) -> None:
        return

    def _send_json(self, payload: dict, status: int = 200) -> None:
        body = json.dumps(payload, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _read_json_body(self) -> dict:
        content_length = int(self.headers.get("Content-Length", "0"))
        if content_length > 100_000:
            raise ValueError("request body is too large")
        if content_length == 0:
            return {}
        body = self.rfile.read(content_length).decode("utf-8")
        data = json.loads(body)
        if not isinstance(data, dict):
            raise ValueError("request body must be a JSON object")
        return data

    def _generate_plan(self) -> None:
        try:
            data = self._read_json_body()
            goal = str(data.get("goal") or "").strip()
            if not goal:
                self._send_json({"error": "goal is required"}, status=400)
                return
            memory = EventMemory(ROOT / "memory" / "events.jsonl")
            memory.append("plan_generation_started", {"goal": goal})
            planner = OllamaPlanner()
            memory.append("planner_selected", planner.diagnostic())
            plan = planner.propose(ROOT, goal)
            payload = {"goal": goal, "plan": asdict(plan)}
            pending_path = ROOT / "memory" / "pending_plan.json"
            pending_path.parent.mkdir(parents=True, exist_ok=True)
            pending_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
            memory.append("plan_generated", {
                "goal": goal,
                "title": plan.title,
                "target": plan.target,
                "operation_count": len(plan.operations),
                "operations": [asdict(operation) for operation in plan.operations],
                "verification_command": list(plan.verification_command),
                "plan": asdict(plan),
            })
            self._send_json({"pending_plan": payload, "state": dashboard_state(ROOT)})
        except Exception as error:
            EventMemory(ROOT / "memory" / "events.jsonl").append("plan_generation_failed", {
                "error": str(error),
                "planner": OllamaPlanner().diagnostic(),
            })
            self._send_json({"error": str(error)}, status=500)

    def _run_pending_plan(self) -> None:
        pending_path = ROOT / "memory" / "pending_plan.json"
        if not pending_path.exists():
            self._send_json({"error": "no pending plan to run"}, status=400)
            return
        try:
            data = json.loads(pending_path.read_text(encoding="utf-8"))
            plan = plan_from_dict(data.get("plan") if isinstance(data, dict) else None)
            result = run_manual_cycle(ROOT, plan, commit=True)
            pending_path.unlink(missing_ok=True)
            self._send_json({"result": asdict(result), "state": dashboard_state(ROOT)})
        except Exception as error:
            EventMemory(ROOT / "memory" / "events.jsonl").append("pending_plan_run_failed", {"error": str(error)})
            self._send_json({"error": str(error)}, status=500)

    def _clear_pending_plan(self) -> None:
        pending_path = ROOT / "memory" / "pending_plan.json"
        pending_path.unlink(missing_ok=True)
        EventMemory(ROOT / "memory" / "events.jsonl").append("pending_plan_cleared", {})
        self._send_json({"state": dashboard_state(ROOT)})

    def _serve_static(self, request_path: str) -> None:
        relative = "index.html" if request_path in {"", "/"} else request_path.lstrip("/")
        path = (PUBLIC_DIR / relative).resolve()
        try:
            path.relative_to(PUBLIC_DIR.resolve())
        except ValueError:
            self.send_error(403)
            return
        if not path.exists() or not path.is_file():
            self.send_error(404)
            return
        body = path.read_bytes()
        content_type = mimetypes.guess_type(str(path))[0] or "application/octet-stream"
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def run(port: int = DEFAULT_PORT) -> None:
    server = ThreadingHTTPServer(("127.0.0.1", port), DashboardHandler)
    print(f"APEX V2 command center running at http://127.0.0.1:{port}")
    server.serve_forever()


if __name__ == "__main__":
    run()
