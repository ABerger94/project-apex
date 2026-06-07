from __future__ import annotations

from apex.core.models import ChangePlan, CycleResult


RETRYABLE_REASONS = {
    "verification_failed",
    "empty_git_diff",
    "no_files_changed",
}


def should_retry_cycle(result: CycleResult) -> bool:
    return not result.accepted and result.reason in RETRYABLE_REASONS


def build_repair_goal(original_goal: str, failed_plan: ChangePlan, result: CycleResult, attempt_number: int) -> str:
    stdout = tail_text(result.verification.stdout)
    stderr = tail_text(result.verification.stderr)
    checks = "\n".join(
        f"- {check.get('name')}: {check.get('detail')}"
        for check in result.verification.checks
    )
    return "\n".join([
        "Repair the failed APEX V2 cycle with a different concrete approach.",
        f"Original user goal: {original_goal}",
        f"Repair attempt: {attempt_number}",
        "",
        "Failed plan:",
        f"- title: {failed_plan.title}",
        f"- target: {failed_plan.target}",
        f"- rationale: {failed_plan.rationale}",
        f"- operations: {', '.join(operation.path for operation in failed_plan.operations)}",
        "",
        "Failure result:",
        f"- reason: {result.reason}",
        f"- changed_paths: {', '.join(result.changed_paths) or 'none'}",
        f"- verification_returncode: {result.verification.returncode}",
        "",
        "Verification checks:",
        checks or "- none",
        "",
        "Verification stdout tail:",
        stdout or "- empty",
        "",
        "Verification stderr tail:",
        stderr or "- empty",
        "",
        "Generate a new strict JSON plan that fixes the underlying cause.",
        "Do not repeat the same failing operation unless you change the implementation strategy.",
    ])


def tail_text(value: str, max_chars: int = 2400) -> str:
    value = value or ""
    if len(value) <= max_chars:
        return value
    return value[-max_chars:]
