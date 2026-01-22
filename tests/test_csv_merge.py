"""
Unit tests for CSV merge functionality.
"""
import pytest
import pandas as pd
from pathlib import Path
from shopify_tool.csv_utils import merge_csv_files


def test_merge_two_files(tmp_path):
    """Test merging two simple CSV files."""
    # Create test files
    file1 = tmp_path / "file1.csv"
    file1.write_text("Name,SKU,Qty\n1001,SKU-A,2\n1002,SKU-B,1")

    file2 = tmp_path / "file2.csv"
    file2.write_text("Name,SKU,Qty\n2001,SKU-C,3\n2002,SKU-D,1")

    # Merge
    merged = merge_csv_files(
        [str(file1), str(file2)],
        delimiter=",",
        add_source_column=True
    )

    # Assertions
    assert len(merged) == 4
    assert "_source_file" in merged.columns
    assert merged["_source_file"].iloc[0] == "file1.csv"
    assert merged["_source_file"].iloc[2] == "file2.csv"


def test_merge_with_duplicates(tmp_path):
    """Test duplicate removal."""
    file1 = tmp_path / "file1.csv"
    file1.write_text("Name,SKU,Qty\n1001,SKU-A,2")

    file2 = tmp_path / "file2.csv"
    file2.write_text("Name,SKU,Qty\n1001,SKU-A,2")  # Duplicate

    # Merge with duplicate removal
    merged = merge_csv_files(
        [str(file1), str(file2)],
        delimiter=",",
        remove_duplicates=True,
        duplicate_keys=["Name", "SKU"]
    )

    assert len(merged) == 1  # Only one kept


def test_merge_with_dtype(tmp_path):
    """Test that dtype is preserved (SKU as string)."""
    file1 = tmp_path / "file1.csv"
    file1.write_text("Name,SKU,Qty\n1001,5170,2")

    merged = merge_csv_files(
        [str(file1)],
        delimiter=",",
        dtype_dict={"SKU": str}
    )

    # SKU should be string, not float (pandas 2.x uses StringDtype)
    assert merged["SKU"].dtype == object or str(merged["SKU"].dtype).startswith('string')
    assert merged["SKU"].iloc[0] == "5170"  # Not "5170.0"


def test_merge_empty_list():
    """Test that empty file list raises ValueError."""
    with pytest.raises(ValueError, match="No files provided"):
        merge_csv_files([], delimiter=",")


def test_merge_multiple_files(tmp_path):
    """Test merging 3+ files."""
    files = []
    for i in range(5):
        file = tmp_path / f"file{i}.csv"
        file.write_text(f"Name,SKU,Qty\n{1000+i},SKU-{i},{i}")
        files.append(str(file))

    merged = merge_csv_files(files, delimiter=",")

    assert len(merged) == 5
    assert merged["Name"].tolist() == [1000, 1001, 1002, 1003, 1004]


def test_merge_without_source_column(tmp_path):
    """Test merging without source tracking column."""
    file1 = tmp_path / "file1.csv"
    file1.write_text("Name,SKU\n1001,A")

    file2 = tmp_path / "file2.csv"
    file2.write_text("Name,SKU\n1002,B")

    merged = merge_csv_files(
        [str(file1), str(file2)],
        delimiter=",",
        add_source_column=False
    )

    assert "_source_file" not in merged.columns
    assert len(merged) == 2


def test_merge_with_different_delimiters(tmp_path):
    """Test merging files with semicolon delimiter."""
    file1 = tmp_path / "file1.csv"
    file1.write_text("Name;SKU;Qty\n1001;SKU-A;2")

    file2 = tmp_path / "file2.csv"
    file2.write_text("Name;SKU;Qty\n2001;SKU-B;3")

    merged = merge_csv_files(
        [str(file1), str(file2)],
        delimiter=";"
    )

    assert len(merged) == 2
    assert "Name" in merged.columns
    assert merged["Name"].iloc[0] == 1001


def test_merge_preserves_column_order(tmp_path):
    """Test that column order is preserved."""
    file1 = tmp_path / "file1.csv"
    file1.write_text("Col1,Col2,Col3\nA,B,C")

    file2 = tmp_path / "file2.csv"
    file2.write_text("Col1,Col2,Col3\nD,E,F")

    merged = merge_csv_files(
        [str(file1), str(file2)],
        delimiter=",",
        add_source_column=False
    )

    assert list(merged.columns) == ["Col1", "Col2", "Col3"]


def test_merge_invalid_file(tmp_path):
    """Test that invalid file raises exception."""
    file1 = tmp_path / "file1.csv"
    file1.write_text("Name,SKU\n1001,A")

    # Non-existent file
    with pytest.raises(Exception, match="Failed to load"):
        merge_csv_files(
            [str(file1), "/nonexistent/file.csv"],
            delimiter=","
        )


def test_merge_duplicate_removal_all_columns(tmp_path):
    """Test duplicate removal without specifying keys (uses all columns)."""
    file1 = tmp_path / "file1.csv"
    file1.write_text("Name,SKU,Qty\n1001,A,2")

    file2 = tmp_path / "file2.csv"
    file2.write_text("Name,SKU,Qty\n1001,A,2\n1002,B,3")  # One duplicate, one unique

    merged = merge_csv_files(
        [str(file1), str(file2)],
        delimiter=",",
        remove_duplicates=True
    )

    # Should have 2 rows (duplicate removed)
    assert len(merged) == 2
