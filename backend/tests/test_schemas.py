import pytest
from pydantic import ValidationError

from code_review.schemas import Finding, ReviewRequest, ReviewResult

from .fakes import finding


def test_finding_normalizes_path_severity_and_category():
    f = Finding(**finding(path=" ./src\\app.py ", severity="HIGH", category=" Security "))
    assert f.path == "src/app.py"
    assert f.severity == "critical"
    assert f.category == "security"


@pytest.mark.parametrize(
    ("raw", "expected"), [("warning", "warn"), ("medium", "warn"), ("low", "info"), ("severe", "critical")]
)
def test_severity_aliases(raw, expected):
    assert Finding(**finding(severity=raw)).severity == expected


@pytest.mark.parametrize(("raw", "expected"), [("7", 7), (7.0, 7), (0, None), (-3, None), (True, None), (None, None)])
def test_line_coercion(raw, expected):
    assert Finding(**finding(line=raw)).line == expected


@pytest.mark.parametrize("field", ["title", "description", "why_it_matters", "suggestion", "path"])
def test_required_text_fields_reject_blank(field):
    with pytest.raises(ValidationError):
        Finding(**finding(**{field: "   "}))


def test_unknown_severity_and_extra_fields_rejected():
    with pytest.raises(ValidationError):
        Finding(**finding(severity="catastrophic"))
    with pytest.raises(ValidationError):
        Finding(**finding(extra="nope"))


def test_review_result_requires_findings_list():
    with pytest.raises(ValidationError):
        ReviewResult.model_validate({"results": []})
    assert ReviewResult.model_validate({"findings": []}).findings == []


def test_request_defaults_to_demo_with_both_reviewers():
    req = ReviewRequest(code="x = 1")
    assert req.mode == "demo"
    assert req.reviewers == ["security", "maintainability"]
    assert req.language == "python"


def test_request_filename_is_reduced_to_a_label():
    assert ReviewRequest(code="x", filename="../../etc/passwd").filename == "passwd"
    assert ReviewRequest(code="x", filename="C:\\Users\\me\\app.py").filename == "app.py"
    assert ReviewRequest(code="x", filename="   ").filename is None


def test_request_dedupes_reviewers_and_rejects_unknown_values():
    assert ReviewRequest(code="x", reviewers=["security", "security"]).reviewers == ["security"]
    with pytest.raises(ValidationError):
        ReviewRequest(code="x", reviewers=[])
    with pytest.raises(ValidationError):
        ReviewRequest(code="x", reviewers=["performance"])
    with pytest.raises(ValidationError):
        ReviewRequest(code="x", language="brainfuck")
    with pytest.raises(ValidationError):
        ReviewRequest(code="x", mode="turbo")
    with pytest.raises(ValidationError):
        ReviewRequest(code="x", unexpected=True)
