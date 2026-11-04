"""Report generation: a JSON document and a standalone HTML page.

The HTML is built here from structured data and every value is escaped, so findings (which are
derived from untrusted code and model output) can never inject markup or script. A strict
Content-Security-Policy meta tag is added as a second layer. The original assignment had an LLM
write the HTML and then sanitized it; generating it deterministically is simpler and safer.
"""

import html
import json
from datetime import datetime

from .schemas import SEVERITY_ORDER, ApiFinding, ReviewResponse

SEVERITY_LABEL = {"critical": "Critical", "warn": "Warning", "info": "Info"}

CSP = (
    '<meta http-equiv="Content-Security-Policy" '
    "content=\"default-src 'none'; style-src 'unsafe-inline'; base-uri 'none'; form-action 'none'\">"
)

STYLE = """
:root{color-scheme:light dark;--bg:#0b1220;--panel:#111a2e;--line:#22304d;--text:#e6edf7;--muted:#93a4c0;--accent:#2dd4bf;--crit:#f87171;--warn:#fbbf24;--info:#60a5fa}
@media (prefers-color-scheme:light){:root{--bg:#f6f8fb;--panel:#fff;--line:#d8e0ec;--text:#0f1b2d;--muted:#52627d;--accent:#0f766e;--crit:#b91c1c;--warn:#a16207;--info:#1d4ed8}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--text);font:15px/1.55 system-ui,-apple-system,"Segoe UI",sans-serif}
main{max-width:920px;margin:0 auto;padding:32px 20px 64px}h1{font-size:1.5rem;margin:0 0 4px}h2{font-size:1.05rem;margin:32px 0 12px}
.muted{color:var(--muted)}.banner{border:1px solid var(--warn);border-left-width:4px;border-radius:6px;padding:10px 14px;margin:16px 0;background:var(--panel)}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(130px,1fr));gap:10px;margin:16px 0}
.stat{background:var(--panel);border:1px solid var(--line);border-radius:6px;padding:12px 14px}.stat b{display:block;font-size:1.6rem}
.finding{background:var(--panel);border:1px solid var(--line);border-radius:6px;padding:14px 16px;margin:12px 0}
.finding h3{margin:0 0 6px;font-size:1rem}.tag{display:inline-block;font-size:.75rem;font-weight:600;border:1px solid currentColor;border-radius:4px;padding:1px 7px;margin-right:6px}
.critical{color:var(--crit)}.warn{color:var(--warn)}.info{color:var(--info)}
dt{font-weight:600;margin-top:8px}dd{margin:2px 0 0}code,pre{font-family:ui-monospace,Consolas,monospace;font-size:.85em}
code{background:rgba(127,127,127,.15);padding:1px 4px;border-radius:3px}pre{white-space:pre-wrap}
table{border-collapse:collapse;width:100%}td,th{text-align:left;padding:6px 8px;border-bottom:1px solid var(--line)}
"""


def _e(value: object) -> str:
    return html.escape(str(value), quote=True)


def render_json(review: ReviewResponse) -> str:
    return json.dumps(review.model_dump(mode="json"), indent=2, ensure_ascii=False) + "\n"


def _where(finding: ApiFinding) -> str:
    return finding.path if finding.line is None else f"{finding.path}:{finding.line}"


def _finding_html(finding: ApiFinding) -> str:
    return (
        '<article class="finding">'
        f'<h3><span class="tag {finding.severity}">{_e(SEVERITY_LABEL[finding.severity])}</span>{_e(finding.title)}</h3>'
        f'<div class="muted">{_e(finding.id)} &middot; {_e(finding.reviewer)} &middot; {_e(finding.category)}'
        f" &middot; <code>{_e(_where(finding))}</code></div>"
        "<dl>"
        f"<dt>What is wrong</dt><dd>{_e(finding.description)}</dd>"
        f"<dt>Why it matters</dt><dd>{_e(finding.why_it_matters)}</dd>"
        f"<dt>Suggested improvement</dt><dd>{_e(finding.suggestion)}</dd>"
        "</dl></article>"
    )


def _timestamp(value: datetime) -> str:
    return value.strftime("%Y-%m-%d %H:%M UTC")


def render_html(review: ReviewResponse) -> str:
    """A self-contained HTML report (no scripts, no external requests)."""
    s = review.summary
    banner = ""
    if review.is_demo:
        banner = (
            '<div class="banner"><b>Demo report.</b> These findings were produced by a deterministic '
            "rule-based scanner, not by an AI model.</div>"
        )
    notices = "".join(
        f'<div class="banner">{_e(n)}</div>' for n in review.notices if not review.is_demo or "Demo mode" not in n
    )

    stats = "".join(
        f'<div class="stat"><span class="muted">{label}</span><b{cls}>{value}</b></div>'
        for label, value, cls in [
            ("Total findings", s.total, ""),
            ("Critical", s.by_severity.critical, ' class="critical"'),
            ("Warnings", s.by_severity.warn, ' class="warn"'),
            ("Info", s.by_severity.info, ' class="info"'),
        ]
    )
    reviewers = "".join(
        f"<tr><td>{_e(r.name)}</td><td>{_e(r.status)}</td><td>{r.finding_count}</td><td>{_e(r.engine)}</td></tr>"
        for r in review.reviewers
    )

    sections = []
    for severity in SEVERITY_ORDER:
        items = [f for f in review.findings if f.severity == severity]
        if items:
            sections.append(
                f"<h2>{_e(SEVERITY_LABEL[severity])} ({len(items)})</h2>" + "".join(_finding_html(f) for f in items)
            )
    body = "".join(sections) or '<p class="muted">No findings were reported.</p>'

    return (
        "<!DOCTYPE html>\n"
        '<html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        f"{CSP}<title>Code review: {_e(review.filename)}</title><style>{STYLE}</style></head><body><main>"
        f"<h1>Code review report</h1>"
        f'<div class="muted">{_e(review.filename)} &middot; {_e(review.language)} &middot; {review.line_count} lines'
        f" &middot; {_e(_timestamp(review.created_at))} &middot; review {_e(review.review_id)}"
        f" &middot; status: {_e(review.status)}</div>"
        f"{banner}{notices}"
        f'<div class="grid">{stats}</div>'
        f"<h2>Reviewers</h2><table><thead><tr><th>Reviewer</th><th>Status</th><th>Findings</th><th>Engine</th></tr></thead>"
        f"<tbody>{reviewers}</tbody></table>"
        f"{body}</main></body></html>\n"
    )


def default_report_name(review: ReviewResponse, extension: str) -> str:
    return f"review-{review.created_at.strftime('%Y%m%d-%H%M%S')}.{extension}"
