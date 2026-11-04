"""The CLI-only code tools must never read secrets or escape the repository."""

import os

import pytest

from code_review import tools


@pytest.fixture
def repo(tmp_path, monkeypatch):
    (tmp_path / "app.py").write_text("print('hi')\nline2\n", encoding="utf-8")
    (tmp_path / ".env").write_text("API_KEY=real-secret\n", encoding="utf-8")
    (tmp_path / ".env.example").write_text("API_KEY=your-key\n", encoding="utf-8")
    (tmp_path / "server.pem").write_text("-----BEGIN PRIVATE KEY-----\n", encoding="utf-8")
    (tmp_path / "id_rsa").write_text("secret", encoding="utf-8")
    (tmp_path / ".git").mkdir()
    (tmp_path / ".git" / "config").write_text("[core]\n", encoding="utf-8")
    outside = tmp_path.parent / "outside-secret.txt"
    outside.write_text("TOP-SECRET-CONTENT", encoding="utf-8")
    monkeypatch.setattr(tools, "REPO_ROOT", os.path.realpath(tmp_path))
    return tmp_path


def test_reads_normal_files_with_line_numbers(repo):
    out = tools.read_file("app.py", 1, 1)
    assert "1 | print('hi')" in out and "line2" not in out


@pytest.mark.parametrize("name", [".env", "server.pem", "id_rsa", ".git/config", "sub/../.env"])
def test_refuses_secret_files(repo, name):
    out = tools.read_file(name)
    assert out.startswith("ERROR") and "real-secret" not in out


def test_env_example_is_allowed(repo):
    assert "your-key" in tools.read_file(".env.example")


@pytest.mark.parametrize("path", ["../outside-secret.txt", "..\\outside-secret.txt", "sub/../../outside-secret.txt"])
def test_refuses_path_traversal(repo, path):
    out = tools.read_file(path)
    assert out.startswith("ERROR") and "TOP-SECRET-CONTENT" not in out


def test_refuses_absolute_paths_outside_repo(repo):
    outside = os.path.join(os.path.dirname(str(repo)), "outside-secret.txt")
    assert tools.read_file(outside).startswith("ERROR")


def test_refuses_symlink_escape(repo):
    link = repo / "link.txt"
    try:
        os.symlink(str(repo.parent / "outside-secret.txt"), str(link))
    except (OSError, NotImplementedError):
        pytest.skip("symlinks not permitted on this system")
    assert tools.read_file("link.txt").startswith("ERROR")


@pytest.mark.parametrize(("start", "end"), [(0, None), (-1, 2), (5, 2), ("1", None), (True, None)])
def test_validates_line_numbers(repo, start, end):
    assert tools.read_file("app.py", start, end).startswith("ERROR")


def test_missing_file_and_directory_errors(repo):
    assert "not found" in tools.read_file("nope.py")
    assert "directory" in tools.read_file(".")


def test_ripgrep_rejects_empty_and_oversized_patterns():
    assert tools.ripgrep("").startswith("ERROR")
    assert tools.ripgrep("x" * 500).startswith("ERROR")
