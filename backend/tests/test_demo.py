from code_review.demo import run_demo_reviewer
from code_review.samples import get_sample

from .conftest import VULNERABLE


def titles(findings):
    return [f.title for f in findings]


def test_security_rules_find_sql_injection_and_secret_with_correct_lines():
    findings = run_demo_reviewer("security", VULNERABLE, "python", "snippet.py")
    by_line = {f.line: f for f in findings}
    assert "api_key" in by_line[2].title and by_line[2].severity == "critical"
    assert "SQL" in by_line[4].title and by_line[4].severity == "critical"


def test_demo_is_deterministic():
    a = run_demo_reviewer("security", VULNERABLE, "python", "snippet.py")
    b = run_demo_reviewer("security", VULNERABLE, "python", "snippet.py")
    assert [f.model_dump() for f in a] == [f.model_dump() for f in b]


def test_findings_sorted_by_severity_then_line():
    sample = get_sample("python-user-service")
    findings = run_demo_reviewer("maintainability", sample.code, "python", "x.py")
    order = {"critical": 0, "warn": 1, "info": 2}
    keys = [(order[f.severity], f.line or 0) for f in findings]
    assert keys == sorted(keys)


def test_python_sample_covers_expected_maintainability_problems():
    sample = get_sample("python-user-service")
    findings = run_demo_reviewer("maintainability", sample.code, "python", "x.py")
    joined = " | ".join(titles(findings))
    assert "Undefined name `math`" in joined
    assert "duplicates" in joined
    assert "Swallowed or overly broad exception handler" in joined
    assert "Unused import `sys`" in joined


def test_clean_sample_has_no_findings():
    sample = get_sample("python-clean-module")
    for reviewer in ("security", "maintainability"):
        assert run_demo_reviewer(reviewer, sample.code, "python", "clean.py") == []


def test_javascript_rules():
    sample = get_sample("javascript-comment-widget")
    sec = " | ".join(titles(run_demo_reviewer("security", sample.code, "javascript", "w.js")))
    assert "eval" in sec and "Unescaped HTML" in sec and "Hardcoded secret" in sec
    main = " | ".join(titles(run_demo_reviewer("maintainability", sample.code, "javascript", "w.js")))
    assert "Empty catch" in main and "`var`" in main


def test_python_only_checks_do_not_run_on_other_languages():
    code = "import os\nvar x = 1\n"
    findings = run_demo_reviewer("maintainability", code, "javascript", "a.js")
    assert not any("Unused import" in t for t in titles(findings))


def test_python_syntax_error_is_reported_not_raised():
    findings = run_demo_reviewer("maintainability", "def broken(:\n    pass\n", "python", "bad.py")
    assert findings[0].title == "Syntax error"
    assert findings[0].line == 1


def test_no_false_positive_for_numbers_or_keywords_inside_strings():
    code = 'message = "call eval(x) or wait 1234567 ms"\n'
    assert run_demo_reviewer("security", code, "python", "a.py") == []
    assert not any("Magic" in t for t in titles(run_demo_reviewer("maintainability", code, "python", "a.py")))


def test_placeholder_secrets_and_comments_are_ignored():
    code = 'api_key = "your-api-key-here"\n# password = "hunter2hunter2"\n'
    assert run_demo_reviewer("security", code, "python", "a.py") == []


def test_parameterized_query_is_not_flagged():
    code = 'cur.execute("SELECT * FROM users WHERE name = ?", (name,))\n'
    assert run_demo_reviewer("security", code, "python", "a.py") == []


def test_same_rule_is_capped_to_avoid_floods():
    code = "\n".join(f'password{i} = "secretvalue{i}"' for i in range(30))
    assert len(run_demo_reviewer("security", code, "python", "a.py")) == 5
