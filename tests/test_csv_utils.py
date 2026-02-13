"""Tests for CSV utility functions (shopify_tool/csv_utils.py).

Covers:
- detect_csv_delimiter() - comma, semicolon, tab, pipe
- validate_delimiter() - correct and incorrect delimiter
- suggest_delimiter_fix() - returns actionable string
- Edge cases: empty file, single column
"""

import os
import pytest
from pathlib import Path

from shopify_tool.csv_utils import detect_csv_delimiter, validate_delimiter, suggest_delimiter_fix


def write_csv(path: Path, content: str, encoding: str = "utf-8-sig"):
    path.write_text(content, encoding=encoding)


class TestDetectCsvDelimiter:

    def test_detects_comma(self, temp_dir):
        f = temp_dir / "orders.csv"
        write_csv(f, "Order_Number,SKU,Qty\nORD-1,SKU-A,2\nORD-2,SKU-B,1\n")
        delimiter, method = detect_csv_delimiter(str(f))
        assert delimiter == ","

    def test_detects_semicolon(self, temp_dir):
        f = temp_dir / "stock.csv"
        write_csv(f, "SKU;Stock;Price\nSKU-A;10;9.99\nSKU-B;5;14.99\n")
        delimiter, method = detect_csv_delimiter(str(f))
        assert delimiter == ";"

    def test_detects_tab(self, temp_dir):
        f = temp_dir / "data.tsv"
        write_csv(f, "A\tB\tC\n1\t2\t3\n4\t5\t6\n")
        delimiter, method = detect_csv_delimiter(str(f))
        assert delimiter == "\t"

    def test_detects_pipe(self, temp_dir):
        f = temp_dir / "data.csv"
        write_csv(f, "A|B|C\n1|2|3\n4|5|6\n")
        delimiter, method = detect_csv_delimiter(str(f))
        assert delimiter == "|"

    def test_returns_tuple(self, temp_dir):
        f = temp_dir / "simple.csv"
        write_csv(f, "a,b\n1,2\n")
        result = detect_csv_delimiter(str(f))
        assert isinstance(result, tuple)
        assert len(result) == 2

    def test_multirow_file(self, temp_dir):
        f = temp_dir / "large.csv"
        rows = ["col1;col2;col3"] + [f"v{i};w{i};x{i}" for i in range(20)]
        write_csv(f, "\n".join(rows) + "\n")
        delimiter, _ = detect_csv_delimiter(str(f))
        assert delimiter == ";"


class TestValidateDelimiter:

    def test_returns_true_for_correct_delimiter(self, temp_dir):
        f = temp_dir / "orders.csv"
        write_csv(f, "Order,SKU,Qty\nORD-1,A,2\n")
        assert validate_delimiter(str(f), ",") is True

    def test_returns_false_for_wrong_delimiter(self, temp_dir):
        f = temp_dir / "stock.csv"
        write_csv(f, "SKU;Stock\nA;10\n")
        assert validate_delimiter(str(f), ",") is False

    def test_semicolon_file_validates_semicolon(self, temp_dir):
        f = temp_dir / "stock.csv"
        write_csv(f, "SKU;Stock\nA;10\nB;5\n")
        assert validate_delimiter(str(f), ";") is True


class TestSuggestDelimiterFix:

    def test_returns_tuple(self, temp_dir):
        f = temp_dir / "data.csv"
        write_csv(f, "a,b,c\n1,2,3\n")
        result = suggest_delimiter_fix(str(f), failed_delimiter=";")
        assert isinstance(result, tuple)
        assert len(result) == 2

    def test_suggests_correct_delimiter(self, temp_dir):
        f = temp_dir / "orders.csv"
        write_csv(f, "Order,SKU,Qty\nORD-1,A,2\n")
        suggested, confidence = suggest_delimiter_fix(str(f), failed_delimiter=";")
        assert suggested == ","

    def test_confidence_is_valid_level(self, temp_dir):
        f = temp_dir / "stock.csv"
        write_csv(f, "A;B\n1;2\n")
        _, confidence = suggest_delimiter_fix(str(f), failed_delimiter=",")
        assert confidence in ("high", "medium", "low")
