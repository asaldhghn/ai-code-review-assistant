"""Parse git diffs into per-file line maps so model-supplied line numbers can be verified."""

import re
from dataclasses import dataclass, field

DIFF_HEADER = re.compile(r'^diff --git "?a/(.+?)"? "?b/(.+?)"?$')
HUNK_HEADER = re.compile(r"^@@ -(\d+)(?:,\d+)? \+(\d+)(?:,\d+)? @@")


@dataclass
class FileDiff:
    path: str  # path in the new version (the one findings must cite)
    old_path: str  # path before the change (differs for renames)
    added: set[int] = field(default_factory=set)  # new-file line numbers of added lines
    context: set[int] = field(default_factory=set)  # new-file line numbers of unchanged lines shown
    deleted: set[int] = field(default_factory=set)  # old-file line numbers of removed lines


@dataclass
class ParsedDiff:
    files: dict[str, FileDiff]
    renames: dict[str, str]  # old path -> new path
    rendered: str  # the diff with NEW/OLD line numbers, as shown to the model

    @property
    def paths(self) -> list[str]:
        return list(self.files)


def parse_diff(diff: str) -> ParsedDiff:
    """Parse a git diff into per-file line maps and a line-numbered rendering."""
    files: dict[str, FileDiff] = {}
    rendered: list[str] = []
    current: FileDiff | None = None
    in_hunk = False
    old_no = new_no = 0

    for line in diff.splitlines():
        header = DIFF_HEADER.match(line)
        if header:
            old_path = header.group(1).replace("\\", "/")
            path = header.group(2).replace("\\", "/")
            current = files.get(path) or FileDiff(path, old_path)
            files[path] = current
            in_hunk = False
            rendered.append(line)
            continue

        if current is None:
            rendered.append(line)
            continue

        hunk = HUNK_HEADER.match(line)
        if hunk:
            old_no, new_no = int(hunk.group(1)), int(hunk.group(2))
            in_hunk = True
            rendered.append(line)
            continue

        if not in_hunk:
            # File header lines: only renames matter here (they name both paths exactly).
            if line.startswith("rename from "):
                current.old_path = line[len("rename from ") :].strip()
            elif line.startswith("rename to "):
                new_path = line[len("rename to ") :].strip()
                if new_path != current.path:
                    files.pop(current.path, None)
                    current.path = new_path
                    files[new_path] = current
            rendered.append(line)
            continue

        marker = line[:1]
        if marker == "+":
            current.added.add(new_no)
            rendered.append(f"NEW {new_no:>4} | {line}")
            new_no += 1
        elif marker == "-":
            current.deleted.add(old_no)
            rendered.append(f"OLD {old_no:>4} | {line}")
            old_no += 1
        elif marker == "\\":
            rendered.append(line)  # "\ No newline at end of file"
        else:  # unchanged context line (git prefixes it with a space)
            current.context.add(new_no)
            rendered.append(f"NEW {new_no:>4} | {line}")
            new_no += 1
            old_no += 1

    renames = {f.old_path: f.path for f in files.values() if f.old_path != f.path}
    return ParsedDiff(files, renames, "\n".join(rendered))
