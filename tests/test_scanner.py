import shutil
import sys
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from copytree.constants import (  # noqa: E402
    GENERATED_OUTPUT_FILENAMES,
    SOURCE_CODE_EXTENSIONS,
    SOURCE_CODE_FILENAMES,
)
from copytree.scanner import build_tree_text, describe_truncation, _normalize_path, _root_display_name, scan_directory  # noqa: E402


class ScannerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path("test_runtime_scanner")
        if self.tmp.exists():
            shutil.rmtree(self.tmp)
        self.tmp.mkdir()

    def tearDown(self):
        if self.tmp.exists():
            shutil.rmtree(self.tmp)

    def test_max_files_minus_one_is_unlimited(self):
        (self.tmp / "a.txt").write_text("a", encoding="utf-8")
        (self.tmp / "b.txt").write_text("b", encoding="utf-8")

        result = scan_directory(str(self.tmp), max_files=-1)

        self.assertFalse(result.truncated)
        self.assertEqual(result.total_files, 2)
        self.assertEqual(result.total_files_actual, 2)

    def test_max_files_truncation_reports_hidden_files(self):
        (self.tmp / "a.txt").write_text("a", encoding="utf-8")
        (self.tmp / "b.txt").write_text("b", encoding="utf-8")

        result = scan_directory(str(self.tmp), max_files=1)

        self.assertTrue(result.truncated)
        self.assertTrue(result.scan_stopped)
        self.assertEqual(result.total_files, 1)
        self.assertIn("达到 maxFiles=1", describe_truncation(result))

    def test_max_files_hides_unscanned_sibling_directories(self):
        for name in ("a", "b", "c"):
            child = self.tmp / name
            child.mkdir()
            (child / f"{name}.txt").write_text(name, encoding="utf-8")

        result = scan_directory(str(self.tmp), max_files=1)
        tree_text = build_tree_text(result)

        self.assertIn("a.txt", tree_text)
        self.assertNotIn("📁 b/", tree_text)
        self.assertNotIn("📁 c/", tree_text)
        self.assertTrue(result.scan_stopped)

    def test_level_truncation_reports_hidden_items(self):
        for i in range(3):
            (self.tmp / f"{i}.txt").write_text("x", encoding="utf-8")

        result = scan_directory(str(self.tmp), max_files=-1, max_items_per_level=2)
        tree_text = build_tree_text(result)

        self.assertTrue(result.truncated)
        self.assertEqual(result.truncated_levels, 1)
        self.assertEqual(result.truncated_items, 2)
        self.assertIn("maxItemsPerLevel", describe_truncation(result))
        self.assertIn("输出已截断", tree_text)
        self.assertIn("└── (还有 2 项未显示)", tree_text)

    def test_long_directory_display_name_keeps_real_path_for_recursion(self):
        long_name = "a" * 90
        child_dir = self.tmp / long_name
        child_dir.mkdir()
        (child_dir / "inside.txt").write_text("x", encoding="utf-8")

        result = scan_directory(str(self.tmp), max_files=-1)

        self.assertEqual(result.total_files, 1)
        self.assertEqual(result.total_dirs, 1)
        self.assertEqual(result.root.children[0].children[0].name, "inside.txt")

    def test_source_filter_includes_extensionless_source_filenames(self):
        (self.tmp / "Dockerfile").write_text("FROM scratch", encoding="utf-8")
        (self.tmp / "Makefile").write_text("all:", encoding="utf-8")
        (self.tmp / "photo.png").write_text("x", encoding="utf-8")

        result = scan_directory(
            str(self.tmp),
            include_ext=SOURCE_CODE_EXTENSIONS,
            include_names=SOURCE_CODE_FILENAMES,
        )

        names = {child.name for child in result.root.children}
        self.assertEqual(names, {"Dockerfile", "Makefile"})

    def test_empty_extension_filter_matches_no_files(self):
        (self.tmp / "a.py").write_text("x", encoding="utf-8")

        result = scan_directory(str(self.tmp), include_ext=set())

        self.assertEqual(result.total_files, 0)
        self.assertEqual(result.root.children, [])

    def test_prune_empty_dirs_after_active_filtering(self):
        child_dir = self.tmp / "logs"
        child_dir.mkdir()
        (child_dir / "debug.log").write_text("x", encoding="utf-8")

        result = scan_directory(
            str(self.tmp),
            exclude_files={"debug.log"},
            prune_empty_dirs=True,
        )

        self.assertEqual(result.root.children, [])

    def test_prune_keeps_directories_that_were_empty_before_filtering(self):
        empty_dir = self.tmp / "empty"
        empty_dir.mkdir()
        logs_dir = self.tmp / "logs"
        logs_dir.mkdir()
        (logs_dir / "debug.log").write_text("x", encoding="utf-8")

        result = scan_directory(
            str(self.tmp),
            exclude_files={"debug.log"},
            prune_empty_dirs=True,
        )

        self.assertEqual([child.name for child in result.root.children], ["empty"])

    def test_generated_output_names_can_be_excluded(self):
        (self.tmp / "directory_tree.txt").write_text("old", encoding="utf-8")
        (self.tmp / "keep.txt").write_text("keep", encoding="utf-8")

        result = scan_directory(
            str(self.tmp),
            exclude_files=set(GENERATED_OUTPUT_FILENAMES),
            max_files=-1,
        )

        names = {child.name for child in result.root.children}
        self.assertEqual(names, {"keep.txt"})

    def test_long_unc_path_uses_unc_prefix(self):
        path = "\\\\server\\share\\" + ("a" * 260)

        normalized = _normalize_path(path)

        self.assertTrue(normalized.startswith("\\\\?\\UNC\\server\\share\\"))

    def test_long_relative_path_is_made_absolute_before_prefix(self):
        path = "a" * 260

        normalized = _normalize_path(path)

        self.assertTrue(normalized.startswith("\\\\?\\"))
        self.assertTrue(Path(normalized[4:]).is_absolute())

    def test_drive_root_display_name_is_not_empty(self):
        self.assertEqual(_root_display_name("C:\\"), "C:")

    def test_extreme_depth_is_truncated_before_recursion_limit(self):
        current = self.tmp
        for i in range(15):
            current = current / f"d{i}"
            current.mkdir()

        with mock.patch("copytree.scanner.sys.getrecursionlimit", return_value=25):
            result = scan_directory(str(self.tmp), max_files=-1)

        tree_text = build_tree_text(result)
        self.assertTrue(result.depth_limited)
        self.assertIn("目录层级过深", describe_truncation(result))
        self.assertIn("目录层级过深，后续未扫描", tree_text)

    def test_negative_max_depth_behaves_like_zero(self):
        (self.tmp / "a").mkdir()
        (self.tmp / "a" / "b.txt").write_text("x", encoding="utf-8")

        result_neg = scan_directory(str(self.tmp), max_files=-1, max_depth=-2)
        result_zero = scan_directory(str(self.tmp), max_files=-1, max_depth=0)

        self.assertEqual(result_neg.total_files, 0)
        self.assertEqual(result_neg.total_dirs, 0)
        self.assertEqual(result_neg.root.children, [])
        self.assertFalse(result_neg.truncated)
        self.assertEqual(result_neg.total_files, result_zero.total_files)
        self.assertEqual(result_neg.total_dirs, result_zero.total_dirs)


if __name__ == "__main__":
    unittest.main()
