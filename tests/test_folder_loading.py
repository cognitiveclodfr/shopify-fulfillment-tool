"""
Integration tests for folder loading functionality.
"""
import pytest
from pathlib import Path
from unittest.mock import Mock, MagicMock


# Mock MainWindow for FileHandler tests
class MockMainWindow:
    def __init__(self):
        self.orders_file_path = None
        self.stock_file_path = None
        self.orders_file_path_label = Mock()
        self.orders_file_status_label = Mock()
        self.stock_file_path_label = Mock()
        self.stock_file_status_label = Mock()
        self.run_analysis_button = Mock()
        self.orders_recursive_checkbox = Mock()
        self.stock_recursive_checkbox = Mock()
        self.orders_remove_duplicates_checkbox = Mock()
        self.stock_remove_duplicates_checkbox = Mock()
        self.orders_file_list_widget = Mock()
        self.stock_file_list_widget = Mock()
        self.orders_file_count_label = Mock()
        self.stock_file_count_label = Mock()
        self.session_path = None
        self.active_profile_config = {
            "column_mappings": {
                "orders": {
                    "Name": "Order_Number",
                    "Lineitem sku": "SKU",
                    "Lineitem quantity": "Quantity",
                    "Shipping Method": "Shipping_Method"
                },
                "stock": {
                    "Артикул": "SKU",
                    "Наличност": "Stock"
                }
            },
            "settings": {
                "orders_csv_delimiter": ",",
                "stock_csv_delimiter": ";"
            }
        }


def test_scan_folder_non_recursive(tmp_path):
    """Test scanning folder without subfolders."""
    from gui.file_handler import FileHandler

    # Create test structure
    (tmp_path / "file1.csv").write_text("Name,SKU\n1001,A")
    (tmp_path / "file2.csv").write_text("Name,SKU\n1002,B")
    (tmp_path / "subdir").mkdir()
    (tmp_path / "subdir" / "file3.csv").write_text("Name,SKU\n1003,C")

    # Mock FileHandler
    mock_mw = MockMainWindow()
    handler = FileHandler(mock_mw)

    # Scan (non-recursive)
    files = handler.scan_folder_for_csv(str(tmp_path), recursive=False)

    # Should find 2 files (not the one in subdir)
    assert len(files) == 2
    assert any("file1.csv" in f for f in files)
    assert any("file2.csv" in f for f in files)
    assert not any("file3.csv" in f for f in files)


def test_scan_folder_recursive(tmp_path):
    """Test scanning folder with subfolders."""
    from gui.file_handler import FileHandler

    # Same structure
    (tmp_path / "file1.csv").write_text("Name,SKU\n1001,A")
    (tmp_path / "subdir").mkdir()
    (tmp_path / "subdir" / "file2.csv").write_text("Name,SKU\n1002,B")

    mock_mw = MockMainWindow()
    handler = FileHandler(mock_mw)

    # Scan (recursive)
    files = handler.scan_folder_for_csv(str(tmp_path), recursive=True)

    # Should find both
    assert len(files) == 2


def test_validate_multiple_files_all_valid(tmp_path):
    """Test validation when all files valid."""
    from gui.file_handler import FileHandler

    # Create valid files
    for i in range(3):
        (tmp_path / f"file{i}.csv").write_text(
            "Name,Lineitem sku,Lineitem quantity,Shipping Method\n"
            f"100{i},SKU-{i},1,Express"
        )

    # Mock
    mock_mw = MockMainWindow()
    handler = FileHandler(mock_mw)

    files = list(tmp_path.glob("*.csv"))
    valid, invalid, rows = handler.validate_multiple_files(
        [str(f) for f in files],
        "orders"
    )

    assert len(valid) == 3
    assert len(invalid) == 0
    assert rows == 3


def test_validate_multiple_files_some_invalid(tmp_path):
    """Test validation with mixed valid/invalid."""
    from gui.file_handler import FileHandler

    # Valid file
    (tmp_path / "valid.csv").write_text(
        "Name,Lineitem sku,Lineitem quantity,Shipping Method\n1001,A,1,Express"
    )

    # Invalid file (missing columns)
    (tmp_path / "invalid.csv").write_text("Name,SKU\n1002,B")

    mock_mw = MockMainWindow()
    handler = FileHandler(mock_mw)

    files = list(tmp_path.glob("*.csv"))
    valid, invalid, rows = handler.validate_multiple_files(
        [str(f) for f in files],
        "orders"
    )

    assert len(valid) == 1
    assert len(invalid) == 1
    assert any("invalid.csv" in str(fp) for fp, _ in invalid)


def test_validate_stock_files(tmp_path):
    """Test validation for stock files."""
    from gui.file_handler import FileHandler

    # Create valid stock files
    (tmp_path / "stock1.csv").write_text("Артикул;Наличност\nSKU-A;10")
    (tmp_path / "stock2.csv").write_text("Артикул;Наличност\nSKU-B;20")

    mock_mw = MockMainWindow()
    handler = FileHandler(mock_mw)

    files = list(tmp_path.glob("*.csv"))
    valid, invalid, rows = handler.validate_multiple_files(
        [str(f) for f in files],
        "stock"
    )

    assert len(valid) == 2
    assert len(invalid) == 0
    assert rows == 2


def test_merge_and_save_files_orders(tmp_path):
    """Test merging and saving orders files."""
    from gui.file_handler import FileHandler

    # Create test files
    (tmp_path / "orders1.csv").write_text(
        "Name,Lineitem sku,Lineitem quantity,Shipping Method\n"
        "1001,SKU-A,2,Express"
    )
    (tmp_path / "orders2.csv").write_text(
        "Name,Lineitem sku,Lineitem quantity,Shipping Method\n"
        "1002,SKU-B,1,Standard"
    )

    mock_mw = MockMainWindow()
    mock_mw.session_path = str(tmp_path / "session")
    mock_mw.orders_remove_duplicates_checkbox.isChecked.return_value = False

    handler = FileHandler(mock_mw)

    files = [str(tmp_path / "orders1.csv"), str(tmp_path / "orders2.csv")]

    # Merge
    merged_path = handler.merge_and_save_files(
        files,
        "orders",
        str(tmp_path)
    )

    # Check merged file exists
    assert Path(merged_path).exists()

    # Check merged file has correct content
    import pandas as pd
    merged_df = pd.read_csv(merged_path)
    assert len(merged_df) == 2
    assert "_source_file" in merged_df.columns


def test_merge_with_duplicates_removal(tmp_path):
    """Test merging with duplicate removal."""
    from gui.file_handler import FileHandler

    # Create test files with duplicates
    (tmp_path / "orders1.csv").write_text(
        "Name,Lineitem sku,Lineitem quantity,Shipping Method\n"
        "1001,SKU-A,2,Express"
    )
    (tmp_path / "orders2.csv").write_text(
        "Name,Lineitem sku,Lineitem quantity,Shipping Method\n"
        "1001,SKU-A,2,Express"  # Duplicate
    )

    mock_mw = MockMainWindow()
    mock_mw.session_path = str(tmp_path / "session")
    mock_mw.orders_remove_duplicates_checkbox.isChecked.return_value = True

    handler = FileHandler(mock_mw)

    files = [str(tmp_path / "orders1.csv"), str(tmp_path / "orders2.csv")]

    # Merge
    merged_path = handler.merge_and_save_files(
        files,
        "orders",
        str(tmp_path)
    )

    # Check merged file has only 1 row (duplicate removed)
    import pandas as pd
    merged_df = pd.read_csv(merged_path)
    assert len(merged_df) == 1


def test_scan_empty_folder(tmp_path):
    """Test scanning empty folder."""
    from gui.file_handler import FileHandler

    mock_mw = MockMainWindow()
    handler = FileHandler(mock_mw)

    # Scan empty folder
    files = handler.scan_folder_for_csv(str(tmp_path), recursive=False)

    # Should find no files
    assert len(files) == 0


def test_scan_folder_with_non_csv_files(tmp_path):
    """Test scanning folder with non-CSV files."""
    from gui.file_handler import FileHandler

    # Create non-CSV files
    (tmp_path / "file1.txt").write_text("text file")
    (tmp_path / "file2.xlsx").write_text("excel file")
    (tmp_path / "file3.csv").write_text("Name,SKU\n1001,A")

    mock_mw = MockMainWindow()
    handler = FileHandler(mock_mw)

    # Scan
    files = handler.scan_folder_for_csv(str(tmp_path), recursive=False)

    # Should find only CSV file
    assert len(files) == 1
    assert files[0].endswith("file3.csv")
