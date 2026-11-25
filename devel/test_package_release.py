"""配布ZIPの回帰テスト（独立した合成ファイルのみを使用）。"""

from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch
import zipfile

from package_release import REQUIRED_FILES, create_package, main


SCRIPT_DIR = Path(__file__).resolve().parent


class PackageReleaseTest(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory(prefix="caliboo package ")
        self.addCleanup(self.temp_dir.cleanup)
        self.root = Path(self.temp_dir.name) / "source with spaces"
        for relative in REQUIRED_FILES:
            path = self.root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("synthetic fixture", encoding="utf-8")
        for name in ("package_release.py", "build.sh"):
            shutil.copyfile(SCRIPT_DIR / name, self.root / "devel" / name)

    def write_fixture(self, relative):
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("synthetic fixture", encoding="utf-8")
        return path

    def build(self):
        return subprocess.run(
            ["bash", str(self.root / "devel/build.sh")],
            cwd=self.temp_dir.name, capture_output=True, text=True, check=False,
        )

    def test_clean_build_and_exclusions(self):
        included = ("backend/src/caliboo_api/example.py", "frontend/src/example.tsx")
        excluded = (
            "backend/var/caliboo.db", "backend/src/caliboo_api/local.sqlite-wal",
            "backend/src/caliboo_api/.env.fixture", "frontend/.env",
            "frontend/src/credentials/sample.ts", "frontend/src/.temp/cached.ts",
            "frontend/src/settings.local.ts", "backend/src/scratch/temporary.py",
            "backend/tests/unit/test_example.py", "backend/tests/integration/test_example.py",
            "frontend/src/example.spec.tsx", "frontend/src/example.impl.test.ts",
            "frontend/src/test/setup.ts", "devel/test_package_release.py",
            "frontend/node_modules/temporary.js", "devel/.temp/old.txt",
            "devel/poc_takeuchi/trace/report.json", ".claude/settings.local.json",
            ".devcontainer/ssh_config", "docs/poc-takeuchi-2026-09-29.md",
            "docs/poc-strength-profile-2026-09-29.md",
        )
        for relative in included + excluded:
            self.write_fixture(relative)

        result = self.build()
        self.assertEqual(result.returncode, 0, result.stderr)
        archive_path, = (self.root / "release").glob("*.zip")
        with zipfile.ZipFile(archive_path) as archive:
            self.assertIsNone(archive.testzip())
            names = set(archive.namelist())
            self.assertEqual(names, {f"Caliboo/{name}" for name in REQUIRED_FILES + included})
            archive.extractall(Path(self.temp_dir.name) / "extracted")
        self.assertTrue((Path(self.temp_dir.name) / "extracted/Caliboo/README.md").is_file())

    def test_optional_directories_absent(self):
        result = self.build()
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_missing_required_file_preserves_archive(self):
        previous = create_package(self.root)
        before = previous.read_bytes()
        (self.root / "frontend/package-lock.json").unlink()
        result = self.build()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("package-lock.json", result.stderr)
        self.assertNotIn("complete!", result.stdout)
        self.assertEqual(previous.read_bytes(), before)
        self.assertEqual(list(previous.parent.iterdir()), [previous])

    def test_compression_failure_preserves_archive(self):
        previous = create_package(self.root)
        before = previous.read_bytes()
        stdout = StringIO()
        stderr = StringIO()
        with (
            patch(
                "package_release.zipfile.ZipFile.write",
                side_effect=OSError("synthetic failure"),
            ),
            patch("sys.argv", ["package_release.py", str(self.root)]),
            redirect_stdout(stdout),
            redirect_stderr(stderr),
        ):
            self.assertEqual(main(), 1)
        self.assertNotIn("complete!", stdout.getvalue())
        self.assertIn("synthetic failure", stderr.getvalue())
        self.assertEqual(previous.read_bytes(), before)
        self.assertEqual(list(previous.parent.iterdir()), [previous])

    def test_archive_validation_failure_preserves_archive(self):
        previous = create_package(self.root)
        before = previous.read_bytes()
        with patch(
            "package_release.zipfile.ZipFile.testzip", return_value="bad file",
        ):
            with self.assertRaises(ValueError):
                create_package(self.root)
        self.assertEqual(previous.read_bytes(), before)
        self.assertEqual(list(previous.parent.iterdir()), [previous])

    def test_source_link_preserves_archive(self):
        previous = create_package(self.root)
        before = previous.read_bytes()
        external = Path(self.temp_dir.name) / "synthetic-external.py"
        external.write_text("synthetic fixture", encoding="utf-8")
        link = self.root / "backend/src/caliboo_api/linked.py"
        try:
            link.symlink_to(external)
        except OSError:
            self.skipTest("この環境ではシンボリックリンクを作成できません")
        result = self.build()
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(previous.read_bytes(), before)
        self.assertEqual(list(previous.parent.iterdir()), [previous])

    def test_success_replaces_previous_archive_without_stale_entries(self):
        old = self.write_fixture("backend/src/caliboo_api/obsolete.py")
        previous = create_package(self.root)
        old.unlink()
        self.assertEqual(create_package(self.root), previous)
        with zipfile.ZipFile(previous) as archive:
            self.assertNotIn("Caliboo/backend/src/caliboo_api/obsolete.py", archive.namelist())


if __name__ == "__main__":
    unittest.main()
