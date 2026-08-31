import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from copytree.gitignore import GitignoreRuleSet, GitignoreStack, _translate_glob  # noqa: E402


def make_ruleset(text: str) -> GitignoreRuleSet:
    """构造规则集：文本经由真实解析路径（打开文件被 mock 掉）。"""
    from unittest import mock

    with mock.patch("builtins.open", mock.mock_open(read_data=text)):
        return GitignoreRuleSet("ignored-path")


class TranslateGlobTests(unittest.TestCase):
    def test_star_stays_within_segment(self):
        self.assertEqual(_translate_glob("*.log"), r"[^/]*\.log")

    def test_double_star_crosses_segments(self):
        self.assertEqual(_translate_glob("a/**/b"), r"a/.*/b")

    def test_question_mark(self):
        self.assertEqual(_translate_glob("file?.txt"), r"file[^/]\.txt")

    def test_regex_special_chars_escaped(self):
        self.assertEqual(_translate_glob("a+b.txt"), r"a\+b\.txt")

    def test_empty_after_strip(self):
        self.assertEqual(_translate_glob("/"), "")


class RuleSetTests(unittest.TestCase):
    def test_comment_and_blank_ignored(self):
        rs = make_ruleset("# 注释\n\n   \n*.log\n")
        self.assertEqual(len(rs.rules), 1)

    def test_unanchored_matches_any_level(self):
        rs = make_ruleset("*.log\n")
        self.assertIs(rs.match("a.log", False), True)
        self.assertIs(rs.match("x/y/a.log", False), True)
        self.assertIs(rs.match("a.logx", False), None)

    def test_negation(self):
        rs = make_ruleset("*.log\n!important.log\n")
        self.assertIs(rs.match("a.log", False), True)
        self.assertIs(rs.match("important.log", False), False)

    def test_anchored_with_inner_slash(self):
        rs = make_ruleset("/build\n")
        self.assertIs(rs.match("build/out.bin", True), True)
        self.assertIs(rs.match("lib/build/x", True), None)

    def test_dir_only(self):
        rs = make_ruleset("temp/\n")
        self.assertIs(rs.match("temp", True), True)
        self.assertIs(rs.match("a/temp", True), True)
        self.assertIs(rs.match("temp", False), None)

    def test_double_star_pattern(self):
        rs = make_ruleset("docs/**/*.md\n")
        self.assertIs(rs.match("docs/guide/index.md", False), True)
        self.assertIs(rs.match("docs/a/b/c.md", False), True)
        self.assertIs(rs.match("docs/readme.txt", False), None)

    def test_bare_name_matches_file_and_dir(self):
        rs = make_ruleset("node_modules\n")
        self.assertIs(rs.match("x/node_modules", True), True)
        self.assertIs(rs.match("x/node_modules", False), True)

    def test_dir_only_rule_does_not_match_file(self):
        rs = make_ruleset("node_modules/\n")
        self.assertIs(rs.match("x/node_modules", True), True)
        self.assertIs(rs.match("x/node_modules", False), None)

    def test_last_matching_rule_wins(self):
        rs = make_ruleset("*.log\n!important.log\nreally.log\n")
        self.assertIs(rs.match("really.log", False), True)
        self.assertIs(rs.match("important.log", False), False)


class StackCascadeTests(unittest.TestCase):
    def test_inner_ruleset_overrides_outer(self):
        import os
        import tempfile

        root = tempfile.mkdtemp()
        self.addCleanup(_cleanup, root)
        sub = os.path.join(root, "sub")
        os.makedirs(sub)
        with open(os.path.join(root, ".gitignore"), "w", encoding="utf-8") as f:
            f.write("*.log\n")
        with open(os.path.join(sub, ".gitignore"), "w", encoding="utf-8") as f:
            f.write("!keep.log\n")

        stack = GitignoreStack()
        stack.push_dir(root)
        self.assertIs(stack.is_ignored("a.log", False), True)
        self.assertIs(stack.is_ignored("sub/keep.log", False), True)
        stack.push_dir(sub)
        self.assertIs(stack.is_ignored("sub/keep.log", False), False)
        stack.pop_dir()
        self.assertIs(stack.is_ignored("sub/keep.log", False), True)

    def test_missing_gitignore_is_empty_ruleset(self):
        import os
        import tempfile

        root = tempfile.mkdtemp()
        self.addCleanup(_cleanup, root)
        stack = GitignoreStack()
        stack.push_dir(root)  # 目录里没有 .gitignore
        self.assertIs(stack.is_ignored("anything", False), False)


def _cleanup(path: str):
    import shutil

    shutil.rmtree(path, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
