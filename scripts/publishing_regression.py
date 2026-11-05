import configparser
import os
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
import unittest

from check_release import check


class PublishingRegression(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        temporary = Path(self.temporary.name)
        root = Path(__file__).resolve().parents[1]
        self.version = check(root)
        self.source = temporary / "source"
        self.source.mkdir()
        for filename in ("Cargo.toml", "Cargo.lock", "README.md", "setup.cfg"):
            shutil.copy2(root / filename, self.source / filename)
        for directory in ("src", "tests", "python"):
            shutil.copytree(root / directory, self.source / directory)
        manifest = self.source / "Cargo.toml"
        contents = re.sub(r"(?m)^(?:publish|license)\s*=.*$", "", manifest.read_text())
        manifest.write_text(contents.replace(
            "[package]", '[package]\npublish = ["crates-io"]\nlicense = "MIT"', 1
        ))
        configuration = configparser.ConfigParser()
        configuration.read(self.source / "setup.cfg")
        configuration["metadata"]["license"] = "MIT"
        with (self.source / "setup.cfg").open("w") as destination:
            configuration.write(destination)
        (self.source / "LICENSE").write_text("Synthetic regression fixture, not the project license.\n")
        self.home = temporary / "home"
        self.home.mkdir()
        self.cargo_home = temporary / "cargo-home"
        self.cargo_home.mkdir()
        self.environment = {
            "HOME": str(self.home),
            "CARGO_HOME": str(self.cargo_home),
            "RUSTUP_HOME": os.environ.get("RUSTUP_HOME", str(Path.home() / ".rustup")),
            "PATH": os.environ["PATH"],
            "CARGO_NET_RETRY": "0",
            "CARGO_HTTP_TIMEOUT": "30",
        }
        for name in ("HTTPS_PROXY", "HTTP_PROXY", "ALL_PROXY", "NO_PROXY"):
            if name in os.environ:
                self.environment[name] = os.environ[name]
        workflow = (root / ".github/workflows/release.yml").read_text()
        step = re.search(
            r"(?m)^      - name: Cargo publishing preflight\n        if: (.+)\n        run: (.+)$",
            workflow,
        )
        self.assertIsNotNone(step, "Keep the Cargo preflight explicit and directly testable.")
        self.condition, command = step.groups()
        self.command = shlex.split(command)
        self.assertEqual(self.command[:3], ["cargo", "+stable", "publish"])
        self.assertIn("--dry-run", self.command)
        self.assertNotIn("--token", self.command)
        self.workflow = workflow

    def run_command(self, command):
        result = subprocess.run(
            command, cwd=self.source, env=self.environment,
            capture_output=True, text=True, timeout=120,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return result

    def test_pypi_only_skips_cargo_publishing_preflight(self):
        self.assertEqual(
            self.condition,
            "github.event_name == 'workflow_dispatch' && inputs.publish && "
            "(inputs.target == 'both' || inputs.target == 'crates')",
        )
        self.assertIn(
            "      - name: Publishing path regressions\n"
            "        if: github.event_name != 'workflow_dispatch' || inputs.target != 'pypi'\n"
            "        run: python scripts/publishing_regression.py",
            self.workflow,
        )

    def test_approved_release_preflight_with_empty_cargo_cache(self):
        self.assertEqual(check(self.source, f"v{self.version}", publish=True), self.version)
        self.assertEqual(list(self.home.iterdir()), [])
        self.assertEqual(list(self.cargo_home.iterdir()), [])
        self.run_command(["cargo", "+stable", "test", "--locked", "--offline"])
        self.run_command(["cargo", "+stable", "package", "--locked", "--offline"])
        self.assertEqual(list(self.cargo_home.glob("registry/**/config.json")), [])
        self.run_command(self.command)
        self.assertTrue(list(self.cargo_home.glob("registry/**/config.json")))

    def test_next_version_passes_release_and_cli_tests(self):
        major, minor, patch = map(int, self.version.split("."))
        next_version = f"{major}.{minor}.{patch + 1}"
        for filename in ("Cargo.toml", "setup.cfg", "python/suye/__init__.py"):
            path = self.source / filename
            path.write_text(path.read_text().replace(self.version, next_version))
        self.assertEqual(check(self.source, f"v{next_version}", publish=True), next_version)
        self.run_command(["cargo", "+stable", "generate-lockfile", "--offline"])
        self.run_command(["cargo", "+stable", "test", "--locked", "--offline"])
        self.environment["PYTHONPATH"] = str(self.source / "python")
        result = self.run_command([sys.executable, "-m", "suye", "--version"])
        self.assertEqual(result.stdout, f"suye {next_version}\n")


if __name__ == "__main__":
    unittest.main()
