import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from copytree.formatter import (  # noqa: E402
    format_names,
    format_output,
    format_paths,
    format_summary,
    VALID_FORMATS,
)
from copytree.scanner import scan_directory, build_tree_text  # noqa: E402
from copytree.config import VALID_FORMATS as CONFIG_FORMATS  # noqa: E402

from loguru import logger as _quiet_logger  # noqa: E402

_quiet_logger.remove()  # 保持测试输出干净


def make_result(tmp, structure):
    for rel, content in structure.items():
        path = tmp / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    return scan_directory(str(tmp))


class NewFormatTests(unittest.TestCase):
    def setUp(self):
        import shutil

        self.tmp = Path("test_runtime_formats")
        if self.tmp.exists():
            shutil.rmtree(self.tmp)
        self.tmp.mkdir()
        self.result = make_result(self.tmp, {
            "src/main.py": "print(1)",
            "src/utils/helper.js": "x",
            "README.md": "hello",
        })

    def tearDown(self):
        import shutil

        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_paths_one_absolute_path_per_file(self):
        import os

        text = format_paths(self.result)
        lines = text.splitlines()
        self.assertEqual(len(lines), 3)
        for line in lines:
            self.assertTrue(os.path.isabs(line), line)
        self.assertIn("main.py", text)
        self.assertIn("helper.js", text)
        # 目录不出现在路径列表
        self.assertNotIn("utils\n", text)

    def test_names_lists_file_names_only(self):
        text = format_names(self.result)
        lines = text.splitlines()
        self.assertEqual(sorted(lines), ["README.md", "helper.js", "main.py"])

    def test_summary_contains_counts_and_size(self):
        text = format_summary(self.result)
        self.assertIn("3 个文件", text)
        self.assertIn("2 个文件夹", text)
        self.assertIn("总大小", text)

    def test_summary_flags_truncation(self):
        self.result.truncated = True
        self.assertIn("已截断", format_summary(self.result))

    def test_format_output_dispatches_new_formats(self):
        tree_text = build_tree_text(self.result)
        for fmt in ("paths", "names", "summary"):
            out = format_output(tree_text, fmt, result=self.result)
            self.assertIsInstance(out, str)
            self.assertTrue(out)

    def test_format_output_without_result_falls_back_to_tree(self):
        tree_text = build_tree_text(self.result)
        self.assertEqual(format_output(tree_text, "paths"), tree_text)
        self.assertEqual(format_output(tree_text, "names"), tree_text)
        self.assertEqual(format_output(tree_text, "summary"), tree_text)

    def test_valid_formats_shared_with_config(self):
        self.assertEqual(set(VALID_FORMATS), set(CONFIG_FORMATS))
        for fmt in ("text", "markdown", "markdown-list", "json", "paths", "names", "summary"):
            self.assertIn(fmt, VALID_FORMATS)


class ScannerMetadataTests(unittest.TestCase):
    def setUp(self):
        import shutil

        self.tmp = Path("test_runtime_meta")
        if self.tmp.exists():
            shutil.rmtree(self.tmp)
        self.tmp.mkdir()

    def tearDown(self):
        import shutil

        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_size_always_populated_for_stats(self):
        result = make_result(self.tmp, {"a.txt": "12345"})
        entry = result.root.children[0]
        self.assertIsNotNone(entry.size)
        self.assertEqual(entry.size, 5)

    def test_exclude_patterns_filter_names_and_paths(self):
        result = scan_directory(
            str(self.tmp),
            exclude_patterns={"*.log", "dist/*"},
            prune_empty_dirs=True,
        )
        self.assertEqual(result.total_files, 0)

    def test_exclude_patterns_path_match(self):
        (self.tmp / "dist").mkdir()
        (self.tmp / "dist" / "deep").mkdir()
        (self.tmp / "dist" / "deep" / "x.js").write_text("1", encoding="utf-8")
        (self.tmp / "keep.js").write_text("1", encoding="utf-8")
        result = scan_directory(str(self.tmp), exclude_patterns={"dist/*"}, prune_empty_dirs=True)
        self.assertEqual(result.total_files, 1)
        self.assertEqual(result.root.children[0].name, "keep.js")


if __name__ == "__main__":
    unittest.main()
