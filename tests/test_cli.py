import contextlib
import io
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from suye.cli import TOOLS, main


class DoctorTests(unittest.TestCase):
    def test_all_tools_available(self):
        output = io.StringIO()
        lookup = patch("suye.cli.shutil.which", return_value="/tool")
        with lookup, contextlib.redirect_stdout(output):
            self.assertEqual(main(["doctor"]), 0)
        self.assertEqual(output.getvalue(), "".join(f"[OK] {tool}\n" for tool in TOOLS))

    def test_missing_tool_and_no_secret_output(self):
        output = io.StringIO()
        lookup = patch("suye.cli.shutil.which", side_effect=["/git", "/python", None, "/rustc"])
        with lookup, contextlib.redirect_stdout(output):
            self.assertEqual(main(["doctor"]), 1)
        self.assertIn("[MISSING] cargo", output.getvalue())
        self.assertIn("[OK] rustc", output.getvalue())
        self.assertIn("PATH", output.getvalue())
        self.assertNotIn("/git", output.getvalue())

    def test_module_with_empty_tool_directory(self):
        with tempfile.TemporaryDirectory() as directory:
            environment = {**os.environ, "PATH": directory, "SUYE_SECRET": "must-not-appear"}
            result = subprocess.run(
                [sys.executable, "-m", "suye", "doctor"], env=environment,
                capture_output=True, text=True, check=False,
            )
            self.assertEqual(list(Path(directory).iterdir()), [])
        self.assertEqual(result.returncode, 1)
        self.assertEqual(result.stdout.count("[MISSING]"), 4)
        self.assertNotIn("must-not-appear", result.stdout + result.stderr)

    @unittest.skipUnless(os.name == "posix", "Unix executable permission checks")
    def test_executable_permissions_and_directories(self):
        with tempfile.TemporaryDirectory() as directory:
            for tool in TOOLS:
                executable = Path(directory, tool)
                executable.write_text("not an executable program", encoding="utf-8")
                executable.chmod(0o755)
            with patch.dict(os.environ, {"PATH": directory}):
                with contextlib.redirect_stdout(io.StringIO()):
                    self.assertEqual(main(["doctor"]), 0)
                Path(directory, "cargo").chmod(0o644)
                Path(directory, "rustc").unlink()
                Path(directory, "rustc").mkdir()
                output = io.StringIO()
                with contextlib.redirect_stdout(output):
                    self.assertEqual(main(["doctor"]), 1)
                self.assertIn("[MISSING] cargo", output.getvalue())
                self.assertIn("[MISSING] rustc", output.getvalue())

    def test_empty_or_unset_path(self):
        for environment in ({}, {"PATH": ""}):
            with patch.dict(os.environ, environment, clear=True):
                output = io.StringIO()
                with contextlib.redirect_stdout(output):
                    self.assertEqual(main(["doctor"]), 1)
                self.assertEqual(output.getvalue().count("[MISSING]"), 4)

    def test_help_version_and_invalid_arguments(self):
        cases = (
            (["--help"], 0), (["--version"], 0), ([], 2),
            (["unknown"], 2), (["doctor", "extra"], 2),
        )
        for arguments, status in cases:
            with self.subTest(arguments=arguments):
                with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                    with self.assertRaises(SystemExit) as error:
                        main(arguments)
                    self.assertEqual(error.exception.code, status)


if __name__ == "__main__":
    unittest.main()
