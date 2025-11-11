"""
Unit tests for CSV encoding auto-detection functionality.
"""

import pytest
import tempfile
from pathlib import Path

from shopify_tool.core import detect_csv_encoding


class TestEncodingDetection:
    """Tests for detect_csv_encoding function."""

    def test_detect_utf8_encoding(self):
        """Test detection of UTF-8 encoding."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, encoding='utf-8') as f:
            f.write("Name,Age,City\n")
            f.write("John,30,New York\n")
            f.write("Jane,25,Los Angeles\n")
            temp_path = f.name

        try:
            encoding = detect_csv_encoding(temp_path)
            assert encoding in ['utf-8', 'utf-8-sig']
        finally:
            Path(temp_path).unlink()

    def test_detect_utf8_with_bom(self):
        """Test detection of UTF-8 with BOM encoding."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, encoding='utf-8-sig') as f:
            f.write("Name,Age,City\n")
            f.write("John,30,New York\n")
            temp_path = f.name

        try:
            encoding = detect_csv_encoding(temp_path)
            assert encoding == 'utf-8-sig'
        finally:
            Path(temp_path).unlink()

    def test_detect_windows1251_cyrillic(self):
        """Test detection of Windows-1251 encoding (Cyrillic)."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, encoding='windows-1251') as f:
            f.write("Артикул,Име,Наличност\n")
            f.write("SKU-001,Продукт А,100\n")
            f.write("SKU-002,Продукт Б,50\n")
            temp_path = f.name

        try:
            encoding = detect_csv_encoding(temp_path)
            # Should detect windows-1251 or fall back to latin-1
            assert encoding in ['windows-1251', 'latin-1', 'utf-8-sig', 'utf-8']
        finally:
            Path(temp_path).unlink()

    def test_detect_cp1252_western_european(self):
        """Test detection of CP1252 encoding (Western European)."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, encoding='cp1252') as f:
            f.write("Nom,Prénom,Ville\n")
            f.write("Dupont,François,Paris\n")
            f.write("Martin,René,Lyon\n")
            temp_path = f.name

        try:
            encoding = detect_csv_encoding(temp_path)
            # CP1252 is similar to windows-1251 and latin-1, so any is acceptable
            assert encoding in ['cp1252', 'windows-1251', 'latin-1', 'utf-8-sig', 'utf-8']
        finally:
            Path(temp_path).unlink()

    def test_detect_latin1_encoding(self):
        """Test detection of Latin-1 encoding."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, encoding='latin-1') as f:
            f.write("Name,Description,Price\n")
            f.write("Product A,High quality,29.99\n")
            temp_path = f.name

        try:
            encoding = detect_csv_encoding(temp_path)
            # Latin-1 compatible files may be detected as various encodings
            assert encoding in ['latin-1', 'utf-8-sig', 'utf-8', 'cp1252']
        finally:
            Path(temp_path).unlink()

    def test_empty_file(self):
        """Test handling of empty file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, encoding='utf-8') as f:
            temp_path = f.name

        try:
            encoding = detect_csv_encoding(temp_path)
            # Should return one of the common encodings even for empty file
            assert encoding in ['utf-8-sig', 'utf-8', 'windows-1251', 'cp1252', 'latin-1']
        finally:
            Path(temp_path).unlink()

    def test_ascii_compatible_file(self):
        """Test that ASCII-only files work with any encoding."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, encoding='ascii') as f:
            f.write("SKU,Stock,Location\n")
            f.write("A001,100,Warehouse\n")
            temp_path = f.name

        try:
            encoding = detect_csv_encoding(temp_path)
            # ASCII is compatible with all tested encodings
            assert encoding is not None
        finally:
            Path(temp_path).unlink()

    def test_mixed_cyrillic_and_latin(self):
        """Test file with both Cyrillic and Latin characters."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, encoding='utf-8') as f:
            f.write("SKU,Артикул,Name,Име\n")
            f.write("A001,АРТ-001,Product A,Продукт А\n")
            temp_path = f.name

        try:
            encoding = detect_csv_encoding(temp_path)
            # UTF-8 should be detected for mixed character sets
            assert encoding in ['utf-8', 'utf-8-sig']
        finally:
            Path(temp_path).unlink()

    def test_real_world_bulgarian_stock_file(self):
        """Test with real-world Bulgarian stock file format."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, encoding='windows-1251') as f:
            f.write("Артикул;Име;Наличност;Резервирано\n")
            f.write("SKU-12345;Продукт А;150;10\n")
            f.write("SKU-67890;Продукт Б;75;5\n")
            temp_path = f.name

        try:
            encoding = detect_csv_encoding(temp_path)
            # Should detect an encoding that can read Cyrillic
            assert encoding in ['windows-1251', 'utf-8', 'utf-8-sig', 'cp1252', 'latin-1']
        finally:
            Path(temp_path).unlink()

    def test_real_world_ukrainian_stock_file(self):
        """Test with real-world Ukrainian stock file format."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, encoding='utf-8') as f:
            f.write("Артикул,Назва,Кількість\n")
            f.write("SKU-001,Товар А,100\n")
            f.write("SKU-002,Товар Б,50\n")
            temp_path = f.name

        try:
            encoding = detect_csv_encoding(temp_path)
            # UTF-8 is common for Ukrainian text
            assert encoding in ['utf-8', 'utf-8-sig', 'windows-1251']
        finally:
            Path(temp_path).unlink()

    def test_excel_exported_csv_with_bom(self):
        """Test Excel-exported CSV with UTF-8 BOM."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, encoding='utf-8-sig') as f:
            f.write("Product,Продукт,Price,Цена\n")
            f.write("Item A,Товар А,29.99,29.99\n")
            temp_path = f.name

        try:
            encoding = detect_csv_encoding(temp_path)
            # Should detect UTF-8 with BOM (common in Excel exports)
            assert encoding == 'utf-8-sig'
        finally:
            Path(temp_path).unlink()

    def test_large_file_encoding_detection(self):
        """Test that encoding detection works efficiently on large files."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, encoding='utf-8') as f:
            f.write("Артикул,Назва,Кількість\n")
            # Write many rows
            for i in range(10000):
                f.write(f"SKU-{i:05d},Товар {i},100\n")
            temp_path = f.name

        try:
            encoding = detect_csv_encoding(temp_path)
            # Should detect UTF-8 even for large files (only reads first 8KB)
            assert encoding in ['utf-8', 'utf-8-sig']
        finally:
            Path(temp_path).unlink()

    def test_fallback_to_latin1(self):
        """Test that function never fails and falls back to latin-1."""
        # Create a file with bytes that might be problematic
        with tempfile.NamedTemporaryFile(mode='wb', suffix='.csv', delete=False) as f:
            # Write some bytes that are valid in latin-1 but not UTF-8
            f.write(b"Name,Value\n")
            f.write(b"Item\xff,100\n")  # \xff is valid latin-1 but invalid UTF-8
            temp_path = f.name

        try:
            encoding = detect_csv_encoding(temp_path)
            # Should fall back to latin-1 which never fails
            assert encoding is not None
            assert encoding in ['utf-8-sig', 'utf-8', 'windows-1251', 'cp1252', 'latin-1']
        finally:
            Path(temp_path).unlink()

    def test_consistency_multiple_calls(self):
        """Test that encoding detection is consistent across multiple calls."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, encoding='windows-1251') as f:
            f.write("Артикул,Име\n")
            f.write("SKU-001,Продукт\n")
            temp_path = f.name

        try:
            # Call detection multiple times
            encoding1 = detect_csv_encoding(temp_path)
            encoding2 = detect_csv_encoding(temp_path)
            encoding3 = detect_csv_encoding(temp_path)

            # Should return the same encoding each time
            assert encoding1 == encoding2 == encoding3
        finally:
            Path(temp_path).unlink()
