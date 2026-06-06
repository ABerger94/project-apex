import tempfile
import unittest
from pathlib import Path

from config import SandboxConfig
from core.oracle import Hypothesis
from self_edit.engine import SelfEditEngine


class SelfEditTests(unittest.TestCase):
    def test_duplicate_proposal_is_rejected_before_commit(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            proposal_dir = root / "self_edit" / "proposals"
            config = SandboxConfig(proposal_dir=proposal_dir)
            engine = SelfEditEngine(root, config)
            hypothesis = Hypothesis(
                title="Increase benchmark observability",
                rationale="APEX should improve measurement before trusting self-edits.",
                target_signal="verification_coverage",
                expected_delta=0.05,
                proposed_patch="# Proposal: improve benchmark observability",
            )
            first_path = engine._write_proposal(hypothesis)

            result = engine.apply_and_verify(hypothesis)

            self.assertFalse(result.accepted)
            self.assertEqual(result.reason, "duplicate_proposal")
            self.assertEqual(result.proposal_path, first_path)

    def test_hypothesis_writes_functional_capability_code(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "levels").mkdir()
            capability_path = root / "levels" / "l5_capabilities.py"
            capability_path.write_text(
                "\n".join([
                    "from __future__ import annotations",
                    "",
                    "",
                    "CAPABILITIES = []",
                    "",
                    "",
                    "def capability_signals() -> dict[str, float]:",
                    "    return {}",
                    "",
                ]),
                encoding="utf-8",
            )
            config = SandboxConfig(proposal_dir=root / "self_edit" / "proposals")
            engine = SelfEditEngine(root, config)
            hypothesis = Hypothesis(
                title="Add L5 coordination benchmark",
                rationale="Improve coordination.",
                target_signal="coordination_score",
                expected_delta=0.08,
                proposed_patch="# Proposal: add L5 coordination benchmark",
            )

            changed = engine._apply_implementation(hypothesis)
            capabilities = engine._read_capabilities(capability_path)

            self.assertEqual(changed, [capability_path])
            self.assertEqual(capabilities[0]["target_signal"], "coordination_score")
            self.assertEqual(capabilities[0]["expected_delta"], 0.08)


if __name__ == "__main__":
    unittest.main()
