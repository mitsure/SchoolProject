import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


LAUNCH_SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "macos_launch.sh"


@unittest.skipUnless(shutil.which("bash"), "bash is required")
class MacOSLaunchTest(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.project = Path(self.directory.name)
        (self.project / "scripts").mkdir()
        shutil.copyfile(LAUNCH_SCRIPT, self.project / "scripts" / "macos_launch.sh")
        (self.project / "logs").mkdir()
        self.error_log = self.project / "logs" / "studyllm.err.log"
        self.error_log.write_text("OLD_LOGIN_TRACEBACK\n", encoding="utf-8")
        (self.project / "logs" / "studyllm.out.log").write_text("OLD_ACCESS_LOG\n", encoding="utf-8")
        (self.project / ".env").write_text("# Test fixture\n", encoding="utf-8")
        (self.project / ".venv" / "bin").mkdir(parents=True)
        python_stub = self.project / ".venv" / "bin" / "python"
        python_stub.write_text("#!/bin/bash\nprintf '%s\\n' 'https://example.test'\n", encoding="utf-8")
        python_stub.chmod(0o755)
        self.calls = self.project / "calls.log"
        self.mocks = self.project / "mock_commands.sh"
        # Shell functions override real commands, even though the launcher prepends PATH.
        # No Mac service, browser, network endpoint, or delay is used by these tests.
        self.mocks.write_text(
            r"""
uname() { printf '%s\n' Darwin; }
sleep() { :; }
open() { printf 'open %s\n' "$*" >> "$TEST_CALLS"; }
launchctl() {
    printf 'launchctl %s\n' "$*" >> "$TEST_CALLS"
    case "$1" in
        print)
            printf '%s\n' 'state = exited' 'pid = 1234' 'last exit code = 1' \
                'last terminating signal = Terminated: 15' 'environment = {' \
                '  PRIVATE_TOKEN = DO_NOT_DISPLAY_THIS_SECRET' '}'
            ;;
        kickstart)
            if [ "$TEST_CASE" = new_error ]; then
                printf '%s\n' 'NEW_STARTUP_ERROR' >> logs/studyllm.err.log
                printf '%s\n' 'NEW_ACCESS_LOG' >> logs/studyllm.out.log
            fi
            ;;
        *) return 1 ;;
    esac
}
curl() {
    printf 'curl %s\n' "$*" >> "$TEST_CALLS"
    if [ "$1" != --noproxy ] || [ "$2" != '*' ]; then
        printf '%s\n' 'MISSING_PROXY_BYPASS' >&2
        return 99
    fi
    case "$*" in
        *11434*|*4040*) return 0 ;;
        *8000*)
            if [ "$TEST_CASE" = success ]; then return 0; fi
            case " $* " in
                *' --write-out '*)
                    if [ "$TEST_CASE" = http_error ]; then
                        printf 500
                        return 0
                    fi
                    printf 000
                    printf '%s\n' 'curl: (7) Could not connect' >&2
                    return 7
                    ;;
                *)
                    if [ "$TEST_CASE" = http_error ]; then return 22; fi
                    return 7
                    ;;
            esac
            ;;
        *) return 98 ;;
    esac
}
""",
            encoding="utf-8",
        )

    def run_launcher(self, scenario):
        environment = os.environ.copy()
        environment.update(BASH_ENV=str(self.mocks), TEST_CASE=scenario, TEST_CALLS=str(self.calls))
        result = subprocess.run(
            ["bash", str(self.project / "scripts" / "macos_launch.sh"), "start"],
            env=environment,
            capture_output=True,
            text=True,
            timeout=10,
        )
        self.assertNotIn("MISSING_PROXY_BYPASS", result.stdout + result.stderr)
        return result

    def test_success_opens_public_url_without_showing_old_logs(self):
        result = self.run_launcher("success")
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        self.assertIn("起動確認が完了しました。公開URL：https://example.test", result.stdout)
        self.assertIn("open https://example.test", self.calls.read_text(encoding="utf-8"))
        self.assertNotIn("OLD_LOGIN_TRACEBACK", result.stdout)

    def test_connection_failure_shows_only_new_logs_and_filtered_service_state(self):
        result = self.run_launcher("new_error")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("curl終了コード: 7", result.stdout)
        self.assertIn("state = exited", result.stdout)
        self.assertIn("pid = 1234", result.stdout)
        self.assertIn("last exit code = 1", result.stdout)
        self.assertIn("last terminating signal = Terminated: 15", result.stdout)
        self.assertIn("NEW_STARTUP_ERROR", result.stdout)
        self.assertIn("NEW_ACCESS_LOG", result.stdout)
        self.assertNotIn("OLD_LOGIN_TRACEBACK", result.stdout)
        self.assertNotIn("OLD_ACCESS_LOG", result.stdout)
        self.assertNotIn("DO_NOT_DISPLAY_THIS_SECRET", result.stdout + result.stderr)
        self.assertTrue(self.error_log.read_text(encoding="utf-8").startswith("OLD_LOGIN_TRACEBACK\n"))
        self.assertNotIn("open https://", self.calls.read_text(encoding="utf-8"))

    def test_stale_login_traceback_is_not_repeated_when_no_new_logs_exist(self):
        result = self.run_launcher("no_new_logs")
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(result.stdout.count("新しいログはありません。"), 2)
        self.assertNotIn("OLD_LOGIN_TRACEBACK", result.stdout)
        self.assertEqual(self.error_log.read_text(encoding="utf-8"), "OLD_LOGIN_TRACEBACK\n")

    def test_http_error_is_distinguished_from_connection_failure(self):
        result = self.run_launcher("http_error")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("ローカル接続確認: HTTP 500", result.stdout)
        self.assertNotIn("curl終了コード:", result.stdout)


if __name__ == "__main__":
    unittest.main()
