"""Tools the reviewers can call in CLI mode: read_file and ripgrep.

These are NEVER exposed through the web API: the server has no filesystem tools. They
only read inside one repository root (set by the CLI), refuse secret files and symlink
escapes, and cap their output.

Both return plain strings. Problems are returned as "ERROR: ..." text (never
raised) so the LLM can see what went wrong and adjust.
"""

import os
import re
import subprocess

MAX_LINES = 400  # most lines read_file returns in one call
MAX_CHARS = 20000  # most characters read_file returns in one call
MAX_LINE_CHARS = 500  # longer lines are cut (minified code, lock files)
MAX_FILE_BYTES = 5000000  # read_file refuses files larger than this

RG_MAX_MATCHES_PER_FILE = 20
RG_MAX_LINES = 100  # most result lines ripgrep returns
RG_MAX_CHARS = 8000  # most characters ripgrep returns
RG_MAX_PATTERN_CHARS = 200
RG_TIMEOUT_SECONDS = 20

# Files whose contents must never be sent to an LLM.
SENSITIVE_SUFFIXES = (".pem", ".key", ".p12", ".pfx", ".pypirc")
SENSITIVE_NAMES = ("id_rsa", "id_dsa", "id_ecdsa", "id_ed25519", ".npmrc", ".netrc")
SAFE_ENV_SUFFIXES = (".example", ".sample", ".template")


def find_repo_root(start=None):
    """Return the git root of `start` (default: the current directory).

    Falls back to `start` itself when it is not inside a git repository, or git
    is unavailable.
    """
    start = os.path.realpath(start or os.getcwd())
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            cwd=start,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=10,
        )
    except (OSError, subprocess.SubprocessError):
        return start
    top = result.stdout.strip()
    if result.returncode != 0 or not top:
        return start
    return os.path.realpath(top)


def set_repo_root(path):
    """Set the only directory tree the tools may read or search."""
    global REPO_ROOT
    REPO_ROOT = os.path.realpath(path)


REPO_ROOT = os.path.realpath(os.getcwd())  # the CLI calls set_repo_root(find_repo_root()) at start-up


def _is_sensitive(path):
    """True if any part of the path is a secret file or the .git folder."""
    for part in path.replace("\\", "/").split("/"):
        name = part.lower()
        if name == ".git":
            return True
        if name == ".env" or (name.startswith(".env.") and not name.endswith(SAFE_ENV_SUFFIXES)):
            return True
        if name.endswith(SENSITIVE_SUFFIXES) or name in SENSITIVE_NAMES:
            return True
    return False


def _resolve_inside_repo(file_path):
    """Return (absolute_path, None) if allowed, else (None, error message)."""
    if not isinstance(file_path, str) or not file_path.strip():
        return None, "file_path must be a non-empty string."

    # Relative paths are relative to the repository root, like paths in a diff.
    candidate = os.path.join(REPO_ROOT, file_path.strip())
    real = os.path.realpath(candidate)  # also resolves symlinks

    root = os.path.normcase(REPO_ROOT)
    target = os.path.normcase(real)
    try:
        inside = os.path.commonpath([root, target]) == root
    except ValueError:  # e.g. different drives on Windows
        inside = False
    if not inside:
        return None, f"'{file_path}' is outside the repository and cannot be read."

    if _is_sensitive(os.path.relpath(real, REPO_ROOT)):
        return None, f"'{file_path}' is a sensitive file and cannot be read."

    return real, None


def _check_line_number(name, value):
    """Return an error message if value is not None or a positive int."""
    if value is None:
        return None
    if not isinstance(value, int) or isinstance(value, bool):
        return f"{name} must be an integer."
    if value < 1:
        return f"{name} must be >= 1 (line numbers start at 1)."
    return None


def read_file(file_path, start_line=None, end_line=None):
    """Read a text file inside the repository and return numbered lines.

    start_line and end_line are 1-based and inclusive; both are optional.
    Output is capped at MAX_LINES lines / MAX_CHARS characters.
    """
    for name, value in (("start_line", start_line), ("end_line", end_line)):
        error = _check_line_number(name, value)
        if error:
            return f"ERROR: {error}"
    if start_line is not None and end_line is not None and start_line > end_line:
        return f"ERROR: start_line ({start_line}) is greater than end_line ({end_line})."

    path, error = _resolve_inside_repo(file_path)
    if error:
        return f"ERROR: {error}"

    if not os.path.exists(path):
        return f"ERROR: file not found: {file_path}"
    if os.path.isdir(path):
        return f"ERROR: '{file_path}' is a directory, not a file."

    try:
        if os.path.getsize(path) > MAX_FILE_BYTES:
            return f"ERROR: '{file_path}' is larger than {MAX_FILE_BYTES} bytes. Use ripgrep to search it instead."
        with open(path, encoding="utf-8") as file:
            lines = file.read().splitlines()
    except PermissionError:
        return f"ERROR: permission denied reading '{file_path}'."
    except UnicodeDecodeError:
        return f"ERROR: '{file_path}' is not a UTF-8 text file."
    except OSError as err:
        return f"ERROR: could not read '{file_path}': {err}"

    total = len(lines)
    if total == 0:
        return f"File: {file_path}\nTotal lines: 0\n(file is empty)"

    first = 1 if start_line is None else start_line
    last = total if end_line is None else min(end_line, total)
    if first > total:
        return f"ERROR: start_line {first} is beyond the end of the file ({total} lines)."

    # Apply the size limits, stopping early if either one is reached.
    width = len(str(last))
    body = []
    chars = 0
    shown_last = first - 1
    for number in range(first, last + 1):
        text = lines[number - 1]
        if len(text) > MAX_LINE_CHARS:
            text = text[:MAX_LINE_CHARS] + " ...[line truncated]"
        row = f"{number:>{width}} | {text}"
        if number - first >= MAX_LINES or chars + len(row) > MAX_CHARS:
            break
        body.append(row)
        chars += len(row) + 1
        shown_last = number

    header = f"File: {file_path}\nTotal lines: {total}\nReturned lines: {first}-{shown_last}\n---\n"
    result = header + "\n".join(body)
    if shown_last < last:
        result += (
            f"\n--- Output truncated at line {shown_last}. "
            f"Call read_file again with start_line={shown_last + 1} to continue."
        )
    return result


def ripgrep(search_pattern):
    """Search the repository recursively with ripgrep (a regex pattern).

    Returns lines in the form path:line:text. Secret files, .git, and files
    ignored by .gitignore are not searched.
    """
    if not isinstance(search_pattern, str) or not search_pattern:
        return "ERROR: search_pattern must be a non-empty string."
    if len(search_pattern) > RG_MAX_PATTERN_CHARS:
        return f"ERROR: search_pattern is longer than {RG_MAX_PATTERN_CHARS} characters."

    command = [
        "rg",
        "--line-number",
        "--no-heading",
        "--color",
        "never",
        "--sort",
        "path",
        "--max-count",
        str(RG_MAX_MATCHES_PER_FILE),
        "--max-columns",
        "300",
        "--max-columns-preview",
        "--max-filesize",
        "1M",
        "--glob",
        "!.git",
        "--glob",
        "!.env",
        "--glob",
        "!.env.*",
        "--glob",
        "!*.pem",
        "--glob",
        "!*.key",
        "--glob",
        "!*.p12",
        "--glob",
        "!*.pfx",
        "--glob",
        "!.pypirc",
        "--glob",
        "!.npmrc",
        "--glob",
        "!.netrc",
        "--glob",
        "!id_rsa*",
        "--glob",
        "!id_ed25519*",
        "--glob",
        "!*.lock",
        "--glob",
        "!package-lock.json",
        "-e",
        search_pattern,
        "--",
        ".",
    ]

    try:
        result = subprocess.run(
            command,
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=RG_TIMEOUT_SECONDS,
        )
    except FileNotFoundError:
        return "ERROR: ripgrep (rg) is not installed or not on PATH."
    except subprocess.TimeoutExpired:
        return f"ERROR: ripgrep timed out after {RG_TIMEOUT_SECONDS} seconds."
    except OSError as err:
        return f"ERROR: could not run ripgrep: {err}"

    if result.returncode == 1:
        return f"No matches found for pattern: {search_pattern}"
    if result.returncode != 0:
        lines = result.stderr.strip().splitlines()
        # For a bad regex the useful detail is the "error: ..." line, not the first one.
        details = [row[len("error:") :].strip() for row in lines if row.startswith("error:")]
        detail = details[0] if details else (lines[0] if lines else "no error message from ripgrep")
        return f"ERROR: ripgrep failed (exit code {result.returncode}): {detail}"

    # Tidy paths (strip "./" or ".\") and apply the output limits.
    rows = []
    for line in result.stdout.splitlines():
        if line.startswith(("./", ".\\")):
            line = line[2:]
        # Use forward slashes in the path only; the matched text is left unchanged.
        match = re.match(r"^(.*?):(\d+):(.*)$", line)
        if match:
            line = match.group(1).replace("\\", "/") + ":" + match.group(2) + ":" + match.group(3)
        rows.append(line)

    total = len(rows)
    output = []
    chars = 0
    for row in rows[:RG_MAX_LINES]:
        if chars + len(row) > RG_MAX_CHARS:
            break
        output.append(row)
        chars += len(row) + 1

    text = f"Found {total} matching line(s) (format: path:line:text)\n" + "\n".join(output)
    if len(output) < total:
        text += f"\n--- Output truncated: showing {len(output)} of {total} lines. Use a more specific pattern."
    return text
