import os
import shutil
import stat
import subprocess
import tempfile
import textwrap
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


class TestEasyLaunchers(unittest.TestCase):
    def test_shell_launcher_targets_easy_app_and_preserves_original_ui(self):
        launcher = (ROOT / "easy_webui.sh").read_text(encoding="utf-8")

        self.assertIn('webui/easy/App.py', launcher)
        self.assertNotIn('webui/Main.py', launcher)
        self.assertIn('.venv/bin/python', launcher)
        self.assertIn('command -v uv', launcher)
        self.assertIn('command -v streamlit', launcher)
        self.assertIn('range(8502, 8600)', launcher)

    def test_mac_command_is_thin_double_click_wrapper(self):
        command_path = ROOT / "MPT Easy.command"
        command = command_path.read_text(encoding="utf-8")

        self.assertIn('MPT_EASY_OPEN_BROWSER=1', command)
        self.assertIn('easy_webui.sh', command)
        self.assertTrue(command_path.stat().st_mode & stat.S_IXUSR)

    def test_windows_launcher_targets_easy_app(self):
        launcher = (ROOT / "easy_webui.bat").read_text(encoding="utf-8")

        self.assertIn(r'.\webui\easy\App.py', launcher)
        self.assertNotIn(r'.\webui\Main.py', launcher)
        self.assertIn(r'.venv\Scripts\python.exe', launcher)
        self.assertIn('uv run streamlit', launcher)
        self.assertIn('8502..8599', launcher)

    def test_shell_scripts_pass_syntax_check(self):
        for path in (ROOT / "easy_webui.sh", ROOT / "MPT Easy.command"):
            result = subprocess.run(
                ["/bin/sh", "-n", str(path)],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)

    def test_shell_launcher_uses_project_python_and_easy_entrypoint(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            shutil.copy2(ROOT / "easy_webui.sh", project / "easy_webui.sh")
            (project / "webui" / "easy").mkdir(parents=True)
            (project / "webui" / "easy" / "App.py").write_text("# smoke\n")
            (project / ".venv" / "bin").mkdir(parents=True)

            capture = project / "captured-args.txt"
            real_python = shutil.which("python3") or shutil.which("python")
            self.assertIsNotNone(real_python)

            fake_python = project / ".venv" / "bin" / "python"
            fake_python.write_text(
                textwrap.dedent(
                    f"""\
                    #!/bin/sh
                    if [ \"$1\" = \"-\" ]; then
                      exec {real_python} -
                    fi
                    printf '%s\\n' \"$@\" > \"{capture}\"
                    exit 0
                    """
                ),
                encoding="utf-8",
            )
            fake_python.chmod(0o755)

            env = os.environ.copy()
            env["MPT_EASY_OPEN_BROWSER"] = "0"
            env["MPT_EASY_PORT"] = "8587"
            result = subprocess.run(
                ["/bin/sh", str(project / "easy_webui.sh")],
                cwd=project,
                env=env,
                capture_output=True,
                text=True,
                timeout=10,
                check=False,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            args = capture.read_text(encoding="utf-8").splitlines()
            self.assertEqual(args[:3], ["-m", "streamlit", "run"])
            self.assertEqual(args[3], str(project / "webui" / "easy" / "App.py"))
            self.assertIn("--server.port=8587", args)
            self.assertIn("MPT Easy: http://127.0.0.1:8587", result.stdout)


if __name__ == "__main__":
    unittest.main()
