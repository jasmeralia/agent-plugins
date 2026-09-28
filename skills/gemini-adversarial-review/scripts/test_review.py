"""Disposable Git and sandbox checks; no real repository is sent to agy."""

import importlib.util
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch


SPEC = importlib.util.spec_from_file_location("review", Path(__file__).with_name("review.py"))
review = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(review)


def run(*args, cwd):
    return subprocess.run(args, cwd=cwd, check=True, capture_output=True)


class ReviewTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="review-test-")
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        run("git", "init", "-q", cwd=self.root)
        run("git", "config", "user.name", "Test", cwd=self.root)
        run("git", "config", "user.email", "test@example.com", cwd=self.root)
        (self.root / "name with spaces.py").write_text("old = 1\n")
        run("git", "add", ".", cwd=self.root)
        run("git", "commit", "-qm", "base", cwd=self.root)

    def selected(self, **kwargs):
        return review.select(self.root, kwargs.get("scope", "worktree"), kwargs.get("branch"),
                             kwargs.get("rev_range"), kwargs.get("path_filter"),
                             kwargs.get("include_untracked", False), kwargs.get("context_paths", []))

    def test_worktree_scope_and_untracked_opt_in(self):
        (self.root / "name with spaces.py").write_text("new = 2\n")
        (self.root / "untracked.txt").write_text("private fixture\n")
        result = self.selected()
        first_digest = review.selection_digest(result)
        self.assertEqual(result["changed_paths"], ["name with spaces.py"])
        self.assertNotIn("untracked.txt", result["files"])
        result = self.selected(include_untracked=True)
        self.assertNotEqual(first_digest, review.selection_digest(result))
        self.assertEqual(result["untracked_paths"], ["untracked.txt"])
        self.assertIn(b"private fixture", result["patch"])
        (self.root / "$(touch pwned).py").write_text("safe = True\n")
        result = self.selected(include_untracked=True)
        self.assertIn("$(touch pwned).py", result["untracked_paths"])
        self.assertFalse((self.root / "pwned").exists())

    def test_range_and_branch_are_committed_snapshots(self):
        base = review.revision(self.root, "HEAD")
        (self.root / "name with spaces.py").write_text("committed = 3\n")
        run("git", "add", ".", cwd=self.root)
        run("git", "commit", "-qm", "second", cwd=self.root)
        (self.root / "name with spaces.py").write_text("dirty = 4\n")
        result = self.selected(scope="range", rev_range=f"{base}..HEAD")
        self.assertEqual(result["files"]["name with spaces.py"], b"committed = 3\n")
        result = self.selected(scope="branch", branch=base)
        self.assertEqual(result["files"]["name with spaces.py"], b"committed = 3\n")

    def test_rejects_empty_invalid_refs_and_symlinks(self):
        with self.assertRaisesRegex(review.ReviewError, "empty diff"):
            self.selected()
        with self.assertRaises(review.ReviewError):
            review.revision(self.root, "--output=/tmp/evil")
        (self.root / "name with spaces.py").write_text("changed = 1\n")
        (self.root / "link.py").symlink_to("/etc/passwd")
        with self.assertRaisesRegex(review.ReviewError, "symlink"):
            self.selected(include_untracked=True)
        with self.assertRaises(review.ReviewError):
            self.selected(path_filter="../outside")
        before = review.selection_digest(self.selected())
        (self.root / "name with spaces.py").write_text("another change\n")
        self.assertNotEqual(before, review.selection_digest(self.selected()))

    def test_timeout_and_nonempty_result(self):
        with self.assertRaises(review.ReviewError):
            review.command(["/usr/bin/sleep", "1"], self.root, timeout=0.01)
        (self.root / "name with spaces.py").write_text("changed = 1\n")
        selected = self.selected()
        fake = self.root / "fake-agy"
        fake.write_text("#!/usr/bin/python3\nprint('{\"status\":\"SUCCESS\",\"response\":\"\"}')\n")
        fake.chmod(0o755)
        token = self.root / "token"
        token.write_text("fake token")
        with patch.object(review, "AUTH", token):
            with self.assertRaisesRegex(review.ReviewError, "did not return a review"):
                review.run_review(selected, "gemini-3.1-pro-high", 5, str(fake), False)
            fake.write_text("#!/usr/bin/python3\nprint('{\"status\":\"ERROR\",\"error\":\"quota exhausted\"}')\n")
            with self.assertRaisesRegex(review.ReviewError, "quota exhausted"):
                review.run_review(selected, "gemini-3.1-pro-high", 5, str(fake), False)
        p = subprocess.run(["/usr/bin/python3", str(Path(__file__).with_name("review.py")),
                            "--repo", str(self.root), "--run", "--expect-sha256", "wrong"],
                           capture_output=True, text=True)
        self.assertNotEqual(p.returncode, 0)
        self.assertIn("selection changed", p.stderr)

    def test_read_only_snapshot_and_source_absence(self):
        (self.root / "name with spaces.py").write_text("changed = 1\n")
        selected = self.selected()
        fake = self.root / "fake-agy"
        fake.write_text("#!/usr/bin/python3\n"
                        "from pathlib import Path\nimport json\n"
                        "p=Path('/review/files/name with spaces.py')\n"
                        "readable=p.read_text()=='changed = 1\\n'\n"
                        "try: p.write_text('tampered'); writable=True\n"
                        "except OSError: writable=False\n"
                        f"visible=Path({str(self.root)!r}).exists()\n"
                        "print(json.dumps({'status':'SUCCESS','response':f'{readable}:{writable}:{visible}'}))\n")
        fake.chmod(0o755)
        token = self.root / "token"
        token.write_text("fake token")
        with patch.object(review, "AUTH", token):
            result = review.run_review(selected, "gemini-3.1-pro-high", 5, str(fake), False)
        self.assertEqual(result["raw_review"], "True:False:False")
        self.assertEqual((self.root / "name with spaces.py").read_text(), "changed = 1\n")


if __name__ == "__main__":
    unittest.main()
