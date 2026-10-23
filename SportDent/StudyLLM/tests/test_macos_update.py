import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


LAUNCH_SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "macos_launch.sh"
PROJECT_PATH = Path("SportDent/StudyLLM")


@unittest.skipUnless(shutil.which("bash") and shutil.which("git"), "bash and git are required")
class MacOSUpdateTest(unittest.TestCase):
    """Exercise the update against real repositories without network or Mac services."""

    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.directory = Path(directory.name)
        self.remote = self.directory / "remote.git"
        self.seed = self.directory / "seed"
        self.checkout = self.directory / "checkout"
        self.stage_marker = self.directory / "updated-stage"
        self.environment = os.environ.copy()
        self.environment.update(GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL=os.devnull)
        self.git(self.directory, "init", "--bare", "--initial-branch=main", str(self.remote))
        self.git(self.directory, "init", "--initial-branch=main", str(self.seed))
        self.git(self.seed, "config", "user.name", "Update test")
        self.git(self.seed, "config", "user.email", "update@example.invalid")
        self.write(self.seed, PROJECT_PATH / "scripts/macos_launch.sh", LAUNCH_SCRIPT.read_text(encoding="utf-8"))
        self.write(self.seed, PROJECT_PATH / "app/version.txt", "initial\n")
        self.write(self.seed, "SportDent/.DS_Store", "original Finder metadata\n")
        self.write(self.seed, ".gitignore", "**/.env\n**/data/*.sqlite3\n")
        self.git(self.seed, "add", ".")
        self.git(self.seed, "commit", "-m", "Initial fixture")
        self.git(self.seed, "remote", "add", "origin", str(self.remote))
        self.git(self.seed, "push", "origin", "main")
        self.git(self.directory, "clone", str(self.remote), str(self.checkout))
        self.initial_head = self.git(self.checkout, "rev-parse", "HEAD").stdout.strip()

        # These preferences must not stash or rebase the user's local changes.
        self.git(self.checkout, "config", "pull.rebase", "true")
        self.git(self.checkout, "config", "rebase.autoStash", "true")
        self.git(self.checkout, "config", "merge.autoStash", "true")

        self.shell_hooks = self.directory / "shell-hooks.sh"
        self.shell_hooks.write_text(
            "uname() { printf '%s\\n' Darwin; }\n"
            # Bash 3.2 reads BASH_ENV before assigning script arguments.
            # Wait until the script itself has read its mode to stop the
            # updated stage before any real dependency or service operations.
            'trap \'if [ "${mode-}" = updated ]; then '
            'printf "%s\\n" updated > "$TEST_UPDATED_STAGE"; exit 0; fi\' DEBUG\n',
            encoding="utf-8",
        )

    def git(self, directory, *arguments):
        return subprocess.run(
            ["git", "-C", str(directory), *arguments],
            env=self.environment,
            check=True,
            capture_output=True,
            text=True,
            timeout=15,
        )

    def write(self, directory, relative_path, content):
        path = directory / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    def advance_remote(self, extra_files=None):
        self.write(self.seed, PROJECT_PATH / "app/version.txt", "updated remotely\n")
        for path, content in (extra_files or {}).items():
            self.write(self.seed, path, content)
        self.git(self.seed, "add", ".")
        self.git(self.seed, "commit", "-m", "Remote update")
        self.git(self.seed, "push", "origin", "main")
        return self.git(self.seed, "rev-parse", "HEAD").stdout.strip()

    def run_update(self):
        environment = self.environment.copy()
        environment.update(BASH_ENV=str(self.shell_hooks), TEST_UPDATED_STAGE=str(self.stage_marker))
        return subprocess.run(
            ["bash", str(self.checkout / PROJECT_PATH / "scripts/macos_launch.sh"), "update"],
            cwd=self.directory,
            env=environment,
            capture_output=True,
            text=True,
            timeout=15,
        )

    def assert_no_stash(self):
        self.assertEqual(self.git(self.checkout, "stash", "list").stdout, "")
        self.assertFalse((self.checkout / ".git/MERGE_AUTOSTASH").exists())
        self.assertFalse((self.checkout / ".git/rebase-merge").exists())

    def assert_update_stopped(self, result):
        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertFalse(self.stage_marker.exists(), "The launcher must not start after a failed update")
        self.assertEqual(self.git(self.checkout, "rev-parse", "HEAD").stdout.strip(), self.initial_head)
        self.assert_no_stash()

    def test_unrelated_local_files_are_preserved_and_update_continues(self):
        local_files = {
            "SportDent/.DS_Store": "locally changed Finder metadata\n",
            "SportDent/CreateData/Step2_傷害カテゴリ別解析/カテゴリ別抽出データ/result.csv": "local analysis\n",
            "SportDent/file/Step2_傷害カテゴリ別解析/result.csv": "another local analysis\n",
            PROJECT_PATH / ".venv/bin/python": "local Python environment\n",
            PROJECT_PATH / ".env": "TEST_PASSWORD=local-fixture-only\n",
            PROJECT_PATH / "data/reviews.sqlite3": "local saved records fixture\n",
        }
        for path, content in local_files.items():
            self.write(self.checkout, path, content)
        status_before = self.git(self.checkout, "status", "--porcelain", "--untracked-files=all").stdout
        self.assertIn(" M SportDent/.DS_Store", status_before)
        self.assertIn("?? SportDent/StudyLLM/.venv/bin/python", status_before)
        self.assertNotIn(".env", status_before)
        self.assertNotIn("reviews.sqlite3", status_before)
        expected_head = self.advance_remote()

        result = self.run_update()

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(self.stage_marker.read_text(encoding="utf-8"), "updated\n")
        self.assertEqual(self.git(self.checkout, "rev-parse", "HEAD").stdout.strip(), expected_head)
        self.assertEqual(
            self.git(self.checkout, "status", "--porcelain", "--untracked-files=all").stdout,
            status_before,
        )
        for path, content in local_files.items():
            self.assertEqual((self.checkout / path).read_text(encoding="utf-8"), content)
        self.assert_no_stash()

    def test_conflicting_tracked_edit_stops_update_without_autostash(self):
        local_path = PROJECT_PATH / "app/version.txt"
        self.write(self.checkout, local_path, "important local edit\n")
        self.advance_remote()

        result = self.run_update()

        self.assert_update_stopped(result)
        self.assertEqual((self.checkout / local_path).read_text(encoding="utf-8"), "important local edit\n")
        self.assertIn(" M SportDent/StudyLLM/app/version.txt", self.git(self.checkout, "status", "--porcelain").stdout)

    def test_colliding_untracked_file_stops_update_and_preserves_contents(self):
        local_path = PROJECT_PATH / "new-file.txt"
        self.write(self.checkout, local_path, "untracked user contents\n")
        self.advance_remote({local_path: "new remote contents\n"})

        result = self.run_update()

        self.assert_update_stopped(result)
        self.assertEqual((self.checkout / local_path).read_text(encoding="utf-8"), "untracked user contents\n")
        self.assertIn("?? SportDent/StudyLLM/new-file.txt", self.git(self.checkout, "status", "--porcelain").stdout)

if __name__ == "__main__":
    unittest.main()
