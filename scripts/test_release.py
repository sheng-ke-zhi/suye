from pathlib import Path
import tempfile
import unittest

from check_release import check


class ReleaseChecks(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        (self.root / "python/suye").mkdir(parents=True)
        (self.root / "python/suye/__init__.py").write_text('__version__ = "0.1.0"\n')
        (self.root / "setup.cfg").write_text('[metadata]\nversion = 0.1.0\n')
        (self.root / "Cargo.toml").write_text('[package]\nversion = "0.1.0"\npublish = false\n')

    def approve_fixture(self):
        (self.root / "setup.cfg").write_text('[metadata]\nversion = 0.1.0\nlicense = MIT\n')
        (self.root / "Cargo.toml").write_text(
            '[package]\nversion = "0.1.0"\nlicense = "MIT"\npublish = ["crates-io"]\n'
        )
        (self.root / "LICENSE").write_text('Synthetic test fixture, not the project license.\n')

    def test_unreleased_project_can_build_but_not_publish(self):
        self.assertEqual(check(self.root, "v0.1.0"), "0.1.0")
        with self.assertRaisesRegex(ValueError, "user-approved"):
            check(self.root, "v0.1.0", publish=True)

    def test_version_mismatch(self):
        for filename in ("setup.cfg", "Cargo.toml", "python/suye/__init__.py"):
            path = self.root / filename
            original = path.read_text()
            with self.subTest(filename=filename):
                path.write_text(original.replace("0.1.0", "0.2.0"))
                with self.assertRaisesRegex(ValueError, "must match"):
                    check(self.root)
                path.write_text(original)

    def test_tag_mismatch(self):
        for tag in ("", "0.1.0", "v0.2.0", "main", "v0.1.0; echo unsafe"):
            with self.subTest(tag=tag), self.assertRaisesRegex(ValueError, "release tag"):
                check(self.root, tag)

    def test_approved_metadata(self):
        self.approve_fixture()
        self.assertEqual(check(self.root, "v0.1.0", publish=True), "0.1.0")
        with self.assertRaisesRegex(ValueError, "explicit version tag"):
            check(self.root, publish=True)

    def test_missing_license_text(self):
        self.approve_fixture()
        (self.root / "LICENSE").unlink()
        with self.assertRaisesRegex(ValueError, "license text"):
            check(self.root, "v0.1.0", publish=True)

    def test_blank_or_mismatched_license(self):
        self.approve_fixture()
        (self.root / "LICENSE").write_text(" \n")
        with self.assertRaisesRegex(ValueError, "license text"):
            check(self.root, "v0.1.0", publish=True)
        self.approve_fixture()
        path = self.root / "Cargo.toml"
        path.write_text(path.read_text().replace('"MIT"', '"Apache-2.0"'))
        with self.assertRaisesRegex(ValueError, "SPDX"):
            check(self.root, "v0.1.0", publish=True)

    def test_publish_disabled(self):
        self.approve_fixture()
        path = self.root / "Cargo.toml"
        path.write_text(path.read_text().replace('["crates-io"]', "false"))
        with self.assertRaisesRegex(ValueError, "publish ="):
            check(self.root, "v0.1.0", publish=True)


if __name__ == "__main__":
    unittest.main()
