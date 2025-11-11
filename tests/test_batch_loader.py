"""
Unit tests for batch_loader module.

Tests cover:
1. Single file loading
2. Multiple files loading
3. Duplicate detection and removal
4. Different file structures (error handling)
5. Empty folder handling
"""

import pytest
import pandas as pd
from pathlib import Path
import tempfile
import shutil

from shopify_tool.batch_loader import (
    discover_csv_files,
    validate_csv_structure,
    load_and_merge_csvs,
    load_orders_from_folder,
    BatchLoaderResult
)


@pytest.fixture
def temp_folder():
    """Create a temporary folder for testing."""
    temp_dir = tempfile.mkdtemp()
    yield Path(temp_dir)
    # Cleanup
    shutil.rmtree(temp_dir)


@pytest.fixture
def sample_orders_df():
    """Create a sample orders DataFrame."""
    return pd.DataFrame({
        'Order_Number': ['1001', '1002', '1003'],
        'SKU': ['SKU-A', 'SKU-B', 'SKU-C'],
        'Product_Name': ['Product A', 'Product B', 'Product C'],
        'Quantity': [1, 2, 1],
        'Shipping_Provider': ['DHL', 'UPS', 'DHL']
    })


class TestDiscoverCsvFiles:
    """Tests for discover_csv_files function."""

    def test_discover_csv_files_empty_folder(self, temp_folder):
        """Test discovering files in an empty folder."""
        files = discover_csv_files(temp_folder)
        assert len(files) == 0

    def test_discover_csv_files_with_csv_files(self, temp_folder):
        """Test discovering CSV files."""
        # Create test CSV files
        (temp_folder / "file1.csv").touch()
        (temp_folder / "file2.csv").touch()
        (temp_folder / "file3.csv").touch()
        (temp_folder / "notcsv.txt").touch()

        files = discover_csv_files(temp_folder)
        assert len(files) == 3
        assert all(f.suffix == '.csv' for f in files)

    def test_discover_csv_files_sorted(self, temp_folder):
        """Test that discovered files are sorted."""
        # Create files in non-alphabetical order
        (temp_folder / "c.csv").touch()
        (temp_folder / "a.csv").touch()
        (temp_folder / "b.csv").touch()

        files = discover_csv_files(temp_folder)
        file_names = [f.name for f in files]
        assert file_names == ['a.csv', 'b.csv', 'c.csv']

    def test_discover_csv_files_not_a_directory(self, temp_folder):
        """Test error when path is not a directory."""
        file_path = temp_folder / "file.csv"
        file_path.touch()

        with pytest.raises(ValueError, match="not a directory"):
            discover_csv_files(file_path)


class TestValidateCsvStructure:
    """Tests for validate_csv_structure function."""

    def test_validate_empty_list(self, temp_folder):
        """Test validation with empty file list."""
        is_valid, error = validate_csv_structure([], ["Order_Number"])
        assert not is_valid
        assert "No CSV files found" in error

    def test_validate_single_file_valid(self, temp_folder, sample_orders_df):
        """Test validation with a single valid file."""
        csv_file = temp_folder / "orders.csv"
        sample_orders_df.to_csv(csv_file, index=False)

        required_cols = ['Order_Number', 'SKU', 'Product_Name']
        is_valid, error = validate_csv_structure([csv_file], required_cols)

        assert is_valid
        assert error is None

    def test_validate_single_file_missing_columns(self, temp_folder, sample_orders_df):
        """Test validation with missing required columns."""
        csv_file = temp_folder / "orders.csv"
        sample_orders_df.to_csv(csv_file, index=False)

        required_cols = ['Order_Number', 'SKU', 'Missing_Column']
        is_valid, error = validate_csv_structure([csv_file], required_cols)

        assert not is_valid
        assert "Missing_Column" in error

    def test_validate_multiple_files_same_structure(self, temp_folder, sample_orders_df):
        """Test validation with multiple files having the same structure."""
        file1 = temp_folder / "orders1.csv"
        file2 = temp_folder / "orders2.csv"
        file3 = temp_folder / "orders3.csv"

        sample_orders_df.to_csv(file1, index=False)
        sample_orders_df.to_csv(file2, index=False)
        sample_orders_df.to_csv(file3, index=False)

        required_cols = ['Order_Number', 'SKU']
        is_valid, error = validate_csv_structure([file1, file2, file3], required_cols)

        assert is_valid
        assert error is None

    def test_validate_multiple_files_different_structure(self, temp_folder, sample_orders_df):
        """Test validation with files having different structures."""
        file1 = temp_folder / "orders1.csv"
        file2 = temp_folder / "orders2.csv"

        sample_orders_df.to_csv(file1, index=False)

        # Create a file with different columns
        different_df = pd.DataFrame({
            'Order_Number': ['1001'],
            'SKU': ['SKU-A'],
            'Different_Column': ['Value']
        })
        different_df.to_csv(file2, index=False)

        required_cols = ['Order_Number', 'SKU']
        is_valid, error = validate_csv_structure([file1, file2], required_cols)

        assert not is_valid
        assert "different structure" in error

    def test_validate_corrupted_file(self, temp_folder):
        """Test validation with a corrupted file."""
        csv_file = temp_folder / "corrupted.csv"
        csv_file.write_text("This is not a valid CSV file\n\x00\x00\x00")

        required_cols = ['Order_Number']
        is_valid, error = validate_csv_structure([csv_file], required_cols)

        assert not is_valid
        # Pandas can still read the file but won't have the required columns
        assert "missing required columns" in error or "Error reading" in error


class TestLoadAndMergeCsvs:
    """Tests for load_and_merge_csvs function."""

    def test_load_single_file(self, temp_folder, sample_orders_df):
        """Test loading a single CSV file."""
        csv_file = temp_folder / "orders.csv"
        sample_orders_df.to_csv(csv_file, index=False)

        result = load_and_merge_csvs([csv_file])

        assert isinstance(result, BatchLoaderResult)
        assert result.files_count == 1
        assert result.total_orders == 3
        assert result.duplicates_removed == 0
        assert len(result.df) == 3

    def test_load_multiple_files(self, temp_folder, sample_orders_df):
        """Test loading multiple CSV files."""
        file1 = temp_folder / "orders1.csv"
        file2 = temp_folder / "orders2.csv"

        df1 = sample_orders_df.copy()
        df2 = pd.DataFrame({
            'Order_Number': ['1004', '1005'],
            'SKU': ['SKU-D', 'SKU-E'],
            'Product_Name': ['Product D', 'Product E'],
            'Quantity': [1, 1],
            'Shipping_Provider': ['DHL', 'UPS']
        })

        df1.to_csv(file1, index=False)
        df2.to_csv(file2, index=False)

        result = load_and_merge_csvs([file1, file2])

        assert result.files_count == 2
        assert result.total_orders == 5
        assert result.duplicates_removed == 0
        assert len(result.df) == 5

    def test_load_with_duplicates(self, temp_folder, sample_orders_df):
        """Test loading files with duplicate order numbers."""
        file1 = temp_folder / "orders1.csv"
        file2 = temp_folder / "orders2.csv"

        df1 = sample_orders_df.copy()
        # Create duplicate orders
        df2 = sample_orders_df.copy()
        df2.loc[0, 'SKU'] = 'SKU-X'  # Same order number, different SKU

        df1.to_csv(file1, index=False)
        df2.to_csv(file2, index=False)

        result = load_and_merge_csvs([file1, file2])

        assert result.files_count == 2
        assert result.duplicates_removed == 3  # All 3 orders were duplicated
        assert result.total_orders == 3  # Only unique orders remain
        # First occurrence should be kept
        assert 'SKU-A' in result.df['SKU'].values
        assert 'SKU-X' not in result.df['SKU'].values

    def test_load_no_files(self, temp_folder):
        """Test loading with no files provided."""
        with pytest.raises(ValueError, match="No CSV files provided"):
            load_and_merge_csvs([])

    def test_load_with_custom_delimiter(self, temp_folder):
        """Test loading files with custom delimiter."""
        csv_file = temp_folder / "stock.csv"

        df = pd.DataFrame({
            'SKU': ['SKU-A', 'SKU-B'],
            'Stock': [10, 20]
        })
        df.to_csv(csv_file, index=False, sep=';')

        result = load_and_merge_csvs([csv_file], delimiter=';')

        assert result.total_orders == 2
        assert 'SKU' in result.df.columns

    def test_load_file_with_error(self, temp_folder):
        """Test loading a file that causes an error."""
        # Create a truly unreadable file by making it a directory
        csv_file = temp_folder / "corrupted.csv"
        csv_file.mkdir()  # Make it a directory instead of a file

        with pytest.raises(ValueError, match="Failed to load file"):
            load_and_merge_csvs([csv_file])

    def test_deduplication_without_order_column(self, temp_folder):
        """Test deduplication when Order_Number column doesn't exist."""
        csv_file = temp_folder / "data.csv"

        df = pd.DataFrame({
            'SKU': ['SKU-A', 'SKU-B', 'SKU-A'],
            'Stock': [10, 20, 10]
        })
        df.to_csv(csv_file, index=False)

        result = load_and_merge_csvs([csv_file], order_number_column='Order_Number')

        # Should not remove duplicates if column doesn't exist
        assert result.total_orders == 3
        assert result.duplicates_removed == 0


class TestLoadOrdersFromFolder:
    """Tests for load_orders_from_folder function (complete workflow)."""

    def test_successful_load_single_file(self, temp_folder, sample_orders_df):
        """Test successful loading from folder with single file."""
        csv_file = temp_folder / "orders.csv"
        sample_orders_df.to_csv(csv_file, index=False)

        required_cols = ['Order_Number', 'SKU']
        result = load_orders_from_folder(temp_folder, required_cols)

        assert result.files_count == 1
        assert result.total_orders == 3
        assert not result.df.empty

    def test_successful_load_multiple_files(self, temp_folder, sample_orders_df):
        """Test successful loading from folder with multiple files."""
        for i in range(3):
            csv_file = temp_folder / f"orders{i}.csv"
            sample_orders_df.to_csv(csv_file, index=False)

        required_cols = ['Order_Number', 'SKU']
        result = load_orders_from_folder(temp_folder, required_cols)

        assert result.files_count == 3
        # Due to duplicates, should only have 3 unique orders
        assert result.total_orders == 3
        assert result.duplicates_removed == 6  # 3 files * 3 orders - 3 unique

    def test_empty_folder(self, temp_folder):
        """Test error when folder is empty."""
        required_cols = ['Order_Number']

        with pytest.raises(ValueError, match="No CSV files found"):
            load_orders_from_folder(temp_folder, required_cols)

    def test_validation_failure_missing_columns(self, temp_folder):
        """Test error when files are missing required columns."""
        csv_file = temp_folder / "orders.csv"
        df = pd.DataFrame({
            'Order_Number': ['1001'],
            'SKU': ['SKU-A']
        })
        df.to_csv(csv_file, index=False)

        required_cols = ['Order_Number', 'SKU', 'Missing_Column']

        with pytest.raises(ValueError, match="CSV validation failed"):
            load_orders_from_folder(temp_folder, required_cols)

    def test_validation_failure_different_structures(self, temp_folder, sample_orders_df):
        """Test error when files have different structures."""
        file1 = temp_folder / "orders1.csv"
        file2 = temp_folder / "orders2.csv"

        sample_orders_df.to_csv(file1, index=False)

        different_df = pd.DataFrame({
            'Order_Number': ['1001'],
            'Different_Column': ['Value']
        })
        different_df.to_csv(file2, index=False)

        required_cols = ['Order_Number']

        with pytest.raises(ValueError, match="different structure"):
            load_orders_from_folder(temp_folder, required_cols)

    def test_custom_delimiter(self, temp_folder):
        """Test loading with custom delimiter."""
        csv_file = temp_folder / "stock.csv"

        df = pd.DataFrame({
            'SKU': ['SKU-A', 'SKU-B'],
            'Stock': [10, 20]
        })
        df.to_csv(csv_file, index=False, sep=';')

        required_cols = ['SKU', 'Stock']
        result = load_orders_from_folder(
            temp_folder,
            required_cols,
            order_number_column='SKU',
            delimiter=';'
        )

        assert result.files_count == 1
        assert result.total_orders == 2

    def test_large_dataset_with_duplicates(self, temp_folder):
        """Test with a larger dataset to verify performance and correctness."""
        # Create 5 files with overlapping data
        for i in range(5):
            csv_file = temp_folder / f"orders{i}.csv"
            orders = []
            for j in range(100):
                # Create some overlap between files
                order_num = 1000 + (j * 5) + i  # Overlapping pattern
                orders.append({
                    'Order_Number': str(order_num),
                    'SKU': f'SKU-{order_num}',
                    'Product_Name': f'Product {order_num}',
                    'Quantity': 1
                })
            pd.DataFrame(orders).to_csv(csv_file, index=False)

        required_cols = ['Order_Number', 'SKU']
        result = load_orders_from_folder(temp_folder, required_cols)

        assert result.files_count == 5
        # Each file has 100 orders, but they overlap
        assert result.total_orders > 100  # Should have merged some
        assert result.total_orders <= 500  # But not all 500


class TestBatchLoaderResult:
    """Tests for BatchLoaderResult class."""

    def test_result_creation(self):
        """Test creating a BatchLoaderResult object."""
        df = pd.DataFrame({'Order_Number': ['1001', '1002']})
        result = BatchLoaderResult(
            df=df,
            files_count=2,
            total_orders=2,
            duplicates_removed=1,
            files_loaded=['file1.csv', 'file2.csv']
        )

        assert result.files_count == 2
        assert result.total_orders == 2
        assert result.duplicates_removed == 1
        assert len(result.files_loaded) == 2

    def test_get_summary(self):
        """Test get_summary method."""
        df = pd.DataFrame({'Order_Number': ['1001', '1002']})
        result = BatchLoaderResult(
            df=df,
            files_count=3,
            total_orders=247,
            duplicates_removed=2,
            files_loaded=['file1.csv', 'file2.csv', 'file3.csv']
        )

        summary = result.get_summary()

        assert "Files loaded: 3" in summary
        assert "Total orders: 247" in summary
        assert "Duplicates removed: 2" in summary
