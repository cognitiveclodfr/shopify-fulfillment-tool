"""
Unit tests for the set_decoder module.

Tests cover:
1. Basic set decoding functionality
2. Quantity multiplication
3. Mixed orders (sets + regular SKUs)
4. CSV import/export functionality
5. Error handling and validation
"""

import pytest
import pandas as pd
import sys
import os
import tempfile

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from shopify_tool.set_decoder import (
    decode_sets_in_orders,
    import_sets_from_csv,
    export_sets_to_csv
)


class TestDecodeSimpleSet:
    """Test basic set decoding with single order containing one set."""

    def test_decode_simple_set(self):
        """Test decoding 1 order with 1 set (3 components)."""
        # Setup: Create order with a set
        orders_df = pd.DataFrame({
            "Order_Number": ["ORDER-001"],
            "SKU": ["TEST-SET-A"],
            "Quantity": [1],
            "Shipping_Method": ["Express"]
        })

        set_decoders = {
            "TEST-SET-A": [
                {"sku": "SKU-COMP-1", "quantity": 1},
                {"sku": "SKU-COMP-2", "quantity": 1},
                {"sku": "SKU-COMP-3", "quantity": 1}
            ]
        }

        # Execute
        result = decode_sets_in_orders(orders_df, set_decoders)

        # Assert: Should have 3 rows (one per component)
        assert len(result) == 3, f"Expected 3 rows, got {len(result)}"

        # Check that all components are present
        result_skus = sorted(result["SKU"].tolist())
        expected_skus = ["SKU-COMP-1", "SKU-COMP-2", "SKU-COMP-3"]
        assert result_skus == expected_skus, f"Expected SKUs {expected_skus}, got {result_skus}"

        # Check quantities (should all be 1)
        assert all(result["Quantity"] == 1), "All quantities should be 1"

        # Check tracking columns
        assert all(result["Original_SKU"] == "TEST-SET-A"), "Original_SKU should be TEST-SET-A"
        assert all(result["Original_Quantity"] == 1), "Original_Quantity should be 1"
        assert all(result["Is_Set_Component"] == True), "All should be marked as set components"

        # Check other columns preserved
        assert all(result["Order_Number"] == "ORDER-001"), "Order number should be preserved"
        assert all(result["Shipping_Method"] == "Express"), "Shipping method should be preserved"


class TestDecodeMultipleQuantity:
    """Test quantity multiplication when ordering multiple sets."""

    def test_decode_multiple_quantity(self):
        """Test set with qty=3, components should have quantities multiplied."""
        orders_df = pd.DataFrame({
            "Order_Number": ["ORDER-002"],
            "SKU": ["TEST-SET-B"],
            "Quantity": [3]
        })

        set_decoders = {
            "TEST-SET-B": [
                {"sku": "SKU-HAT", "quantity": 1},
                {"sku": "SKU-GLOVES", "quantity": 2}  # 2x per set
            ]
        }

        # Execute
        result = decode_sets_in_orders(orders_df, set_decoders)

        # Assert: Should have 2 rows (one per component type)
        assert len(result) == 2, f"Expected 2 rows, got {len(result)}"

        # Check quantity multiplication
        hat_row = result[result["SKU"] == "SKU-HAT"].iloc[0]
        assert hat_row["Quantity"] == 3, "HAT quantity should be 3 (1 x 3)"

        gloves_row = result[result["SKU"] == "SKU-GLOVES"].iloc[0]
        assert gloves_row["Quantity"] == 6, "GLOVES quantity should be 6 (2 x 3)"

        # Check tracking columns
        assert all(result["Original_SKU"] == "TEST-SET-B")
        assert all(result["Original_Quantity"] == 3)
        assert all(result["Is_Set_Component"] == True)


class TestDecodeMixedOrders:
    """Test processing orders with both sets and regular SKUs."""

    def test_decode_mixed_orders(self):
        """Test 2 sets + 1 regular SKU in same batch."""
        orders_df = pd.DataFrame({
            "Order_Number": ["ORDER-001", "ORDER-002", "ORDER-003"],
            "SKU": ["SET-WINTER", "REGULAR-SKU", "SET-SUMMER"],
            "Quantity": [1, 5, 2]
        })

        set_decoders = {
            "SET-WINTER": [
                {"sku": "COMP-W1", "quantity": 1},
                {"sku": "COMP-W2", "quantity": 1}
            ],
            "SET-SUMMER": [
                {"sku": "COMP-S1", "quantity": 1}
            ]
        }

        # Execute
        result = decode_sets_in_orders(orders_df, set_decoders)

        # Assert: 2 components from SET-WINTER + 1 regular + 1 component from SET-SUMMER = 4 rows
        assert len(result) == 4, f"Expected 4 rows, got {len(result)}"

        # Check regular SKU preserved
        regular_rows = result[result["SKU"] == "REGULAR-SKU"]
        assert len(regular_rows) == 1, "Regular SKU should have 1 row"
        assert regular_rows.iloc[0]["Quantity"] == 5, "Regular quantity should be preserved"
        assert regular_rows.iloc[0]["Is_Set_Component"] == False, "Regular SKU not a set component"
        assert regular_rows.iloc[0]["Original_SKU"] == "REGULAR-SKU", "Original_SKU should be same"

        # Check sets expanded
        set_components = result[result["Is_Set_Component"] == True]
        assert len(set_components) == 3, "Should have 3 set component rows"

        # Check SET-SUMMER quantity multiplication
        summer_comp = result[result["SKU"] == "COMP-S1"]
        assert len(summer_comp) == 1
        assert summer_comp.iloc[0]["Quantity"] == 2, "COMP-S1 quantity should be 2 (1 x 2)"


class TestNoSetsDefined:
    """Test behavior when no sets are defined."""

    def test_no_sets_defined(self):
        """Test with empty set_decoders, orders should be unchanged but with tracking columns."""
        orders_df = pd.DataFrame({
            "Order_Number": ["ORDER-001", "ORDER-002"],
            "SKU": ["SKU-A", "SKU-B"],
            "Quantity": [1, 2]
        })

        set_decoders = {}  # Empty

        # Execute
        result = decode_sets_in_orders(orders_df, set_decoders)

        # Assert: Same number of rows
        assert len(result) == 2, "Should have same number of rows"

        # Check tracking columns added
        assert "Original_SKU" in result.columns, "Should have Original_SKU column"
        assert "Original_Quantity" in result.columns, "Should have Original_Quantity column"
        assert "Is_Set_Component" in result.columns, "Should have Is_Set_Component column"

        # Check all marked as not set components
        assert all(result["Is_Set_Component"] == False), "All should be marked as non-set"

        # Check tracking columns match original
        assert all(result["Original_SKU"] == result["SKU"]), "Original_SKU should match SKU"
        assert all(result["Original_Quantity"] == result["Quantity"]), "Original_Quantity should match Quantity"


class TestImportCSVValid:
    """Test importing set definitions from valid CSV."""

    def test_import_csv_valid(self):
        """Test importing valid CSV with 2 sets."""
        # Create temporary CSV file
        csv_content = """Set_SKU,Component_SKU,Component_Quantity
SET-A,COMP-1,1
SET-A,COMP-2,2
SET-B,COMP-3,1
SET-B,COMP-4,3"""

        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write(csv_content)
            csv_path = f.name

        try:
            # Execute
            result = import_sets_from_csv(csv_path)

            # Assert: Should have 2 sets
            assert len(result) == 2, f"Expected 2 sets, got {len(result)}"
            assert "SET-A" in result, "Should have SET-A"
            assert "SET-B" in result, "Should have SET-B"

            # Check SET-A components
            set_a = result["SET-A"]
            assert len(set_a) == 2, "SET-A should have 2 components"
            assert set_a[0] == {"sku": "COMP-1", "quantity": 1}
            assert set_a[1] == {"sku": "COMP-2", "quantity": 2}

            # Check SET-B components
            set_b = result["SET-B"]
            assert len(set_b) == 2, "SET-B should have 2 components"
            assert set_b[0] == {"sku": "COMP-3", "quantity": 1}
            assert set_b[1] == {"sku": "COMP-4", "quantity": 3}

        finally:
            # Cleanup
            os.unlink(csv_path)


class TestImportCSVMissingColumn:
    """Test error handling when CSV has missing required columns."""

    def test_import_csv_missing_column(self):
        """Test CSV without Component_Quantity column raises ValueError."""
        # Create CSV missing Component_Quantity
        csv_content = """Set_SKU,Component_SKU
SET-A,COMP-1
SET-A,COMP-2"""

        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write(csv_content)
            csv_path = f.name

        try:
            # Execute & Assert: Should raise ValueError
            with pytest.raises(ValueError) as exc_info:
                import_sets_from_csv(csv_path)

            assert "missing required columns" in str(exc_info.value).lower()

        finally:
            # Cleanup
            os.unlink(csv_path)

    def test_import_csv_invalid_quantity(self):
        """Test CSV with non-integer quantity raises ValueError."""
        csv_content = """Set_SKU,Component_SKU,Component_Quantity
SET-A,COMP-1,abc"""

        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write(csv_content)
            csv_path = f.name

        try:
            with pytest.raises(ValueError) as exc_info:
                import_sets_from_csv(csv_path)

            assert "must be integers" in str(exc_info.value).lower()

        finally:
            os.unlink(csv_path)

    def test_import_csv_negative_quantity(self):
        """Test CSV with negative quantity raises ValueError."""
        csv_content = """Set_SKU,Component_SKU,Component_Quantity
SET-A,COMP-1,-1"""

        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write(csv_content)
            csv_path = f.name

        try:
            with pytest.raises(ValueError) as exc_info:
                import_sets_from_csv(csv_path)

            assert "positive integers" in str(exc_info.value).lower()

        finally:
            os.unlink(csv_path)


class TestExportThenImport:
    """Test round-trip: export sets to CSV, then import back."""

    def test_export_then_import(self):
        """Test export → import → same dict (round-trip)."""
        # Original set definitions
        original_sets = {
            "SET-ALPHA": [
                {"sku": "COMP-A", "quantity": 1},
                {"sku": "COMP-B", "quantity": 2}
            ],
            "SET-BETA": [
                {"sku": "COMP-C", "quantity": 3}
            ]
        }

        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            csv_path = f.name

        try:
            # Export
            export_sets_to_csv(original_sets, csv_path)

            # Import
            imported_sets = import_sets_from_csv(csv_path)

            # Assert: Should be identical
            assert imported_sets == original_sets, "Round-trip should preserve data"

            # Check specific values
            assert len(imported_sets) == 2
            assert imported_sets["SET-ALPHA"][0]["sku"] == "COMP-A"
            assert imported_sets["SET-ALPHA"][0]["quantity"] == 1
            assert imported_sets["SET-BETA"][0]["quantity"] == 3

        finally:
            # Cleanup
            if os.path.exists(csv_path):
                os.unlink(csv_path)

    def test_export_empty_sets(self):
        """Test exporting empty dict raises ValueError."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            csv_path = f.name

        try:
            with pytest.raises(ValueError) as exc_info:
                export_sets_to_csv({}, csv_path)

            assert "empty" in str(exc_info.value).lower()

        finally:
            if os.path.exists(csv_path):
                os.unlink(csv_path)


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_empty_dataframe(self):
        """Test with empty orders DataFrame."""
        orders_df = pd.DataFrame(columns=["Order_Number", "SKU", "Quantity"])
        set_decoders = {"SET-A": [{"sku": "COMP-1", "quantity": 1}]}

        result = decode_sets_in_orders(orders_df, set_decoders)

        assert len(result) == 0, "Result should be empty"
        assert "Original_SKU" in result.columns, "Should have tracking columns"

    def test_set_with_no_components(self):
        """Test set with empty components list is skipped."""
        orders_df = pd.DataFrame({
            "Order_Number": ["ORDER-001"],
            "SKU": ["EMPTY-SET"],
            "Quantity": [1]
        })

        set_decoders = {"EMPTY-SET": []}  # Empty components

        result = decode_sets_in_orders(orders_df, set_decoders)

        # Should keep original row but mark as non-set
        assert len(result) == 1
        assert result.iloc[0]["SKU"] == "EMPTY-SET"
        assert result.iloc[0]["Is_Set_Component"] == False

    def test_component_with_invalid_quantity(self):
        """Test component with invalid quantity is skipped."""
        orders_df = pd.DataFrame({
            "Order_Number": ["ORDER-001"],
            "SKU": ["BAD-SET"],
            "Quantity": [1]
        })

        set_decoders = {
            "BAD-SET": [
                {"sku": "GOOD-COMP", "quantity": 1},
                {"sku": "BAD-COMP", "quantity": 0},  # Invalid
                {"sku": "ANOTHER-GOOD", "quantity": 2}
            ]
        }

        result = decode_sets_in_orders(orders_df, set_decoders)

        # Should have 2 rows (bad component skipped)
        assert len(result) == 2
        result_skus = sorted(result["SKU"].tolist())
        assert result_skus == ["ANOTHER-GOOD", "GOOD-COMP"]

    def test_csv_with_duplicate_pairs(self):
        """Test CSV with duplicate (Set_SKU, Component_SKU) pairs - last one wins."""
        csv_content = """Set_SKU,Component_SKU,Component_Quantity
SET-A,COMP-1,1
SET-A,COMP-1,5"""

        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write(csv_content)
            csv_path = f.name

        try:
            result = import_sets_from_csv(csv_path)

            # Should keep last occurrence (quantity 5)
            assert len(result["SET-A"]) == 1
            assert result["SET-A"][0]["quantity"] == 5

        finally:
            os.unlink(csv_path)
