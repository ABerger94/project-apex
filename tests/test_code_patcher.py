import ast
import tempfile
import unittest
from pathlib import Path

from self_edit.code_patcher import CodePatch, PatchError, apply_patch


class AppendModeTests(unittest.TestCase):
    def test_appends_code_after_existing_content(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "module.py"
            target.write_text("x = 1\n", encoding="utf-8")
            patch = CodePatch(target_file="module.py", mode="append", code="def foo(): return 42")
            apply_patch(Path(tmp), patch)
            content = target.read_text(encoding="utf-8")
            self.assertIn("x = 1", content)
            self.assertIn("def foo():", content)
            self.assertGreater(content.index("def foo():"), content.index("x = 1"))

    def test_result_is_valid_python(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "module.py"
            target.write_text("x = 1\n", encoding="utf-8")
            patch = CodePatch(target_file="module.py", mode="append", code="def bar(n): return n * 2")
            apply_patch(Path(tmp), patch)
            ast.parse(target.read_text(encoding="utf-8"))  # must not raise

    def test_syntax_error_raises_patch_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "module.py"
            target.write_text("x = 1\n", encoding="utf-8")
            patch = CodePatch(target_file="module.py", mode="append", code="def broken(: pass")
            with self.assertRaises(PatchError):
                apply_patch(Path(tmp), patch)

    def test_file_unchanged_when_syntax_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "module.py"
            original = "x = 1\n"
            target.write_text(original, encoding="utf-8")
            patch = CodePatch(target_file="module.py", mode="append", code="def bad(: pass")
            try:
                apply_patch(Path(tmp), patch)
            except PatchError:
                pass
            self.assertEqual(target.read_text(encoding="utf-8"), original)

    def test_missing_target_raises_patch_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            patch = CodePatch(target_file="nonexistent.py", mode="append", code="x = 1")
            with self.assertRaises(PatchError):
                apply_patch(Path(tmp), patch)

    def test_returns_path_to_modified_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "module.py"
            target.write_text("x = 1\n", encoding="utf-8")
            patch = CodePatch(target_file="module.py", mode="append", code="y = 2")
            result = apply_patch(Path(tmp), patch)
            self.assertEqual(result, target)

    def test_append_to_empty_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "extensions.py"
            target.write_text("", encoding="utf-8")
            patch = CodePatch(target_file="extensions.py", mode="append", code="def f(): pass")
            apply_patch(Path(tmp), patch)
            content = target.read_text(encoding="utf-8")
            self.assertIn("def f():", content)
            ast.parse(content)

    def test_multiple_patches_accumulate(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "extensions.py"
            target.write_text("# stub\n", encoding="utf-8")
            for name in ("alpha", "beta", "gamma"):
                patch = CodePatch(
                    target_file="extensions.py",
                    mode="append",
                    code=f"def {name}(): return '{name}'",
                )
                apply_patch(Path(tmp), patch)
            content = target.read_text(encoding="utf-8")
            for name in ("alpha", "beta", "gamma"):
                self.assertIn(f"def {name}():", content)
            ast.parse(content)


class InsertAfterImportsTests(unittest.TestCase):
    def test_inserts_between_imports_and_body(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "module.py"
            target.write_text("import os\nimport sys\n\nx = 1\n", encoding="utf-8")
            patch = CodePatch(
                target_file="module.py",
                mode="insert_after_imports",
                code="def my_func(): pass",
            )
            apply_patch(Path(tmp), patch)
            content = target.read_text(encoding="utf-8")
            self.assertLess(content.index("import sys"), content.index("def my_func"))
            self.assertLess(content.index("def my_func"), content.index("x = 1"))

    def test_falls_back_to_append_when_no_imports(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "module.py"
            target.write_text("x = 1\n", encoding="utf-8")
            patch = CodePatch(
                target_file="module.py",
                mode="insert_after_imports",
                code="def f(): pass",
            )
            apply_patch(Path(tmp), patch)
            self.assertIn("def f():", target.read_text(encoding="utf-8"))

    def test_result_is_valid_python(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "module.py"
            target.write_text("from pathlib import Path\n\nROOT = Path('.')\n", encoding="utf-8")
            patch = CodePatch(
                target_file="module.py",
                mode="insert_after_imports",
                code="def helper(): return ROOT",
            )
            apply_patch(Path(tmp), patch)
            ast.parse(target.read_text(encoding="utf-8"))


class UnknownModeTests(unittest.TestCase):
    def test_unknown_mode_raises_patch_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "module.py"
            target.write_text("x = 1\n", encoding="utf-8")
            patch = CodePatch(target_file="module.py", mode="replace_function", code="pass")
            with self.assertRaises(PatchError):
                apply_patch(Path(tmp), patch)


class ExtensionCodePatchTests(unittest.TestCase):
    """Verify that the extension function strings bundled in oracle routes are valid Python."""

    def _check(self, code: str) -> None:
        """Each code string must be valid Python on its own."""
        try:
            ast.parse(code)
        except SyntaxError as exc:
            self.fail(f"Bundled code patch has a syntax error: {exc}\n---\n{code}")

    def test_audit_cycle_code_is_valid(self):
        from core.oracle import _CODE_AUDIT_CYCLE
        self._check(_CODE_AUDIT_CYCLE)

    def test_gap_velocity_code_is_valid(self):
        from core.oracle import _CODE_GAP_VELOCITY
        self._check(_CODE_GAP_VELOCITY)

    def test_signal_saturation_code_is_valid(self):
        from core.oracle import _CODE_SIGNAL_SATURATION
        self._check(_CODE_SIGNAL_SATURATION)

    def test_verify_gain_code_is_valid(self):
        from core.oracle import _CODE_VERIFY_GAIN
        self._check(_CODE_VERIFY_GAIN)

    def test_rank_objectives_code_is_valid(self):
        from core.oracle import _CODE_RANK_OBJECTIVES
        self._check(_CODE_RANK_OBJECTIVES)

    def test_validate_patch_code_is_valid(self):
        from core.oracle import _CODE_VALIDATE_PATCH
        self._check(_CODE_VALIDATE_PATCH)

    def test_score_route_code_is_valid(self):
        from core.oracle import _CODE_SCORE_ROUTE
        self._check(_CODE_SCORE_ROUTE)

    def test_detect_novel_code_is_valid(self):
        from core.oracle import _CODE_DETECT_NOVEL
        self._check(_CODE_DETECT_NOVEL)

    def test_stagnation_detector_code_is_valid(self):
        from core.oracle import _CODE_STAGNATION_DETECTOR
        self._check(_CODE_STAGNATION_DETECTOR)


if __name__ == "__main__":
    unittest.main()
