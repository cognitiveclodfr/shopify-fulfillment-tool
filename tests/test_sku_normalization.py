"""
Tests for SKU normalization and dtype handling.

This test suite verifies that:
1. normalize_sku function works correctly for all edge cases
2. Numeric SKUs don't get converted to floats during CSV loading
3. SKU matching works across different data types
4. Integration with analysis pipeline handles SKU correctly
"""
import pytest
import pandas as pd
import numpy as np
import io
from shopify_tool.csv_utils import normalize_sku


class TestNormalizeSku:
    """Test the normalize_sku function."""

    def test_float_artifact_removal(self):
        """Test that .0 suffix from float conversion is removed."""
        assert normalize_sku(5170.0) == "5170"
        assert normalize_sku("5170.0") == "5170"
        assert normalize_sku("5010.0") == "5010"

    def test_string_sku_unchanged(self):
        """Test that clean string SKUs remain unchanged."""
        assert normalize_sku("5170") == "5170"
        assert normalize_sku("ABC-123") == "ABC-123"
        assert normalize_sku("SKU-001") == "SKU-001"

    def test_whitespace_removal(self):
        """Test that leading/trailing whitespace is removed."""
        assert normalize_sku(" 5170 ") == "5170"
        assert normalize_sku("  ABC-123  ") == "ABC-123"
        assert normalize_sku("\t5170\n") == "5170"

    def test_leading_zeros_removed(self):
        """Test that leading zeros are removed for numeric SKUs."""
        assert normalize_sku("07") == "7"
        assert normalize_sku("0042") == "42"
        assert normalize_sku("00100") == "100"

    def test_alphanumeric_preserved(self):
        """Test that alphanumeric SKUs are preserved as-is."""
        assert normalize_sku("ABC-123") == "ABC-123"
        assert normalize_sku("01-DM-0379-110-L") == "01-DM-0379-110-L"
        assert normalize_sku("SKU-001-XL") == "SKU-001-XL"

    def test_nan_handling(self):
        """Test that NaN/None values return empty string."""
        assert normalize_sku(None) == ""
        assert normalize_sku(np.nan) == ""
        assert normalize_sku(pd.NA) == ""
        assert normalize_sku("") == ""

    def test_integer_input(self):
        """Test that integer inputs work correctly."""
        assert normalize_sku(5170) == "5170"
        assert normalize_sku(42) == "42"
        assert normalize_sku(7) == "7"

    def test_mixed_format_consistency(self):
        """Test that different representations normalize to same value."""
        # All these should normalize to "5170"
        inputs = [5170, 5170.0, "5170", "5170.0", " 5170 "]
        results = [normalize_sku(x) for x in inputs]
        assert all(r == "5170" for r in results)


class TestSkuDtypeForcing:
    """Test that forcing dtype=str prevents float conversion."""

    def test_csv_load_with_dtype_string(self):
        """Test that numeric SKUs stay as strings when dtype is forced."""
        csv_content = "SKU,Stock\n5170,100\n5010,50\n5140,75"

        # Without dtype (broken)
        df_broken = pd.read_csv(io.StringIO(csv_content))
        assert df_broken["SKU"].dtype == np.float64
        assert df_broken["SKU"].iloc[0] == 5170.0

        # With dtype=str (fixed)
        df_fixed = pd.read_csv(io.StringIO(csv_content), dtype={"SKU": str})
        assert df_fixed["SKU"].dtype == object
        assert df_fixed["SKU"].iloc[0] == "5170"

    def test_csv_load_mixed_sku_types(self):
        """Test CSV with both numeric and alphanumeric SKUs."""
        csv_content = "SKU,Stock\n5170,100\nABC-123,50\n07,75"

        # Force string dtype
        df = pd.read_csv(io.StringIO(csv_content), dtype={"SKU": str})

        # All SKUs should be strings
        assert df["SKU"].iloc[0] == "5170"  # Not 5170.0
        assert df["SKU"].iloc[1] == "ABC-123"
        assert df["SKU"].iloc[2] == "07"  # Leading zero preserved


class TestSkuMatching:
    """Test SKU matching across different formats."""

    def test_merge_with_normalized_skus(self):
        """Test that merge works after SKU normalization."""
        orders = pd.DataFrame({"SKU": ["5170", "5010", "5140"]})
        stock = pd.DataFrame({"SKU": [5170.0, 5010.0, 5140.0], "Stock": [100, 50, 75]})

        # Apply normalization
        orders["SKU"] = orders["SKU"].apply(normalize_sku)
        stock["SKU"] = stock["SKU"].apply(normalize_sku)

        # Should match all rows
        merged = pd.merge(orders, stock, on="SKU", how="left")
        assert len(merged) == 3
        assert merged["Stock"].notna().all()
        assert merged["SKU"].tolist() == ["5170", "5010", "5140"]

    def test_dictionary_lookup_with_normalized_skus(self):
        """Test dictionary lookup works with normalized SKUs."""
        # Stock dictionary with float SKUs
        stock_dict = {normalize_sku(5170.0): 100, normalize_sku(5010.0): 50}

        # Order SKUs as strings
        order_skus = ["5170", "5010", "9999"]

        # All lookups should work
        assert stock_dict.get(normalize_sku(order_skus[0]), 0) == 100
        assert stock_dict.get(normalize_sku(order_skus[1]), 0) == 50
        assert stock_dict.get(normalize_sku(order_skus[2]), 0) == 0  # Not found

    def test_mixed_format_comparison(self):
        """Test that mixed format SKUs match after normalization."""
        test_cases = [
            ("5170", "5170.0", True),
            ("5170", 5170, True),
            ("5170", 5170.0, True),
            (" 5170 ", "5170", True),
            ("07", "7", True),
            ("ABC-123", "ABC-123", True),
            ("5170", "5171", False),
        ]

        for sku1, sku2, should_match in test_cases:
            norm1 = normalize_sku(sku1)
            norm2 = normalize_sku(sku2)
            assert (norm1 == norm2) == should_match, \
                f"Failed: normalize_sku({sku1!r}) vs normalize_sku({sku2!r})"


class TestSkuDataFrameOperations:
    """Test SKU operations on DataFrames."""

    def test_apply_normalize_to_series(self):
        """Test applying normalize_sku to pandas Series."""
        df = pd.DataFrame({
            "SKU": [5170.0, "5010.0", " 5140 ", "ABC-123", None]
        })

        df["SKU"] = df["SKU"].apply(normalize_sku)

        assert df["SKU"].iloc[0] == "5170"
        assert df["SKU"].iloc[1] == "5010"
        assert df["SKU"].iloc[2] == "5140"
        assert df["SKU"].iloc[3] == "ABC-123"
        assert df["SKU"].iloc[4] == ""

    def test_filter_by_normalized_sku(self):
        """Test filtering DataFrame by normalized SKU."""
        df = pd.DataFrame({
            "SKU": [5170.0, 5010.0, 5140.0],
            "Stock": [100, 50, 75]
        })

        df["SKU"] = df["SKU"].apply(normalize_sku)

        # Filter for specific SKU
        result = df[df["SKU"] == normalize_sku("5170.0")]
        assert len(result) == 1
        assert result["Stock"].iloc[0] == 100

    def test_isin_with_normalized_skus(self):
        """Test .isin() with normalized SKUs."""
        df = pd.DataFrame({
            "SKU": [5170.0, 5010.0, 5140.0, "ABC-123"]
        })

        df["SKU"] = df["SKU"].apply(normalize_sku)

        exclude_list = ["5170", "ABC-123"]
        mask = df["SKU"].isin(exclude_list)

        assert mask.sum() == 2
        assert df[mask]["SKU"].tolist() == ["5170", "ABC-123"]


class TestRealWorldScenarios:
    """Test real-world scenarios that caused the bug."""

    def test_shopify_orders_vs_stock(self):
        """
        Test the exact scenario from the bug report:
        - Shopify orders export has string SKUs: "5170", "5010", "5140"
        - Stock CSV has numeric SKUs that become floats: 5170, 5010, 5140
        """
        # Orders from Shopify (strings)
        orders = pd.DataFrame({
            "Order_Number": ["1001", "1002", "1003"],
            "SKU": ["5170", "5010", "5140"],
            "Quantity": [1, 2, 1]
        })

        # Stock from CSV (will be auto-detected as float if not forced)
        stock_csv = "Артикул,Наличност\n5170,100\n5010,50\n5140,75"
        stock = pd.read_csv(io.StringIO(stock_csv), delimiter=",", dtype={"Артикул": str})
        stock.rename(columns={"Артикул": "SKU", "Наличност": "Stock"}, inplace=True)

        # Apply normalization (as done in analysis.py)
        orders["SKU"] = orders["SKU"].apply(normalize_sku)
        stock["SKU"] = stock["SKU"].apply(normalize_sku)

        # Create stock dictionary (as done in analysis.py)
        live_stock = pd.Series(stock.Stock.values, index=stock.SKU).to_dict()

        # Check fulfillment (as done in analysis.py)
        for _, order in orders.iterrows():
            sku = order["SKU"]
            required_qty = order["Quantity"]
            available_stock = live_stock.get(sku, 0)

            # Should find stock for all SKUs
            assert available_stock > 0, f"Stock not found for SKU {sku}"
            assert available_stock >= required_qty, \
                f"Insufficient stock for SKU {sku}: need {required_qty}, have {available_stock}"

    def test_exclude_skus_matching(self):
        """
        Test exclude SKUs feature with mixed formats.
        This was working in packing_lists.py, should work everywhere now.
        """
        df = pd.DataFrame({
            "SKU": [5170.0, 5010.0, 5140.0, "ABC-123"]
        })

        # Apply normalization
        df["SKU"] = df["SKU"].apply(normalize_sku)

        # Exclude list with mixed formats
        exclude_skus = ["5170.0", 5010, "ABC-123"]
        exclude_skus_normalized = [normalize_sku(s) for s in exclude_skus]

        # Filter out excluded SKUs
        mask = ~df["SKU"].isin(exclude_skus_normalized)
        filtered = df[mask]

        # Should only have 5140 left
        assert len(filtered) == 1
        assert filtered["SKU"].iloc[0] == "5140"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
