import tempfile
import unittest
from pathlib import Path

from apex.core.context import read_repo_context
from tests.helpers import init_repo


class ContextTests(unittest.TestCase):
    def test_context_includes_level_5_objective_directive(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            init_repo(root)

            context = read_repo_context(root)

            self.assertIn("Level 5 AGI Organizer", context.objective_directive)
            self.assertIn("L5 Organizers", context.objective_directive)


if __name__ == "__main__":
    unittest.main()

