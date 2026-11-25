"""限定試用エクスポートの通常の選別・再生成・出力管理。"""

import hashlib
import subprocess
import zipfile

import pytest

from package_trial import (MANIFEST, REQUIRED_FILES, SOURCE_ARCHIVE,
                           create_package, parse_manifest)


def commit(root):
    subprocess.run(["git", "-C", str(root), "add", "."], check=True)
    subprocess.run(["git", "-C", str(root), "-c", "user.name=trial test",
                    "-c", "user.email=trial-test@example.invalid", "commit", "-qm", "test"],
                   check=True)


@pytest.fixture
def checkout(tmp_path):
    root = tmp_path / "repo"
    root.mkdir()
    subprocess.run(["git", "-C", str(root), "init", "-q"], check=True)
    for path in REQUIRED_FILES:
        file = root / path
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_text("synthetic source", encoding="utf-8")
    (root / MANIFEST).write_text("\n".join(sorted(REQUIRED_FILES)) + "\n", encoding="utf-8")
    # 許可対象外の作業用ファイル。機密値は一切使用しない。
    for path in ("devel/poc/trace/sample.json", "backend/var/sample.sqlite",
                 "frontend/src/NotReviewed.ts"):
        file = root / path
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_text("synthetic excluded", encoding="utf-8")
    commit(root)
    return root


def test_package_committed_snapshot_only(checkout, tmp_path):
    file = checkout / "frontend/src/App.tsx"
    file.write_text("uncommitted synthetic", encoding="utf-8")
    (checkout / "temporary.log").write_text("synthetic excluded", encoding="utf-8")
    first = tmp_path / "first"
    second = tmp_path / "second"
    commit1, digest1, count = create_package(checkout, "HEAD", first)
    commit2, digest2, _count2 = create_package(checkout, "HEAD", second)
    assert commit1 == commit2 and digest1 == digest2
    assert count == len(REQUIRED_FILES)
    assert hashlib.sha256((first / SOURCE_ARCHIVE).read_bytes()).hexdigest() == digest1
    expected = sorted(REQUIRED_FILES)
    with zipfile.ZipFile(first / SOURCE_ARCHIVE) as archive:
        assert archive.namelist() == expected
        for path in expected:
            assert archive.read(path) == (first / "source" / path).read_bytes()
        assert archive.read("frontend/src/App.tsx") == b"synthetic source"
    assert sorted(file.relative_to(first / "source").as_posix()
                  for file in (first / "source").rglob("*") if file.is_file()) == expected


def test_existing_output_remains_untouched(checkout, tmp_path):
    output = tmp_path / "existing"
    output.mkdir()
    marker = output / "existing.txt"
    marker.write_text("keep", encoding="utf-8")
    with pytest.raises(ValueError):
        create_package(checkout, "HEAD", output)
    assert marker.read_text(encoding="utf-8") == "keep"


def test_required_source_must_be_present_in_commit(checkout, tmp_path):
    (checkout / "frontend/src/App.tsx").unlink()
    commit(checkout)
    output = tmp_path / "missing"
    with pytest.raises(ValueError):
        create_package(checkout, "HEAD", output)
    assert not output.exists()


@pytest.mark.parametrize("extra", ["backend/var/sample.sqlite", "devel/poc/trace/sample.json",
                                   "frontend/src/example.test.ts", "frontend/src/public/file.ts"])
def test_manifest_disallows_non_source(extra):
    value = "\n".join([*sorted(REQUIRED_FILES), extra])
    with pytest.raises(ValueError):
        parse_manifest(value.encode("utf-8"))


def test_symlink_source_is_not_packaged(checkout, tmp_path):
    file = checkout / "frontend/src/App.tsx"
    file.unlink()
    file.symlink_to("main.tsx")
    commit(checkout)
    output = tmp_path / "symlink"
    with pytest.raises(ValueError):
        create_package(checkout, "HEAD", output)
    assert not output.exists()
