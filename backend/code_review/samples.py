"""Safe, bundled sample files for the web UI.

Clients choose a sample by id from a fixed allow-list. A request can never name a path, so
this endpoint cannot be used to read arbitrary files from the server.
"""

from pathlib import Path

from .errors import InvalidInputError
from .schemas import Sample, SampleSummary

_DIR = Path(__file__).parent / "sample_files"

# id -> (title, language, filename on disk, description)
_SAMPLES = {
    "python-user-service": (
        "Python: user service",
        "python",
        "user_service.py",
        "SQL injection, hardcoded credentials, duplicated logic, a swallowed exception and an undefined name.",
    ),
    "javascript-comment-widget": (
        "JavaScript: comment widget",
        "javascript",
        "comment_widget.js",
        "innerHTML with user text, eval(), a leaked password in a log and an empty catch block.",
    ),
    "python-clean-module": (
        "Python: clean module",
        "python",
        "clean_module.py",
        "A tidy dataclass-based module, to see what an empty result looks like.",
    ),
}


def list_samples() -> list[SampleSummary]:
    return [
        SampleSummary(id=sid, title=title, language=lang, filename=name, description=desc)
        for sid, (title, lang, name, desc) in _SAMPLES.items()
    ]


def get_sample(sample_id: str) -> Sample:
    entry = _SAMPLES.get(sample_id)
    if entry is None:
        raise InvalidInputError(f"Unknown sample '{sample_id[:40]}'.", code="sample_not_found")
    title, language, filename, description = entry
    code = (_DIR / filename).read_text(encoding="utf-8")
    return Sample(id=sample_id, title=title, language=language, filename=filename, description=description, code=code)
