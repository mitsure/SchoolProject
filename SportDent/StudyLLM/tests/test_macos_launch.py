import os
import shutil
import signal
import subprocess
import tempfile
import time
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
        python_stub.write_text(
            "#!/bin/bash\n"
            'if [ "${1-}" = run.py ]; then\n'
            '  if [ "$TEST_CASE" = fallback_failure ]; then echo DIRECT_START_ERROR; exit 1; fi\n'
            '  echo $$ > fallback.pid\n'
            "  trap 'echo stopped > fallback-stopped; exit 0' TERM INT HUP\n"
            "  touch fallback-ready\n"
            '  while [ ! -f fallback-release ]; do /bin/sleep 0.02; done\n'
            "  exit 0\n"
            "fi\n"
            "printf '%s\\n' 'https://example.test'\n",
            encoding="utf-8",
        )
        python_stub.chmod(0o755)
        self.calls = self.project / "calls.log"
        self.mocks = self.project / "mock_commands.sh"
        # Shell functions override real commands, even though the launcher prepends PATH.
        # No Mac service, browser, network endpoint, or delay is used by these tests.
        self.mocks.write_text(
            r"""
uname() { printf '%s\n' Darwin; }
sleep() {
    case "$TEST_CASE" in fallback_*) /bin/sleep 0.02 ;; *) : ;; esac
}
open() { printf 'open %s\n' "$*" >> "$TEST_CALLS"; }
launchctl() {
    printf 'launchctl %s\n' "$*" >> "$TEST_CALLS"
    case "$1" in
        print)
            case "$TEST_CASE" in fallback_*) code=78 ;; *) code=1 ;; esac
            printf '%s\n' 'state = exited' 'pid = 1234' "last exit code = $code" \
                'last terminating signal = Terminated: 15' 'environment = {' \
                '  PRIVATE_TOKEN = DO_NOT_DISPLAY_THIS_SECRET' '}'
            ;;
        bootout) touch service-unloaded ;;
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
            if [ "$TEST_CASE" = success ] || [ -f fallback-ready ]; then return 0; fi
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

    def run_launcher(self, scenario, mode="start"):
        result = subprocess.run(
            ["bash", str(self.project / "scripts" / "macos_launch.sh"), mode],
            env=self.launcher_environment(scenario),
            capture_output=True,
            text=True,
            timeout=10,
        )
        self.assertNotIn("MISSING_PROXY_BYPASS", result.stdout + result.stderr)
        return result

    def launcher_environment(self, scenario):
        environment = os.environ.copy()
        environment.update(BASH_ENV=str(self.mocks), TEST_CASE=scenario, TEST_CALLS=str(self.calls))
        return environment

    def start_fallback(self):
        process = subprocess.Popen(
            ["bash", str(self.project / "scripts" / "macos_launch.sh"), "start"],
            env=self.launcher_environment("fallback_success"),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        self.addCleanup(self.stop_launcher, process)
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            if self.calls.exists() and "open https://example.test" in self.calls.read_text(encoding="utf-8"):
                return process
            if process.poll() is not None:
                self.fail(str(process.communicate()))
            time.sleep(0.02)
        self.fail("The fallback did not open the public URL")

    @staticmethod
    def stop_launcher(process):
        if process.poll() is None:
            process.terminate()
        process.communicate(timeout=5)

    def test_config_failure_starts_direct_server_and_waits_for_it(self):
        process = self.start_fallback()
        self.assertTrue((self.project / "service-unloaded").exists())
        self.assertIsNone(process.poll(), "The launcher must keep the direct server alive")
        (self.project / "fallback-release").touch()
        stdout, stderr = process.communicate(timeout=5)
        self.assertEqual(process.returncode, 0, stdout + stderr)
        self.assertIn("利用中はこのターミナルを開いたまま", stdout)
        self.assertNotIn("閉じてもアプリは動き続けます", stdout)

    def test_stopping_launcher_stops_only_its_direct_server(self):
        process = self.start_fallback()
        child_pid = int((self.project / "fallback.pid").read_text())
        process.send_signal(signal.SIGTERM)
        process.communicate(timeout=5)
        self.assertEqual(process.returncode, 143)
        self.assertTrue((self.project / "fallback-stopped").exists())
        with self.assertRaises(ProcessLookupError):
            os.kill(child_pid, 0)

    def test_direct_server_failure_does_not_open_public_url(self):
        result = self.run_launcher("fallback_failure")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("DIRECT_START_ERROR", result.stdout)
        self.assertIn("直接起動にも失敗", result.stdout + result.stderr)
        self.assertNotIn("open https://", self.calls.read_text(encoding="utf-8"))

    def test_success_opens_public_url_without_showing_old_logs(self):
        result = self.run_launcher("success")
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        self.assertIn("起動確認が完了しました。公開URL：https://example.test", result.stdout)
        self.assertIn("open https://example.test", self.calls.read_text(encoding="utf-8"))
        self.assertNotIn("OLD_LOGIN_TRACEBACK", result.stdout)
        self.assertNotIn("launchctl kickstart", self.calls.read_text(encoding="utf-8"))

    def test_update_does_not_claim_old_manually_running_server_was_restarted(self):
        result = self.run_launcher("success", mode="updated")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("手動起動中のターミナルでControl + C", result.stderr)
        self.assertNotIn("open https://", self.calls.read_text(encoding="utf-8"))

    def test_connection_failure_shows_only_new_logs_and_filtered_service_state(self):
        result = self.run_launcher("new_error")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("ローカル接続確認に失敗しました（curl終了コード: 7、HTTP: 000）。", result.stdout)
        self.assertIn("logs/studyllm.err.log（今回の起動操作以降・最大30行）:", result.stdout)
        self.assertIn("logs/studyllm.out.log（今回の起動操作以降・最大30行）:", result.stdout)
        self.assertNotIn("unbound variable", result.stderr)
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
