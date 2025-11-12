"""
Integration tests for set/bundle decoder system.

Tests the complete workflow from set definitions through analysis
to ensure sets are properly expanded and processed.
"""

import pytest
import pandas as pd
import sys
import os
import tempfile

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from shopify_tool.analysis import run_analysis
from shopify_tool.set_decoder import import_sets_from_csv


class TestFullWorkflowWithSets:
    """Test complete analysis workflow with sets."""

    def test_full_workflow_with_sets(self):
        """Test full analysis with sets: load → expand → analyze → fulfill."""
        # Create test orders with sets
        orders_df = pd.DataFrame({
            "Order_Number": ["ORDER-001", "ORDER-002"],
            "SKU": ["TEST-SET-A", "SKU-REGULAR"],
            "Quantity": [1, 2],
            "Shipping_Method": ["Express", "Standard"],
            "Shipping_Country": ["US", "UK"]
        })

        # Create test stock
        stock_df = pd.DataFrame({
            "SKU": ["COMP-A", "COMP-B", "SKU-REGULAR"],
            "Product_Name": ["Component A", "Component B", "Regular Item"],
            "Stock": [10, 20, 100]
        })

        # Create history
        history_df = pd.DataFrame(columns=["Order_Number", "Execution_Date"])

        # Set definitions
        set_decoders = {
            "TEST-SET-A": [
                {"sku": "COMP-A", "quantity": 1},
                {"sku": "COMP-B", "quantity": 2}
            ]
        }

        column_mappings = {"set_decoders": set_decoders}

        # Execute analysis
        final_df, summary_present, summary_missing, stats = run_analysis(
            stock_df, orders_df, history_df, column_mappings
        )

        # Verify expansion happened
        assert len(final_df) > len(orders_df), "Sets should be expanded"

        # Check that set components are present
        expanded_skus = set(final_df["SKU"].tolist())
        assert "COMP-A" in expanded_skus, "Component A should be in results"
        assert "COMP-B" in expanded_skus, "Component B should be in results"
        assert "SKU-REGULAR" in expanded_skus, "Regular SKU should be preserved"

        # Check fulfillment status column exists
        assert "Order_Fulfillment_Status" in final_df.columns

        # Verify quantity multiplication for COMP-B (should be 2x)
        comp_b_rows = final_df[final_df["SKU"] == "COMP-B"]
        if not comp_b_rows.empty:
            assert comp_b_rows.iloc[0]["Quantity"] == 2, "COMP-B quantity should be multiplied"

    def test_set_with_missing_component(self):
        """Test set where a component is missing from stock."""
        orders_df = pd.DataFrame({
            "Order_Number": ["ORDER-001"],
            "SKU": ["MISSING-SET"],
            "Quantity": [1],
            "Shipping_Method": ["Express"],
            "Shipping_Country": ["US"]
        })

        # Stock missing one component
        stock_df = pd.DataFrame({
            "SKU": ["COMP-EXISTS"],
            "Product_Name": ["Component Exists"],
            "Stock": [10]
        })

        history_df = pd.DataFrame(columns=["Order_Number", "Execution_Date"])

        set_decoders = {
            "MISSING-SET": [
                {"sku": "COMP-EXISTS", "quantity": 1},
                {"sku": "COMP-MISSING", "quantity": 1}  # This doesn't exist in stock
            ]
        }

        column_mappings = {"set_decoders": set_decoders}

        # Execute analysis
        final_df, summary_present, summary_missing, stats = run_analysis(
            stock_df, orders_df, history_df, column_mappings
        )

        # Verify set was expanded
        assert "COMP-EXISTS" in final_df["SKU"].tolist()
        assert "COMP-MISSING" in final_df["SKU"].tolist()

        # Order should not be fully fulfillable
        order_status = final_df[final_df["Order_Number"] == "ORDER-001"]["Order_Fulfillment_Status"].unique()
        # Should be "Not Fulfillable" because missing component
        assert any("Not" in str(status) or "Partially" in str(status) for status in order_status)

    def test_set_with_insufficient_stock(self):
        """Test set where stock exists but is insufficient."""
        orders_df = pd.DataFrame({
            "Order_Number": ["ORDER-001"],
            "SKU": ["LOW-STOCK-SET"],
            "Quantity": [10],  # Ordering 10 sets
            "Shipping_Method": ["Express"],
            "Shipping_Country": ["US"]
        })

        # Stock exists but insufficient for 10 sets
        stock_df = pd.DataFrame({
            "SKU": ["COMP-X"],
            "Product_Name": ["Component X"],
            "Stock": [5]  # Only 5, but need 10
        })

        history_df = pd.DataFrame(columns=["Order_Number", "Execution_Date"])

        set_decoders = {
            "LOW-STOCK-SET": [
                {"sku": "COMP-X", "quantity": 1}
            ]
        }

        column_mappings = {"set_decoders": set_decoders}

        # Execute analysis
        final_df, summary_present, summary_missing, stats = run_analysis(
            stock_df, orders_df, history_df, column_mappings
        )

        # Verify expansion (10 sets × 1 component = 10 quantity needed)
        comp_x_rows = final_df[final_df["SKU"] == "COMP-X"]
        assert not comp_x_rows.empty
        assert comp_x_rows.iloc[0]["Quantity"] == 10

        # Order should not be fulfillable due to insufficient stock
        order_status = final_df[final_df["Order_Number"] == "ORDER-001"]["Order_Fulfillment_Status"].unique()
        assert any("Not" in str(status) or "Partially" in str(status) for status in order_status)

    def test_mixed_orders_sets_and_regular(self):
        """Test processing mixed orders (sets + regular items)."""
        orders_df = pd.DataFrame({
            "Order_Number": ["O1", "O2", "O3", "O4", "O5"],
            "SKU": ["SET-A", "SET-B", "REG-1", "REG-2", "SET-A"],
            "Quantity": [1, 1, 5, 3, 2],
            "Shipping_Method": ["Express"] * 5,
            "Shipping_Country": ["US"] * 5
        })

        stock_df = pd.DataFrame({
            "SKU": ["COMP-A1", "COMP-A2", "COMP-B1", "REG-1", "REG-2"],
            "Product_Name": ["CA1", "CA2", "CB1", "R1", "R2"],
            "Stock": [100, 100, 100, 100, 100]
        })

        history_df = pd.DataFrame(columns=["Order_Number", "Execution_Date"])

        set_decoders = {
            "SET-A": [
                {"sku": "COMP-A1", "quantity": 1},
                {"sku": "COMP-A2", "quantity": 1}
            ],
            "SET-B": [
                {"sku": "COMP-B1", "quantity": 1}
            ]
        }

        column_mappings = {"set_decoders": set_decoders}

        # Execute analysis
        final_df, summary_present, summary_missing, stats = run_analysis(
            stock_df, orders_df, history_df, column_mappings
        )

        # Verify both types processed
        # Original: 5 orders → After expansion: more rows
        assert len(final_df) > 5

        # Check set components present
        expanded_skus = set(final_df["SKU"].tolist())
        assert "COMP-A1" in expanded_skus
        assert "COMP-A2" in expanded_skus
        assert "COMP-B1" in expanded_skus

        # Check regular SKUs preserved
        assert "REG-1" in expanded_skus
        assert "REG-2" in expanded_skus

        # Verify all orders have fulfillment status
        assert "Order_Fulfillment_Status" in final_df.columns

    def test_multiple_sets_per_order(self):
        """Test order containing multiple different sets."""
        # Simulate multi-item order with 2 different sets
        orders_df = pd.DataFrame({
            "Order_Number": ["ORDER-MULTI", "ORDER-MULTI"],
            "SKU": ["SET-ALPHA", "SET-BETA"],
            "Quantity": [1, 1],
            "Shipping_Method": ["Express", "Express"],
            "Shipping_Country": ["US", "US"]
        })

        stock_df = pd.DataFrame({
            "SKU": ["ALPHA-1", "ALPHA-2", "BETA-1", "BETA-2"],
            "Product_Name": ["A1", "A2", "B1", "B2"],
            "Stock": [50, 50, 50, 50]
        })

        history_df = pd.DataFrame(columns=["Order_Number", "Execution_Date"])

        set_decoders = {
            "SET-ALPHA": [
                {"sku": "ALPHA-1", "quantity": 1},
                {"sku": "ALPHA-2", "quantity": 1}
            ],
            "SET-BETA": [
                {"sku": "BETA-1", "quantity": 2},
                {"sku": "BETA-2", "quantity": 1}
            ]
        }

        column_mappings = {"set_decoders": set_decoders}

        # Execute analysis
        final_df, summary_present, summary_missing, stats = run_analysis(
            stock_df, orders_df, history_df, column_mappings
        )

        # Verify both sets expanded
        expanded_skus = set(final_df["SKU"].tolist())
        assert "ALPHA-1" in expanded_skus
        assert "ALPHA-2" in expanded_skus
        assert "BETA-1" in expanded_skus
        assert "BETA-2" in expanded_skus

        # All components should belong to same order
        multi_order_rows = final_df[final_df["Order_Number"] == "ORDER-MULTI"]
        assert len(multi_order_rows) == 4, "Should have 4 component rows"

        # Check quantity for BETA-1 (should be 2 because component_quantity=2)
        beta1_rows = final_df[(final_df["SKU"] == "BETA-1") & (final_df["Order_Number"] == "ORDER-MULTI")]
        if not beta1_rows.empty:
            assert beta1_rows.iloc[0]["Quantity"] == 2


class TestEdgeCasesIntegration:
    """Test edge cases in integration."""

    def test_empty_set_decoders(self):
        """Test that analysis works normally with no sets defined."""
        orders_df = pd.DataFrame({
            "Order_Number": ["O1"],
            "SKU": ["SKU-A"],
            "Quantity": [1],
            "Shipping_Method": ["Express"],
            "Shipping_Country": ["US"]
        })

        stock_df = pd.DataFrame({
            "SKU": ["SKU-A"],
            "Product_Name": ["Product A"],
            "Stock": [10]
        })

        history_df = pd.DataFrame(columns=["Order_Number", "Execution_Date"])

        # No set_decoders
        column_mappings = {}

        # Execute analysis - should not crash
        final_df, summary_present, summary_missing, stats = run_analysis(
            stock_df, orders_df, history_df, column_mappings
        )

        # Should work normally
        assert len(final_df) == 1
        assert final_df.iloc[0]["SKU"] == "SKU-A"

        # Check fulfillment works
        assert "Order_Fulfillment_Status" in final_df.columns

    def test_csv_import_integration(self):
        """Test importing sets from CSV and using in analysis."""
        # Create temporary CSV
        csv_content = """Set_SKU,Component_SKU,Component_Quantity
CSV-SET,CSV-COMP-1,1
CSV-SET,CSV-COMP-2,3"""

        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write(csv_content)
            csv_path = f.name

        try:
            # Import sets
            imported_sets = import_sets_from_csv(csv_path)

            # Use in analysis
            orders_df = pd.DataFrame({
                "Order_Number": ["O1"],
                "SKU": ["CSV-SET"],
                "Quantity": [2],
                "Shipping_Method": ["Express"],
                "Shipping_Country": ["US"]
            })

            stock_df = pd.DataFrame({
                "SKU": ["CSV-COMP-1", "CSV-COMP-2"],
                "Product_Name": ["C1", "C2"],
                "Stock": [100, 100]
            })

            history_df = pd.DataFrame(columns=["Order_Number", "Execution_Date"])

            column_mappings = {"set_decoders": imported_sets}

            # Execute analysis
            final_df, summary_present, summary_missing, stats = run_analysis(
                stock_df, orders_df, history_df, column_mappings
            )

            # Verify CSV-imported set was expanded correctly
            assert "CSV-COMP-1" in final_df["SKU"].tolist()
            assert "CSV-COMP-2" in final_df["SKU"].tolist()

            # Check quantity multiplication (2 sets × 3 comp = 6)
            comp2_rows = final_df[final_df["SKU"] == "CSV-COMP-2"]
            assert comp2_rows.iloc[0]["Quantity"] == 6

        finally:
            os.unlink(csv_path)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
