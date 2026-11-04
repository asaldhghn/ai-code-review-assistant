from code_review.agents import ReviewInput, check_line
from code_review.diffs import parse_diff

DIFF = """diff --git a/app.py b/app.py
index 111..222 100644
--- a/app.py
+++ b/app.py
@@ -1,3 +1,4 @@
 import os
-old = 1
+new = 2
+extra = 3
 tail = 4
diff --git a/old_name.py b/new_name.py
similarity index 90%
rename from old_name.py
rename to new_name.py
@@ -1,1 +1,1 @@
-a = 1
+a = 2
"""


def test_parse_diff_tracks_added_context_deleted_lines():
    parsed = parse_diff(DIFF)
    app = parsed.files["app.py"]
    assert app.added == {2, 3}
    assert app.context == {1, 4}
    assert app.deleted == {2}
    assert "NEW    2 | +new = 2" in parsed.rendered
    assert "OLD    2 | -old = 1" in parsed.rendered


def test_parse_diff_handles_renames():
    parsed = parse_diff(DIFF)
    assert parsed.paths == ["app.py", "new_name.py"]
    assert parsed.renames == {"old_name.py": "new_name.py"}


def test_check_line_in_git_mode_only_accepts_added_or_context_lines():
    review_input = ReviewInput("git", DIFF, parse_diff(DIFF).paths)
    assert check_line(review_input, "app.py", 2) == ("added", 2)
    assert check_line(review_input, "app.py", 4) == ("context", 4)
    assert check_line(review_input, "app.py", 99) == ("unverified", None)
    assert check_line(review_input, "unknown.py", 1) == ("unverified", None)
    assert check_line(review_input, "app.py", None) == ("none", None)


def test_check_line_in_file_mode_requires_line_to_exist():
    review_input = ReviewInput("file", "a\nb\nc\n", ["x.py"])
    assert check_line(review_input, "x.py", 3) == ("valid", 3)
    assert check_line(review_input, "x.py", 4) == ("unverified", None)
