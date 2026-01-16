"""
Unit tests for PDF Processor (Reference Labels).
"""

import pytest
import tempfile
from pathlib import Path
from datetime import datetime

from shopify_tool.pdf_processor import (
    process_reference_labels,
    load_csv_mapping,
    match_reference,
    normalize_text,
    extract_postone_number,
    extract_tracking_numbers,
    check_name_presence,
    sort_pages_by_reference,
    create_reference_order_map,
    InvalidPDFError,
    InvalidCSVError,
    PDFProcessorError
)


class TestTextNormalization:
    """Tests for text normalization functions."""

    def test_normalize_text_basic(self):
        """Test basic text normalization."""
        assert normalize_text("Hello  World") == "hello world"
        assert normalize_text("  Trim   Spaces  ") == "trim spaces"
        assert normalize_text("UPPERCASE") == "uppercase"

    def test_normalize_text_empty(self):
        """Test normalization of empty/None text."""
        assert normalize_text("") == ""
        assert normalize_text(None) == ""

    def test_normalize_text_special_chars(self):
        """Test normalization with special characters."""
        assert normalize_text("São Paulo") == "são paulo"
        assert normalize_text("O'Brien") == "o'brien"


class TestPostOneExtraction:
    """Tests for PostOne number extraction."""

    def test_extract_postone_r_number(self):
        """Test extracting R-type PostOne number."""
        text = "Order ID: R1234567890\nShip to: John Doe"
        assert extract_postone_number(text) == "R1234567890"

    def test_extract_postone_p_number(self):
        """Test extracting P-type PostOne number."""
        text = "Package P0987654321 shipped"
        assert extract_postone_number(text) == "P0987654321"

    def test_extract_postone_none(self):
        """Test when no PostOne number present."""
        text = "Random text without PostOne number"
        assert extract_postone_number(text) is None

    def test_extract_postone_invalid_length(self):
        """Test that short numbers are not matched."""
        text = "R123456"  # Too short
        assert extract_postone_number(text) is None


class TestTrackingExtraction:
    """Tests for tracking number extraction."""

    def test_extract_tracking_numbers(self):
        """Test extracting tracking numbers."""
        text = "Tracking: ABC123456789XYZ\nReference: R1234567890"
        numbers = extract_tracking_numbers(text)
        assert "ABC123456789XYZ" in numbers

    def test_extract_tracking_multiple(self):
        """Test extracting multiple tracking numbers."""
        text = "Track1: ABC123456789 Track2: DEF987654321"
        numbers = extract_tracking_numbers(text)
        assert len(numbers) >= 2

    def test_extract_tracking_none(self):
        """Test when no tracking numbers present."""
        text = "Short text"
        numbers = extract_tracking_numbers(text)
        assert len(numbers) == 0


class TestNamePresence:
    """Tests for name presence checking."""

    def test_check_name_present_full(self):
        """Test when full name is present."""
        name = "John Smith"
        text = "Ship to: John Smith\n123 Main Street"
        assert check_name_presence(name, text) is True

    def test_check_name_present_partial(self):
        """Test when partial name is present (>50%)."""
        name = "Maria Garcia Lopez"
        text = "Customer: Maria Garcia"
        assert check_name_presence(name, text) is True

    def test_check_name_not_present(self):
        """Test when name is not present."""
        name = "John Smith"
        text = "Ship to: Jane Doe"
        assert check_name_presence(name, text) is False

    def test_check_name_empty(self):
        """Test with empty name/text."""
        assert check_name_presence("", "text") is False
        assert check_name_presence("name", "") is False


class TestCSVLoading:
    """Tests for CSV mapping loading."""

    def test_load_csv_valid(self, tmp_path):
        """Test loading valid CSV mapping file."""
        csv_content = """Header1,Header2,Header3,H4,H5,H6,Header7
R1234567890,TRACK001,REF001,X,X,X,John Doe
P0987654321,TRACK002,REF002,X,X,X,Jane Smith"""

        csv_file = tmp_path / "mapping.csv"
        csv_file.write_text(csv_content)

        mapping = load_csv_mapping(str(csv_file))

        assert 'by_postone' in mapping
        assert 'R1234567890' in mapping['by_postone']
        assert mapping['by_postone']['R1234567890']['ref'] == 'REF001'
        assert mapping['by_postone']['R1234567890']['name'] == 'John Doe'

    def test_load_csv_empty(self, tmp_path):
        """Test loading empty CSV raises error."""
        csv_file = tmp_path / "empty.csv"
        csv_file.write_text("")

        with pytest.raises(InvalidCSVError):
            load_csv_mapping(str(csv_file))

    def test_load_csv_not_found(self):
        """Test loading non-existent CSV raises error."""
        with pytest.raises(InvalidCSVError):
            load_csv_mapping("nonexistent.csv")


class TestReferenceMatching:
    """Tests for reference matching."""

    def test_match_by_postone(self):
        """Test matching by PostOne ID."""
        mapping = {
            'by_postone': {'R1234567890': {'ref': 'REF001', 'name': 'John Doe'}},
            'by_tracking': {},
            'by_name': {}
        }

        page_text = "Order R1234567890\nJohn Doe\n123 Main St"
        result = match_reference(page_text, mapping)

        assert result is not None
        assert result['ref'] == 'REF001'
        assert result['method'] == 'postone'

    def test_match_by_tracking(self):
        """Test matching by tracking number."""
        mapping = {
            'by_postone': {},
            'by_tracking': {'TRACK123456789': {'ref': 'REF002', 'name': 'Jane Smith'}},
            'by_name': {}
        }

        page_text = "Tracking: TRACK123456789\nJane Smith"
        result = match_reference(page_text, mapping)

        assert result is not None
        assert result['ref'] == 'REF002'
        assert result['method'] == 'tracking'

    def test_match_by_name(self):
        """Test matching by name (fallback)."""
        mapping = {
            'by_postone': {},
            'by_tracking': {},
            'by_name': {'john doe': {'ref': 'REF003', 'name': 'John Doe'}}
        }

        page_text = "Ship to: John Doe\nAddress..."
        result = match_reference(page_text, mapping)

        assert result is not None
        assert result['ref'] == 'REF003'
        assert result['method'] == 'name'

    def test_match_no_match(self):
        """Test when no match found."""
        mapping = {
            'by_postone': {},
            'by_tracking': {},
            'by_name': {}
        }

        page_text = "Random text"
        result = match_reference(page_text, mapping)

        assert result is None


class TestPageSorting:
    """Tests for page sorting by reference."""

    def test_sort_pages_by_reference(self):
        """Test sorting pages by reference number."""
        page_data_list = [
            {'ref': 'REF003', 'original_order': 0},
            {'ref': 'REF001', 'original_order': 1},
            {'ref': 'REF002', 'original_order': 2},
            {'ref': None, 'original_order': 3}
        ]

        sorted_pages = sort_pages_by_reference(page_data_list)

        # First 3 should be sorted by ref number
        assert sorted_pages[0]['ref'] == 'REF001'
        assert sorted_pages[1]['ref'] == 'REF002'
        assert sorted_pages[2]['ref'] == 'REF003'
        # Last should be unmatched
        assert sorted_pages[3]['ref'] is None

    def test_sort_pages_numeric_refs(self):
        """Test sorting with numeric reference numbers."""
        page_data_list = [
            {'ref': '10', 'original_order': 0},
            {'ref': '2', 'original_order': 1},
            {'ref': '1', 'original_order': 2}
        ]

        sorted_pages = sort_pages_by_reference(page_data_list)

        # Should sort numerically, not alphabetically
        assert sorted_pages[0]['ref'] == '1'
        assert sorted_pages[1]['ref'] == '2'
        assert sorted_pages[2]['ref'] == '10'


class TestReferenceOrderMap:
    """Tests for reference order map creation."""

    def test_create_reference_order_map(self):
        """Test creating reference order map."""
        sorted_pages = [
            {'ref': 'REF001', 'original_order': 0},
            {'ref': 'REF001', 'original_order': 1},  # Duplicate ref
            {'ref': 'REF002', 'original_order': 2},
            {'ref': None, 'original_order': 3}
        ]

        order_map = create_reference_order_map(sorted_pages)

        assert order_map['REF001'] == 1
        assert order_map['REF002'] == 2
        assert len(order_map) == 2  # Only unique refs


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
