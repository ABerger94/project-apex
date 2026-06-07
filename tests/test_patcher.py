import tempfile
import unittest
from pathlib import Path

from apex.core.models import ChangePlan, FileOperation
from apex.core.patcher import Patcher


class PatcherTests(unittest.TestCase):
    def test_rejects_path_escape(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            patcher = Patcher(Path(temp_dir))
            plan = ChangePlan(
                title="Bad path",
                rationale="Paths must stay inside the repo.",
                target="safety",
                operations=(FileOperation(kind="write_file", path="../escape.py", content="x = 1\n"),),
            )

            with self.assertRaises(ValueError):
                patcher.apply(plan)

    def test_replace_text_changes_existing_file(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "module.py").write_text("VALUE = 1\n", encoding="utf-8")
            plan = ChangePlan(
                title="Update value",
                rationale="A concrete source edit should be applied.",
                target="module.py",
                operations=(FileOperation(kind="replace_text", path="module.py", old="VALUE = 1", new="VALUE = 2"),),
            )

            result = Patcher(root).apply(plan)

            self.assertEqual((root / "module.py").read_text(encoding="utf-8"), "VALUE = 2\n")
            self.assertEqual(result.changed_paths, (root / "module.py",))


if __name__ == "__main__":
    unittest.main()

