"""
Unit tests for CSV delimiter auto-detection functionality.
"""

import pytest
import tempfile
from pathlib import Path

from shopify_tool.core import detect_csv_delimiter


class TestDelimiterDetection:
    """Tests for detect_csv_delimiter function."""

    def test_detect_comma_delimiter(self):
        """Test detection of comma delimiter."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, encoding='utf-8') as f:
            f.write("Name,Age,City\n")
            f.write("John,30,New York\n")
            f.write("Jane,25,Los Angeles\n")
            temp_path = f.name

        try:
            delimiter = detect_csv_delimiter(temp_path)
            assert delimiter == ','
        finally:
            Path(temp_path).unlink()

    def test_detect_semicolon_delimiter(self):
        """Test detection of semicolon delimiter."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, encoding='utf-8') as f:
            f.write("SKU;Stock;Price\n")
            f.write("SKU-001;100;29.99\n")
            f.write("SKU-002;50;39.99\n")
            temp_path = f.name

        try:
            delimiter = detect_csv_delimiter(temp_path)
            assert delimiter == ';'
        finally:
            Path(temp_path).unlink()

    def test_detect_tab_delimiter(self):
        """Test detection of tab delimiter."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, encoding='utf-8') as f:
            f.write("Order\tProduct\tQuantity\n")
            f.write("1001\tLaptop\t2\n")
            f.write("1002\tMouse\t5\n")
            temp_path = f.name

        try:
            delimiter = detect_csv_delimiter(temp_path)
            assert delimiter == '\t'
        finally:
            Path(temp_path).unlink()

    def test_detect_pipe_delimiter(self):
        """Test detection of pipe delimiter."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, encoding='utf-8') as f:
            f.write("ID|Name|Status\n")
            f.write("1|Product A|Active\n")
            f.write("2|Product B|Inactive\n")
            temp_path = f.name

        try:
            delimiter = detect_csv_delimiter(temp_path)
            assert delimiter == '|'
        finally:
            Path(temp_path).unlink()

    def test_empty_file(self):
        """Test handling of empty file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, encoding='utf-8') as f:
            temp_path = f.name

        try:
            delimiter = detect_csv_delimiter(temp_path)
            # Should return default comma
            assert delimiter == ','
        finally:
            Path(temp_path).unlink()

    def test_single_column_file(self):
        """Test file with single column (no delimiters)."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, encoding='utf-8') as f:
            f.write("SingleColumn\n")
            f.write("Value1\n")
            f.write("Value2\n")
            temp_path = f.name

        try:
            delimiter = detect_csv_delimiter(temp_path)
            # Should return default comma
            assert delimiter == ','
        finally:
            Path(temp_path).unlink()

    def test_mixed_delimiters_semicolon_dominant(self):
        """Test file with mixed delimiters where semicolon is more common."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, encoding='utf-8') as f:
            # Semicolons used as delimiter, commas in content
            f.write("Name;Address;Price\n")
            f.write("Product A;123 Main St, Suite 100;$29.99\n")
            f.write("Product B;456 Oak Ave, Floor 2;$39.99\n")
            temp_path = f.name

        try:
            delimiter = detect_csv_delimiter(temp_path)
            assert delimiter == ';'
        finally:
            Path(temp_path).unlink()

    def test_quoted_fields_with_commas(self):
        """Test CSV with quoted fields containing commas."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, encoding='utf-8') as f:
            f.write('Name,Description,Price\n')
            f.write('"Product A","High quality, durable",29.99\n')
            f.write('"Product B","Compact, portable",39.99\n')
            temp_path = f.name

        try:
            delimiter = detect_csv_delimiter(temp_path)
            assert delimiter == ','
        finally:
            Path(temp_path).unlink()

    def test_file_with_bom(self):
        """Test file with UTF-8 BOM."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, encoding='utf-8-sig') as f:
            f.write("SKU;Stock;Location\n")
            f.write("A001;100;Warehouse A\n")
            f.write("B002;50;Warehouse B\n")
            temp_path = f.name

        try:
            delimiter = detect_csv_delimiter(temp_path)
            assert delimiter == ';'
        finally:
            Path(temp_path).unlink()

    def test_real_world_stock_file_semicolon(self):
        """Test with real-world stock file format (semicolon)."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, encoding='utf-8') as f:
            f.write("SKU;Warehouse_Location;Available_Quantity;Reserved_Quantity\n")
            f.write("SKU-12345;MAIN-A1;150;10\n")
            f.write("SKU-67890;MAIN-B2;75;5\n")
            f.write("SKU-11111;WAREHOUSE-C3;200;20\n")
            temp_path = f.name

        try:
            delimiter = detect_csv_delimiter(temp_path)
            assert delimiter == ';'
        finally:
            Path(temp_path).unlink()

    def test_real_world_stock_file_comma(self):
        """Test with real-world stock file format (comma)."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, encoding='utf-8') as f:
            f.write("SKU,Warehouse_Location,Available_Quantity,Reserved_Quantity\n")
            f.write("SKU-12345,MAIN-A1,150,10\n")
            f.write("SKU-67890,MAIN-B2,75,5\n")
            f.write("SKU-11111,WAREHOUSE-C3,200,20\n")
            temp_path = f.name

        try:
            delimiter = detect_csv_delimiter(temp_path)
            assert delimiter == ','
        finally:
            Path(temp_path).unlink()

    def test_real_world_orders_file(self):
        """Test with real-world orders file format."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, encoding='utf-8') as f:
            f.write("Order_Number,SKU,Product_Name,Quantity,Shipping_Provider\n")
            f.write("1001,SKU-A,Product A,2,DHL\n")
            f.write("1002,SKU-B,Product B,1,UPS\n")
            f.write("1003,SKU-C,Product C,3,FedEx\n")
            temp_path = f.name

        try:
            delimiter = detect_csv_delimiter(temp_path)
            assert delimiter == ','
        finally:
            Path(temp_path).unlink()

    def test_latin1_encoding(self):
        """Test file with latin-1 encoding."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, encoding='latin-1') as f:
            f.write("Nom;Prénom;Ville\n")
            f.write("Dupont;François;Paris\n")
            f.write("Martin;René;Lyon\n")
            temp_path = f.name

        try:
            delimiter = detect_csv_delimiter(temp_path)
            assert delimiter == ';'
        finally:
            Path(temp_path).unlink()

    def test_small_sample_size(self):
        """Test with very small file (fewer lines than sample size)."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, encoding='utf-8') as f:
            f.write("A;B;C\n")
            f.write("1;2;3\n")
            temp_path = f.name

        try:
            delimiter = detect_csv_delimiter(temp_path)
            assert delimiter == ';'
        finally:
            Path(temp_path).unlink()

    def test_large_file_detection(self):
        """Test that detection works efficiently on large files (only reads sample)."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, encoding='utf-8') as f:
            f.write("Col1;Col2;Col3;Col4;Col5\n")
            # Write many rows but only first few should be read
            for i in range(1000):
                f.write(f"Val{i}A;Val{i}B;Val{i}C;Val{i}D;Val{i}E\n")
            temp_path = f.name

        try:
            delimiter = detect_csv_delimiter(temp_path)
            assert delimiter == ';'
        finally:
            Path(temp_path).unlink()

    def test_custom_sample_size(self):
        """Test detection with custom sample size."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, encoding='utf-8') as f:
            f.write("A,B,C\n")
            f.write("1,2,3\n")
            f.write("4,5,6\n")
            temp_path = f.name

        try:
            # Use sample_size of 2 (header + 1 data row)
            delimiter = detect_csv_delimiter(temp_path, sample_size=2)
            assert delimiter == ','
        finally:
            Path(temp_path).unlink()
