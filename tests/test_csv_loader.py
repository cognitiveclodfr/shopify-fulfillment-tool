"""Unit tests for csv_loader module.

Tests cover:
- Single file loading
- Multiple file loading from folder
- Duplicate detection and removal
- Column mapping (WooCommerce vs Shopify)
- Delimiter detection
- Structure validation
- Error handling
"""

import pytest
import pandas as pd
from pathlib import Path
import tempfile
import shutil

from shopify_tool.csv_loader import (
    load_single_csv,
    load_orders_from_folder,
    detect_csv_delimiter,
    detect_export_format,
    normalize_columns,
    validate_csv_structure,
    remove_duplicates,
    CSVLoadResult
)


@pytest.fixture
def temp_dir():
    """Create a temporary directory for test files."""
    temp_path = Path(tempfile.mkdtemp())
    yield temp_path
    # Cleanup
    if temp_path.exists():
        shutil.rmtree(temp_path)


@pytest.fixture
def shopify_csv_data():
    """Sample Shopify export data (no duplicates)."""
    return pd.DataFrame({
        "Name": ["#1001", "#1002", "#1003", "#1004"],
        "Lineitem sku": ["SKU-A", "SKU-B", "SKU-C", "SKU-D"],
        "Lineitem name": ["Product A", "Product B", "Product C", "Product D"],
        "Lineitem quantity": [1, 2, 1, 3],
        "Shipping Method": ["Standard", "Standard", "Express", "Standard"]
    })


@pytest.fixture
def woocommerce_csv_data():
    """Sample WooCommerce export data (no duplicates)."""
    return pd.DataFrame({
        "Order ID": ["1001", "1002", "1003", "1004"],
        "Lineitem sku": ["SKU-A", "SKU-B", "SKU-C", "SKU-D"],
        "Lineitem name": ["Product A", "Product B", "Product C", "Product D"],
        "Lineitem quantity": [1, 2, 1, 3],
        "Shipping Method": ["Standard", "Standard", "Express", "Standard"]
    })


class TestDelimiterDetection:
    """Test CSV delimiter detection."""

    def test_detect_comma_delimiter(self, temp_dir):
        """Test detection of comma delimiter."""
        csv_file = temp_dir / "test_comma.csv"
        csv_file.write_text("Name,SKU,Quantity\nOrder1,SKU-A,5\n")

        delimiter = detect_csv_delimiter(csv_file)
        assert delimiter == ','

    def test_detect_semicolon_delimiter(self, temp_dir):
        """Test detection of semicolon delimiter."""
        csv_file = temp_dir / "test_semicolon.csv"
        csv_file.write_text("Name;SKU;Quantity\nOrder1;SKU-A;5\n")

        delimiter = detect_csv_delimiter(csv_file)
        assert delimiter == ';'

    def test_detect_tab_delimiter(self, temp_dir):
        """Test detection of tab delimiter."""
        csv_file = temp_dir / "test_tab.csv"
        csv_file.write_text("Name\tSKU\tQuantity\nOrder1\tSKU-A\t5\n")

        delimiter = detect_csv_delimiter(csv_file)
        assert delimiter == '\t'

    def test_empty_file_default_delimiter(self, temp_dir):
        """Test that empty file returns default comma delimiter."""
        csv_file = temp_dir / "empty.csv"
        csv_file.write_text("")

        delimiter = detect_csv_delimiter(csv_file)
        assert delimiter == ','


class TestFormatDetection:
    """Test export format detection."""

    def test_detect_shopify_format(self, shopify_csv_data):
        """Test Shopify format detection."""
        format_type = detect_export_format(shopify_csv_data)
        assert format_type == "shopify"

    def test_detect_woocommerce_format(self, woocommerce_csv_data):
        """Test WooCommerce format detection."""
        format_type = detect_export_format(woocommerce_csv_data)
        assert format_type == "woocommerce"

    def test_detect_unknown_format(self):
        """Test unknown format detection."""
        df = pd.DataFrame({
            "Unknown1": [1, 2],
            "Unknown2": [3, 4]
        })
        format_type = detect_export_format(df)
        assert format_type is None


class TestColumnNormalization:
    """Test column normalization."""

    def test_normalize_shopify_columns(self, shopify_csv_data):
        """Test normalization of Shopify columns."""
        normalized = normalize_columns(shopify_csv_data, "shopify")

        assert "Order_Number" in normalized.columns
        assert "SKU" in normalized.columns
        assert "Product_Name" in normalized.columns
        assert "Quantity" in normalized.columns
        assert "Shipping_Method" in normalized.columns

    def test_normalize_woocommerce_columns(self, woocommerce_csv_data):
        """Test normalization of WooCommerce columns."""
        normalized = normalize_columns(woocommerce_csv_data, "woocommerce")

        assert "Order_Number" in normalized.columns
        assert "SKU" in normalized.columns
        assert "Product_Name" in normalized.columns
        assert "Quantity" in normalized.columns
        assert "Shipping_Method" in normalized.columns


class TestDuplicateRemoval:
    """Test duplicate detection and removal."""

    def test_remove_duplicates_by_order(self):
        """Test removing duplicate orders."""
        df = pd.DataFrame({
            "Order_Number": ["#1001", "#1001", "#1002", "#1003"],
            "SKU": ["SKU-A", "SKU-A", "SKU-B", "SKU-C"],
            "Quantity": [1, 1, 2, 3]
        })

        deduped, count = remove_duplicates(df, "Order_Number")

        assert count == 1
        assert len(deduped) == 3
        assert list(deduped["Order_Number"]) == ["#1001", "#1002", "#1003"]

    def test_no_duplicates(self):
        """Test with no duplicates."""
        df = pd.DataFrame({
            "Order_Number": ["#1001", "#1002", "#1003"],
            "SKU": ["SKU-A", "SKU-B", "SKU-C"]
        })

        deduped, count = remove_duplicates(df, "Order_Number")

        assert count == 0
        assert len(deduped) == 3

    def test_missing_order_column(self):
        """Test when order column doesn't exist."""
        df = pd.DataFrame({
            "SKU": ["SKU-A", "SKU-B"],
            "Quantity": [1, 2]
        })

        deduped, count = remove_duplicates(df, "Order_Number")

        assert count == 0
        assert len(deduped) == 2


class TestStructureValidation:
    """Test CSV structure validation."""

    def test_validate_compatible_structure(self, temp_dir):
        """Test validation of files with same structure."""
        df1 = pd.DataFrame({"A": [1, 2], "B": [3, 4]})
        df2 = pd.DataFrame({"A": [5, 6], "B": [7, 8]})

        files_data = [
            (temp_dir / "file1.csv", df1),
            (temp_dir / "file2.csv", df2)
        ]

        is_valid, errors = validate_csv_structure(files_data)

        assert is_valid is True
        assert len(errors) == 0

    def test_validate_incompatible_structure(self, temp_dir):
        """Test validation of files with different structures."""
        df1 = pd.DataFrame({"A": [1, 2], "B": [3, 4]})
        df2 = pd.DataFrame({"A": [5, 6], "C": [7, 8]})  # Different column

        files_data = [
            (temp_dir / "file1.csv", df1),
            (temp_dir / "file2.csv", df2)
        ]

        is_valid, errors = validate_csv_structure(files_data)

        assert is_valid is False
        assert len(errors) > 0
        assert "file2.csv" in errors[0]

    def test_validate_empty_list(self):
        """Test validation with no files."""
        is_valid, errors = validate_csv_structure([])

        assert is_valid is False
        assert "No files" in errors[0]


class TestSingleFileLoading:
    """Test loading single CSV files."""

    def test_load_shopify_csv(self, temp_dir, shopify_csv_data):
        """Test loading a Shopify CSV file."""
        csv_file = temp_dir / "shopify_orders.csv"
        shopify_csv_data.to_csv(csv_file, index=False)

        result = load_single_csv(csv_file)

        assert result.success is True
        assert result.dataframe is not None
        assert len(result.dataframe) == 4
        assert result.detected_format == "shopify"
        assert result.files_processed == 1

    def test_load_woocommerce_csv(self, temp_dir, woocommerce_csv_data):
        """Test loading a WooCommerce CSV file."""
        csv_file = temp_dir / "woocommerce_orders.csv"
        woocommerce_csv_data.to_csv(csv_file, index=False)

        result = load_single_csv(csv_file)

        assert result.success is True
        assert result.dataframe is not None
        assert len(result.dataframe) == 4
        assert result.detected_format == "woocommerce"

    def test_load_csv_with_semicolon(self, temp_dir):
        """Test loading CSV with semicolon delimiter."""
        csv_file = temp_dir / "semicolon.csv"
        csv_file.write_text("Name;SKU;Quantity\n#1001;SKU-A;5\n#1002;SKU-B;3\n")

        result = load_single_csv(csv_file)

        assert result.success is True
        assert result.delimiter == ';'
        assert len(result.dataframe) == 2

    def test_load_nonexistent_file(self, temp_dir):
        """Test loading a file that doesn't exist."""
        csv_file = temp_dir / "nonexistent.csv"

        result = load_single_csv(csv_file)

        assert result.success is False
        assert len(result.errors) > 0
        assert "not found" in result.errors[0].lower()

    def test_load_empty_file(self, temp_dir):
        """Test loading an empty CSV file."""
        csv_file = temp_dir / "empty.csv"
        csv_file.write_text("")

        result = load_single_csv(csv_file)

        assert result.success is False
        assert len(result.errors) > 0


class TestMultiFileLoading:
    """Test loading multiple files from folder."""

    def test_load_single_file_from_folder(self, temp_dir, shopify_csv_data):
        """Test loading folder with single file."""
        csv_file = temp_dir / "orders1.csv"
        shopify_csv_data.to_csv(csv_file, index=False)

        result = load_orders_from_folder(temp_dir)

        assert result.success is True
        assert result.files_processed == 1
        assert result.total_orders == 4

    def test_load_multiple_files_from_folder(self, temp_dir):
        """Test loading folder with multiple files."""
        # Create 3 files with different orders
        df1 = pd.DataFrame({
            "Name": ["#1001", "#1002"],
            "Lineitem sku": ["SKU-A", "SKU-B"],
            "Lineitem name": ["Product A", "Product B"],
            "Lineitem quantity": [1, 2],
            "Shipping Method": ["Standard", "Express"]
        })
        df2 = pd.DataFrame({
            "Name": ["#1003", "#1004"],
            "Lineitem sku": ["SKU-C", "SKU-D"],
            "Lineitem name": ["Product C", "Product D"],
            "Lineitem quantity": [3, 1],
            "Shipping Method": ["Standard", "Standard"]
        })
        df3 = pd.DataFrame({
            "Name": ["#1005", "#1006"],
            "Lineitem sku": ["SKU-E", "SKU-F"],
            "Lineitem name": ["Product E", "Product F"],
            "Lineitem quantity": [2, 4],
            "Shipping Method": ["Express", "Standard"]
        })

        (temp_dir / "orders1.csv").write_text(df1.to_csv(index=False))
        (temp_dir / "orders2.csv").write_text(df2.to_csv(index=False))
        (temp_dir / "orders3.csv").write_text(df3.to_csv(index=False))

        result = load_orders_from_folder(temp_dir)

        assert result.success is True
        assert result.files_processed == 3
        assert result.total_orders == 6  # 2 orders per file * 3 files

    def test_load_folder_with_duplicates(self, temp_dir):
        """Test loading files with duplicate orders."""
        # File 1
        df1 = pd.DataFrame({
            "Name": ["#1001", "#1002"],
            "Lineitem sku": ["SKU-A", "SKU-B"],
            "Lineitem name": ["Product A", "Product B"],
            "Lineitem quantity": [1, 2],
            "Shipping Method": ["Standard", "Express"]
        })
        (temp_dir / "file1.csv").write_text(df1.to_csv(index=False))

        # File 2 with duplicate order #1001
        df2 = pd.DataFrame({
            "Name": ["#1001", "#1003"],
            "Lineitem sku": ["SKU-A", "SKU-C"],
            "Lineitem name": ["Product A", "Product C"],
            "Lineitem quantity": [1, 3],
            "Shipping Method": ["Standard", "Standard"]
        })
        (temp_dir / "file2.csv").write_text(df2.to_csv(index=False))

        result = load_orders_from_folder(temp_dir)

        assert result.success is True
        assert result.files_processed == 2
        assert result.duplicates_removed > 0
        assert result.total_orders == 3  # #1001, #1002, #1003 (one duplicate removed)
        assert len(result.warnings) > 0

    def test_load_folder_with_different_structures(self, temp_dir):
        """Test loading files with incompatible structures (should fail)."""
        # File 1 - Shopify format
        df1 = pd.DataFrame({
            "Name": ["#1001"],
            "Lineitem sku": ["SKU-A"],
            "Lineitem quantity": [1]
        })
        (temp_dir / "file1.csv").write_text(df1.to_csv(index=False))

        # File 2 - Different columns
        df2 = pd.DataFrame({
            "OrderID": ["#1002"],
            "SKU": ["SKU-B"],
            "Qty": [2]
        })
        (temp_dir / "file2.csv").write_text(df2.to_csv(index=False))

        result = load_orders_from_folder(temp_dir)

        assert result.success is False
        assert len(result.errors) > 0

    def test_load_empty_folder(self, temp_dir):
        """Test loading folder with no CSV files."""
        result = load_orders_from_folder(temp_dir)

        assert result.success is False
        assert "No CSV files" in result.errors[0]

    def test_load_nonexistent_folder(self, temp_dir):
        """Test loading folder that doesn't exist."""
        result = load_orders_from_folder(temp_dir / "nonexistent")

        assert result.success is False
        assert "not found" in result.errors[0].lower()


class TestCSVLoadResult:
    """Test CSVLoadResult class."""

    def test_result_initialization(self):
        """Test result object initialization."""
        result = CSVLoadResult()

        assert result.success is False
        assert result.dataframe is None
        assert result.files_processed == 0
        assert result.total_orders == 0
        assert result.duplicates_removed == 0
        assert len(result.warnings) == 0
        assert len(result.errors) == 0

    def test_add_warning(self):
        """Test adding warnings."""
        result = CSVLoadResult()
        result.add_warning("Test warning")

        assert len(result.warnings) == 1
        assert result.warnings[0] == "Test warning"

    def test_add_error(self):
        """Test adding errors."""
        result = CSVLoadResult()
        result.add_error("Test error")

        assert len(result.errors) == 1
        assert result.errors[0] == "Test error"

    def test_get_summary_success(self):
        """Test success summary."""
        result = CSVLoadResult()
        result.success = True
        result.files_processed = 3
        result.total_orders = 100
        result.duplicates_removed = 5
        result.detected_format = "shopify"

        summary = result.get_summary()

        assert "✓" in summary
        assert "3 file(s)" in summary
        assert "100" in summary
        assert "5" in summary
        assert "SHOPIFY" in summary

    def test_get_summary_failure(self):
        """Test failure summary."""
        result = CSVLoadResult()
        result.success = False
        result.add_error("File not found")

        summary = result.get_summary()

        assert "✗" in summary
        assert "Failed" in summary
        assert "File not found" in summary


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
