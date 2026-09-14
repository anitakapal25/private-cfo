"""Git metadata must prove local environment files are safe to exempt."""
import importlib.util
from pathlib import Path
import subprocess


spec = importlib.util.spec_from_file_location(
    "repository_guardrails",
    Path(__file__).resolve().parents[2] / "scripts/check_repository_guardrails.py",
)
guardrails = importlib.util.module_from_spec(spec)
spec.loader.exec_module(guardrails)


def test_only_ignored_untracked_environment_is_exempt(tmp_path):
    subprocess.run(["git", "init", "--quiet", str(tmp_path)], check=True)
    (tmp_path / ".env").write_text("# synthetic fixture\n")
    assert not guardrails.is_ignored_local_file(tmp_path, ".env")
    (tmp_path / ".gitignore").write_text(".env\n")
    assert guardrails.is_ignored_local_file(tmp_path, ".env")
    subprocess.run(["git", "add", "--force", ".env"], cwd=tmp_path, check=True)
    assert not guardrails.is_ignored_local_file(tmp_path, ".env")


def test_missing_git_metadata_fails_closed(tmp_path):
    (tmp_path / ".env").write_text("# synthetic fixture\n")
    assert not guardrails.is_ignored_local_file(tmp_path, ".env")


def test_local_virtual_environment_is_not_scanned(tmp_path, monkeypatch):
    package = tmp_path / ".venv" / "lib" / "example.py"
    package.parent.mkdir(parents=True)
    package.write_text("synthetic third-party package\n")
    monkeypatch.setattr(guardrails, "ROOT", tmp_path)

    assert list(guardrails.iter_text_files()) == []
