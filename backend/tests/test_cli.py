import json
import subprocess
import sys

import pytest

from code_review import cli

from .conftest import VULNERABLE
from .fakes import FakeClient, finding, reply


@pytest.fixture(autouse=True)
def no_ambient_key(monkeypatch):
    for name in ("LLM_API_KEY", "OPENROUTER_API_KEY"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setattr("code_review.config.load_dotenv", lambda *a, **k: None)


@pytest.fixture
def source(tmp_path):
    path = tmp_path / "app.py"
    path.write_text(VULNERABLE, encoding="utf-8")
    return path


def run_cli(*args):
    cli.main(list(args))


def test_demo_json_report(source, tmp_path, capsys):
    out = tmp_path / "report.json"
    run_cli("--demo", "--file", str(source), "--format", "json", "--output", str(out))
    report = json.loads(out.read_text(encoding="utf-8"))
    assert report["is_demo"] is True and report["summary"]["total"] > 0
    printed = capsys.readouterr().out
    assert "engine: demo" in printed and "Report saved to" in printed


def test_demo_html_report_is_default_format(source, tmp_path):
    out = tmp_path / "report.html"
    run_cli("--demo", "--file", str(source), "--output", str(out), "--reviewers", "security")
    html = out.read_text(encoding="utf-8")
    assert (
        html.startswith("<!DOCTYPE html>")
        and "Demo report" in html
        and "Maintainability" not in html.split("<h2>Reviewers")[1].split("</table>")[0]
    )


def exit_message(excinfo, capsys):
    assert excinfo.value.code == 1
    return capsys.readouterr().err


def test_missing_file_has_a_clear_error(tmp_path, capsys):
    with pytest.raises(SystemExit) as exc:
        run_cli("--demo", "--file", str(tmp_path / "missing.py"), "--output", str(tmp_path / "o.html"))
    assert "file not found" in exit_message(exc, capsys)


def test_empty_file_is_rejected(tmp_path, capsys):
    empty = tmp_path / "e.py"
    empty.write_text("  \n", encoding="utf-8")
    with pytest.raises(SystemExit) as exc:
        run_cli("--demo", "--file", str(empty), "--output", str(tmp_path / "o.html"))
    assert "empty" in exit_message(exc, capsys)


def test_binary_file_is_rejected(tmp_path, capsys):
    binary = tmp_path / "b.bin"
    binary.write_bytes(b"\xff\xfe\x00\x80")
    with pytest.raises(SystemExit) as exc:
        run_cli("--demo", "--file", str(binary), "--output", str(tmp_path / "o.html"))
    assert "not a UTF-8 text file" in exit_message(exc, capsys)


def test_unknown_reviewer_is_rejected(source, tmp_path, capsys):
    with pytest.raises(SystemExit) as exc:
        run_cli("--demo", "--file", str(source), "--reviewers", "speed", "--output", str(tmp_path / "o.html"))
    assert "unknown reviewer" in exit_message(exc, capsys)


def test_output_folder_must_exist(source, tmp_path, capsys):
    with pytest.raises(SystemExit) as exc:
        run_cli("--demo", "--file", str(source), "--output", str(tmp_path / "nope" / "o.html"))
    assert "does not exist" in exit_message(exc, capsys)


def test_live_review_without_key_explains_how_to_fix_it(source, tmp_path, capsys):
    with pytest.raises(SystemExit) as exc:
        run_cli("--file", str(source), "--output", str(tmp_path / "o.html"))
    message = exit_message(exc, capsys)
    assert "LLM_API_KEY" in message and "--demo" in message


def test_live_review_with_mocked_provider(source, tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("LLM_API_KEY", "sk-live-abcdef123456")
    client = FakeClient([reply(finding(path="snippet.py")), reply()])
    monkeypatch.setattr(cli, "create_client", lambda settings, key: client)
    out = tmp_path / "live.json"
    run_cli("--file", str(source), "--no-tools", "--format", "json", "--output", str(out))
    # The finding names a path that is not part of the review, so it is dropped and reported.
    report = json.loads(out.read_text(encoding="utf-8"))
    assert report["is_demo"] is False and report["mode"] == "live"
    assert any("discarded" in n for n in report["notices"])
    assert "sk-live-abcdef123456" not in capsys.readouterr().out + out.read_text(encoding="utf-8")
    assert client.closed


def test_staged_diff_mode_in_a_real_git_repo(tmp_path, monkeypatch, capsys):
    def git(*a):
        subprocess.run(["git", *a], cwd=tmp_path, check=True, capture_output=True)

    git("init")
    git("config", "user.email", "t@example.com")
    git("config", "user.name", "t")
    (tmp_path / "a.py").write_text("x = 1\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("LLM_API_KEY", "sk-live-abcdef123456")

    with pytest.raises(SystemExit) as exc:  # nothing staged yet
        run_cli("--output", str(tmp_path / "o.html"))
    assert "No staged changes" in exit_message(exc, capsys)

    git("add", "a.py")
    client = FakeClient([reply(finding(path="a.py", line=1, category="naming")), reply()])
    monkeypatch.setattr(cli, "create_client", lambda settings, key: client)
    run_cli("--no-tools", "--format", "json", "--output", str(tmp_path / "o.json"))
    report = json.loads((tmp_path / "o.json").read_text(encoding="utf-8"))
    assert report["findings"][0]["path"] == "a.py" and report["findings"][0]["line"] == 1
    assert "git diff --staged" in capsys.readouterr().out


def test_demo_cannot_be_combined_with_git_mode(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    with pytest.raises(SystemExit) as exc:
        run_cli("--demo", "--output", str(tmp_path / "o.html"))
    assert "--demo reviews whole files" in exit_message(exc, capsys)


def test_module_entry_point_prints_help():
    result = subprocess.run([sys.executable, "-m", "code_review", "--help"], capture_output=True, text=True)
    assert result.returncode == 0 and "--demo" in result.stdout and "--file" in result.stdout
