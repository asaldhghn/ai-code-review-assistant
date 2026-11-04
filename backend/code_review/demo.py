"""Demo engine: a deterministic, rule-based scanner.

It exists so the product can be explored without an API key or any paid AI call. It is NOT an
AI model: it applies fixed regex rules (any language) and Python `ast` checks (Python only), and
every result is labeled as demo output by the service and the UI. The same input always produces
the same findings.
"""

import ast
import builtins
import re
from collections.abc import Callable
from dataclasses import dataclass

from .schemas import SEVERITY_ORDER, Finding, ReviewerId

DEMO_ENGINE = "demo-rules-v1 (rule-based, no AI)"
MAX_PER_RULE = 5
LONG_LINE = 140
LONG_FUNCTION_LINES = 40
MAX_PARAMS = 5

_COMMENT_PREFIXES = ("#", "//", "/*", "*", "--")


@dataclass(frozen=True)
class Rule:
    id: str
    reviewer: ReviewerId
    severity: str
    category: str
    title: str
    pattern: re.Pattern
    description: str  # may use {name} (a regex group called `name`) and {line}
    why: str
    suggestion: str
    languages: frozenset[str] | None = None  # None = every language
    also: re.Pattern | None = None  # a second regex that must match the same line
    skip: Callable[[re.Match], bool] | None = None
    scan_comments: bool = False
    code_only: bool = False  # match against the line with string-literal contents blanked out


_STRING_LITERAL = re.compile(r"\"(?:[^\"\\]|\\.)*\"|'(?:[^'\\]|\\.)*'")


def _blank_strings(text: str) -> str:
    """Replace the inside of string literals with spaces so rules do not match inside them."""
    return _STRING_LITERAL.sub(lambda m: m.group(0)[0] + " " * (len(m.group(0)) - 2) + m.group(0)[-1], text)


def _rx(pattern: str) -> re.Pattern:
    return re.compile(pattern)


def _placeholder(match: re.Match) -> bool:
    value = match.group("value").lower()
    return value.startswith(("your", "<", "${", "{{", "changeme", "example", "xxx", "todo")) or "placeholder" in value


SECURITY_RULES = [
    Rule(
        "hardcoded-secret",
        "security",
        "critical",
        "security",
        "Hardcoded secret in `{name}`",
        _rx(
            r"""(?i)\b(?P<name>\w*(?:api[_-]?key|secret|passw(?:or)?d|passwd|pwd|token|private[_-]?key|access[_-]?key)\w*)\s*[:=]\s*["'](?P<value>[^"'\s]{6,})["']"""
        ),
        "`{name}` is assigned a literal credential-like string directly in the source.",
        "Anyone with read access to the repository, a build log or a screenshot can use this credential, and it stays in git history even after deletion.",
        'Load it from an environment variable or a secrets manager (for example `os.environ["API_KEY"]`) and rotate the exposed value.',
        skip=_placeholder,
    ),  # fmt: skip
    Rule(
        "aws-key",
        "security",
        "critical",
        "security",
        "AWS access key ID in source",
        _rx(r"\bAKIA[0-9A-Z]{16}\b"),
        "A string matching the format of an AWS access key ID is committed in the code.",
        "Leaked cloud keys are scanned for and abused within minutes of being pushed.",
        "Revoke the key in AWS, create a new one and load it from the environment or an IAM role.",
    ),  # fmt: skip
    Rule(
        "private-key",
        "security",
        "critical",
        "security",
        "Private key material in source",
        _rx(r"-----BEGIN (?:RSA |EC |DSA |OPENSSH )?PRIVATE KEY-----"),
        "A PEM private key header appears in the code.",
        "Anyone who can read the file can impersonate the key owner.",
        "Remove the key from the repository, rotate it, and mount it as a secret at runtime.",
        scan_comments=True,
    ),  # fmt: skip
    Rule(
        "sql-injection",
        "security",
        "critical",
        "security",
        "SQL built from string concatenation",
        _rx(r"""(?i)\b(?:select\s.+\sfrom|insert\s+into|delete\s+from|update\s+\w+\s+set)\b"""),
        "A SQL statement is assembled with string concatenation or interpolation, so values are mixed into the query text.",
        "An attacker who controls any interpolated value can change the query, for example `alice' OR '1'='1`, to read or modify other rows.",
        'Use parameterized queries, e.g. `cursor.execute("SELECT * FROM users WHERE name = ?", (name,))`.',
        also=_rx(r"""["']\s*\+|\+\s*["']|\bf["'][^"']*\{|\.format\(|["']\s*%\s*[\w(]|`[^`]*\$\{"""),
    ),  # fmt: skip
    Rule(
        "eval-call",
        "security",
        "critical",
        "security",
        "`eval()` on dynamic input",
        _rx(r"(?<![\w.])(?P<name>eval)\s*\("),
        "`eval()` executes a string as code.",
        "If any part of the string comes from a user, file or network, the attacker can run arbitrary code with your privileges.",
        "Parse data with `json.loads` / `ast.literal_eval`, or dispatch through an explicit allow-list of operations.",
        languages=frozenset({"python", "javascript", "typescript", "php", "ruby"}),
        code_only=True,
    ),  # fmt: skip
    Rule(
        "exec-call",
        "security",
        "critical",
        "security",
        "`exec()` runs dynamic code",
        _rx(r"(?<![\w.])exec\s*\("),
        "`exec()` executes a string as Python code.",
        "Any attacker-influenced input becomes arbitrary code execution.",
        "Remove dynamic execution, or restrict the behavior to a fixed set of functions chosen by name.",
        languages=frozenset({"python"}),
        code_only=True,
    ),  # fmt: skip
    Rule(
        "shell-true",
        "security",
        "warn",
        "security",
        "Shell command execution",
        _rx(r"shell\s*=\s*True|\bos\.system\s*\(|\bos\.popen\s*\(|child_process[^\n]*\.exec(?:Sync)?\s*\("),
        "A command is run through a shell, which interprets metacharacters such as `;`, `&&` and `$()`.",
        "If any argument contains user-controlled text, an attacker can append their own commands.",
        'Pass an argument list without a shell, e.g. `subprocess.run(["git", "status"], check=True)`, and validate arguments.',
    ),  # fmt: skip
    Rule(
        "unsafe-deserialization",
        "security",
        "warn",
        "security",
        "Unsafe deserialization",
        _rx(r"\bpickle\.loads?\s*\(|\byaml\.load\s*\((?![^)]*Safe)|\bmarshal\.loads?\s*\("),
        "Data is deserialized with a loader that can construct arbitrary objects.",
        "Deserializing untrusted bytes can execute code during loading.",
        "Use `json` for data exchange or `yaml.safe_load`, and never unpickle data from an untrusted source.",
    ),  # fmt: skip
    Rule(
        "weak-hash",
        "security",
        "warn",
        "security",
        "Weak hash algorithm (MD5/SHA-1)",
        _rx(r"""(?i)hashlib\.(?:md5|sha1)\s*\(|createHash\(\s*["'](?:md5|sha1)["']"""),
        "MD5 and SHA-1 are broken for security purposes.",
        "Collisions can be forged, and fast hashes make stored passwords cheap to brute-force.",
        "Use SHA-256 or better for integrity, and a password hash (bcrypt, scrypt, Argon2) for passwords.",
    ),  # fmt: skip
    Rule(
        "tls-verify-off",
        "security",
        "warn",
        "security",
        "TLS certificate verification disabled",
        _rx(
            r"verify\s*=\s*False|rejectUnauthorized\s*:\s*false|InsecureSkipVerify\s*:\s*true|CURLOPT_SSL_VERIFYPEER\s*,\s*(?:false|0)"
        ),
        "Certificate verification is turned off for an outgoing connection.",
        "Anyone on the network path can impersonate the server and read or alter traffic.",
        "Remove the override and fix the underlying certificate problem, e.g. by trusting the right CA bundle.",
    ),  # fmt: skip
    Rule(
        "dom-xss",
        "security",
        "warn",
        "security",
        "Unescaped HTML insertion (XSS risk)",
        _rx(r"\.innerHTML\s*=|dangerouslySetInnerHTML|document\.write\s*\("),
        "HTML is inserted into the page without escaping.",
        "If the string contains user-controlled text, an attacker can inject script that runs in other users' sessions.",
        "Use `textContent` or the framework's escaping, or sanitize with a vetted library such as DOMPurify.",
        languages=frozenset({"javascript", "typescript", "other"}),
    ),  # fmt: skip
    Rule(
        "secret-logged",
        "security",
        "warn",
        "security",
        "Sensitive value written to logs",
        _rx(r"(?i)\b(?:print|console\.log|log(?:ger)?\.\w+)\s*\(.*\b(?:password|passwd|secret|token|api[_-]?key)\b"),
        "A log or print statement includes a credential-like variable.",
        "Logs are copied to many systems and are rarely protected like secrets.",
        "Log an identifier instead of the value, or mask it (for example the last 4 characters).",
    ),  # fmt: skip
    Rule(
        "cors-wildcard",
        "security",
        "warn",
        "security",
        "Wildcard CORS policy",
        _rx(
            r"""allow_origins\s*=\s*\[\s*["']\*["']|Access-Control-Allow-Origin["']?\s*[:,]\s*["']\*["']|origin\s*:\s*["']\*["']"""
        ),
        "Any website is allowed to call this API from a browser.",
        "Combined with cookies or tokens, a wildcard policy lets malicious pages act on behalf of visitors.",
        "List the specific origins that need access.",
    ),  # fmt: skip
    Rule(
        "debug-enabled",
        "security",
        "info",
        "security",
        "Debug mode enabled",
        _rx(r"\bdebug\s*=\s*True\b"),
        "Debug mode is switched on in code.",
        "Debug servers can expose stack traces and, in some frameworks, an interactive console.",
        "Read the flag from configuration and default it to off in production.",
        languages=frozenset({"python"}),
    ),  # fmt: skip
]

MAINTAINABILITY_RULES = [
    Rule(
        "bare-except-js",
        "maintainability",
        "warn",
        "error-handling",
        "Empty catch block",
        _rx(r"catch\s*(?:\([^)]*\))?\s*\{\s*\}"),
        "The catch block is empty, so the error disappears.",
        "Failures become invisible and the program continues in an unknown state.",
        "Handle the error, or at least log it with context before continuing.",
        languages=frozenset({"javascript", "typescript", "java", "csharp", "php"}),
    ),  # fmt: skip
    Rule(
        "todo-marker",
        "maintainability",
        "info",
        "documentation",
        "Unresolved TODO/FIXME marker",
        _rx(r"\b(?:TODO|FIXME|HACK|XXX)\b"),
        "A work-in-progress marker is left in the code.",
        "Markers without an owner or ticket tend to stay forever and hide real gaps.",
        "Resolve it, or link it to a tracked issue.",
        scan_comments=True,
    ),  # fmt: skip
    Rule(
        "console-log",
        "maintainability",
        "info",
        "dead-code",
        "Leftover debugging output",
        _rx(r"\bconsole\.log\s*\(|^\s*debugger\s*;?\s*$"),
        "A debugging statement is still in the code.",
        "Debug output adds noise in production and can leak data.",
        "Remove it, or replace it with a real logger at an appropriate level.",
        languages=frozenset({"javascript", "typescript"}),
    ),  # fmt: skip
    Rule(
        "var-keyword",
        "maintainability",
        "info",
        "style",
        "`var` used instead of `let`/`const`",
        _rx(r"^\s*var\s+\w+"),
        "`var` is function-scoped and hoisted, which makes variable lifetimes hard to follow.",
        "It is a frequent source of accidental shadowing and bugs.",
        "Use `const` by default and `let` when reassignment is needed.",
        languages=frozenset({"javascript", "typescript"}),
    ),  # fmt: skip
    Rule(
        "loose-equality",
        "maintainability",
        "info",
        "style",
        "Loose equality (`==`)",
        _rx(r"(?<![=!<>])==(?!=)"),
        "`==` applies type coercion before comparing.",
        "Surprising results such as `0 == ''` being true make conditions harder to reason about.",
        "Use strict equality (`===`) unless coercion is intended and documented.",
        languages=frozenset({"javascript", "typescript"}),
        code_only=True,
    ),  # fmt: skip
    Rule(
        "magic-number",
        "maintainability",
        "info",
        "naming",
        "Magic number {name}",
        _rx(r"[*/+\-]\s*(?P<name>0\.\d{2,}|\d{3,})\b(?!\s*[\]:)])"),
        "The literal {name} is used directly in an expression.",
        "A reader cannot tell what it represents, and changing it later means hunting for every copy.",
        "Give it a named constant, e.g. `TAX_RATE = 0.13`.",
        languages=frozenset(
            {"python", "javascript", "typescript", "java", "go", "csharp", "cpp", "c", "php", "ruby", "rust"}
        ),
        code_only=True,
    ),  # fmt: skip
]

ALL_RULES = SECURITY_RULES + MAINTAINABILITY_RULES


def _is_comment(line: str) -> bool:
    return line.lstrip().startswith(_COMMENT_PREFIXES)


def _rule_findings(rule: Rule, lines: list[str], language: str, path: str) -> list[Finding]:
    if rule.languages is not None and language not in rule.languages and language != "other":
        return []
    found: list[Finding] = []
    for number, text in enumerate(lines, start=1):
        if not rule.scan_comments and _is_comment(text):
            continue
        match = rule.pattern.search(_blank_strings(text) if rule.code_only else text)
        if not match or (rule.also and not rule.also.search(text)):
            continue
        if rule.skip and rule.skip(match):
            continue
        fields = {"name": match.groupdict().get("name") or match.group(0).strip(), "line": number}
        found.append(
            Finding(
                path=path,
                line=number,
                severity=rule.severity,
                category=rule.category,
                title=rule.title.format(**fields),
                description=rule.description.format(**fields),
                why_it_matters=rule.why,
                suggestion=rule.suggestion,
            )  # fmt: skip
        )
        if len(found) >= MAX_PER_RULE:
            break
    return found


# ---------------------------------------------------------------------------
# Python-only structural checks (ast)
# ---------------------------------------------------------------------------


def _bound_names(tree: ast.AST) -> set[str]:
    """Every name that is bound anywhere in the module (an over-approximation, so no false alarms)."""
    names = set(dir(builtins)) | {"__file__", "__name__", "__doc__"}
    for node in ast.walk(tree):
        if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store | ast.Del):
            names.add(node.id)
        elif isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef):
            names.add(node.name)
        elif isinstance(node, ast.arg):
            names.add(node.arg)
        elif isinstance(node, ast.Import | ast.ImportFrom):
            for alias in node.names:
                names.add((alias.asname or alias.name).split(".")[0])
        elif isinstance(node, ast.ExceptHandler) and node.name:
            names.add(node.name)
        elif isinstance(node, ast.Global | ast.Nonlocal):
            names.update(node.names)
        elif isinstance(node, ast.MatchAs | ast.MatchStar) and node.name:
            names.add(node.name)
    return names


def _function_lines(node: ast.FunctionDef | ast.AsyncFunctionDef) -> int:
    return (node.end_lineno or node.lineno) - node.lineno + 1


def _python_findings(code: str, path: str) -> list[Finding]:
    """Maintainability findings from Python AST checks."""
    maintain: list[Finding] = []
    try:
        tree = ast.parse(code)
    except SyntaxError as err:
        maintain.append(
            Finding(
                path=path,
                line=err.lineno if err.lineno and err.lineno >= 1 else None,
                severity="critical",
                category="bug",
                title="Syntax error",
                description=f"Python cannot parse this file: {err.msg}.",
                why_it_matters="The module cannot be imported or run until the syntax error is fixed.",
                suggestion="Fix the syntax at the reported line; the rest of the structural checks were skipped.",
            )  # fmt: skip
        )
        return maintain

    # Undefined names (a definite NameError when that line runs).
    bound = _bound_names(tree)
    reported: set[str] = set()
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Name)
            and isinstance(node.ctx, ast.Load)
            and node.id not in bound
            and node.id not in reported
        ):
            reported.add(node.id)
            maintain.append(
                Finding(
                    path=path,
                    line=node.lineno,
                    severity="critical",
                    category="bug",
                    title=f"Undefined name `{node.id}`",
                    description=f"`{node.id}` is used but never imported, defined or assigned in this file.",
                    why_it_matters="Running this line raises NameError.",
                    suggestion=f"Import it (for example `import {node.id}`) or define it before use.",
                )  # fmt: skip
            )

    # Unused imports.
    used = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load)}
    used |= {n.value.id for n in ast.walk(tree) if isinstance(n, ast.Attribute) and isinstance(n.value, ast.Name)}
    exported = set()
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Assign)
            and any(isinstance(t, ast.Name) and t.id == "__all__" for t in node.targets)
            and isinstance(node.value, ast.List | ast.Tuple)
        ):
            exported = {e.value for e in node.value.elts if isinstance(e, ast.Constant)}
    for node in tree.body:
        if isinstance(node, ast.Import | ast.ImportFrom):
            for alias in node.names:
                bound_name = (alias.asname or alias.name).split(".")[0]
                if alias.name != "*" and bound_name not in used and bound_name not in exported:
                    maintain.append(
                        Finding(
                            path=path,
                            line=node.lineno,
                            severity="info",
                            category="dead-code",
                            title=f"Unused import `{bound_name}`",
                            description=f"`{bound_name}` is imported but never used.",
                            why_it_matters="Unused imports add noise, slow start-up slightly, and mislead readers about dependencies.",
                            suggestion=f"Delete the `{bound_name}` import.",
                        )  # fmt: skip
                    )

    functions = [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef | ast.AsyncFunctionDef)]
    for func in functions:
        size = _function_lines(func)
        if size > LONG_FUNCTION_LINES:
            maintain.append(
                Finding(
                    path=path,
                    line=func.lineno,
                    severity="warn",
                    category="complexity",
                    title=f"`{func.name}` is {size} lines long",
                    description=f"`{func.name}` spans {size} lines, above the {LONG_FUNCTION_LINES}-line guideline.",
                    why_it_matters="Long functions mix responsibilities, are hard to test, and hide bugs.",
                    suggestion="Extract cohesive blocks into well-named helper functions.",
                )  # fmt: skip
            )
        params = len(func.args.args) + len(func.args.kwonlyargs)
        if params > MAX_PARAMS:
            maintain.append(
                Finding(
                    path=path,
                    line=func.lineno,
                    severity="info",
                    category="complexity",
                    title=f"`{func.name}` takes {params} parameters",
                    description=f"`{func.name}` has {params} parameters.",
                    why_it_matters="Long parameter lists are easy to call in the wrong order and signal a missing abstraction.",
                    suggestion="Group related parameters into a dataclass or a small config object.",
                )  # fmt: skip
            )
        for default in [*func.args.defaults, *func.args.kw_defaults]:
            if isinstance(default, ast.List | ast.Dict | ast.Set):
                maintain.append(
                    Finding(
                        path=path,
                        line=default.lineno,
                        severity="warn",
                        category="bug",
                        title=f"Mutable default argument in `{func.name}`",
                        description=f"`{func.name}` uses a list, dict or set as a default argument value.",
                        why_it_matters="The default is created once and shared by every call, so state leaks between calls.",
                        suggestion="Use `None` as the default and create the container inside the function.",
                    )  # fmt: skip
                )

    # Swallowed / bare exceptions.
    for node in ast.walk(tree):
        if isinstance(node, ast.ExceptHandler):
            swallowed = len(node.body) == 1 and isinstance(node.body[0], ast.Pass)
            if node.type is None or swallowed:
                what = "A bare `except:`" if node.type is None else f"`except {ast.unparse(node.type)}`"
                suffix = (
                    " that does nothing with the error"
                    if swallowed
                    else " catches everything, including KeyboardInterrupt"
                )
                maintain.append(
                    Finding(
                        path=path,
                        line=node.lineno,
                        severity="warn",
                        category="error-handling",
                        title="Swallowed or overly broad exception handler",
                        description=f"{what}{suffix}.",
                        why_it_matters="Real failures vanish silently, so bugs surface far from their cause.",
                        suggestion="Catch the specific exception you expect and log or re-raise anything else.",
                    )  # fmt: skip
                )

    # Duplicate function bodies.
    seen: dict[str, ast.FunctionDef | ast.AsyncFunctionDef] = {}
    for func in functions:
        if _function_lines(func) < 2:
            continue
        key = "\n".join(ast.dump(stmt) for stmt in func.body)
        first = seen.get(key)
        if first is None:
            seen[key] = func
        else:
            maintain.append(
                Finding(
                    path=path,
                    line=func.lineno,
                    severity="warn",
                    category="duplication",
                    title=f"`{func.name}` duplicates `{first.name}`",
                    description=f"`{func.name}` has exactly the same body as `{first.name}` (line {first.lineno}).",
                    why_it_matters="Fixing a bug in one copy and forgetting the other is how inconsistencies are born.",
                    suggestion=f"Keep one implementation (or parameterize it) and call it from both places instead of `{func.name}`.",
                )  # fmt: skip
            )

    return maintain


def _long_lines(lines: list[str], path: str) -> list[Finding]:
    long = [n for n, text in enumerate(lines, start=1) if len(text) > LONG_LINE]
    if not long:
        return []
    return [
        Finding(
            path=path,
            line=long[0],
            severity="info",
            category="style",
            title=f"{len(long)} line(s) longer than {LONG_LINE} characters",
            description=f"First occurrence is line {long[0]}; {len(long)} line(s) exceed {LONG_LINE} characters.",
            why_it_matters="Very long lines are hard to read in diffs and side-by-side views.",
            suggestion="Break the expression across lines or extract intermediate variables.",
        )  # fmt: skip
    ]


def run_demo_reviewer(reviewer: ReviewerId, code: str, language: str, path: str) -> list[Finding]:
    """Deterministic findings for one reviewer, sorted by severity then line."""
    lines = code.splitlines()
    rules = SECURITY_RULES if reviewer == "security" else MAINTAINABILITY_RULES
    findings: list[Finding] = []
    for rule in rules:
        findings.extend(_rule_findings(rule, lines, language, path))
    if reviewer == "maintainability":
        findings.extend(_long_lines(lines, path))
        if language == "python":
            findings.extend(_python_findings(code, path))

    unique: dict[tuple, Finding] = {}
    for finding in findings:
        unique.setdefault((finding.line, finding.title), finding)
    order = {name: index for index, name in enumerate(SEVERITY_ORDER)}
    return sorted(unique.values(), key=lambda f: (order[f.severity], f.line or 0, f.title))
