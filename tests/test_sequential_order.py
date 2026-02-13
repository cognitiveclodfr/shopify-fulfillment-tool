"""Tests for sequential order numbering (shopify_tool/sequential_order.py).

Covers:
- generate_sequential_order_map() assigns unique 1-indexed numbers
- Only Fulfillable orders are included
- Natural sort order is respected (ORDER-2 before ORDER-10)
- load_sequential_order_map() round-trips save/load
- get_sequential_number() returns correct value
- Existing map is reused without regeneration by default
- force_regenerate=True overwrites existing map
"""

import json
import pytest
import pandas as pd
from pathlib import Path

from shopify_tool.sequential_order import (
    generate_sequential_order_map,
    load_sequential_order_map,
    get_sequential_number,
)


def make_df(orders, statuses):
    """Helper: create minimal analysis DataFrame."""
    return pd.DataFrame({
        "Order_Number": orders,
        "SKU": [f"SKU-{i}" for i in range(len(orders))],
        "Order_Fulfillment_Status": statuses,
    })


class TestGenerateSequentialOrderMap:

    def test_assigns_unique_numbers(self, temp_dir):
        df = make_df(
            ["ORD-A", "ORD-B", "ORD-C"],
            ["Fulfillable", "Fulfillable", "Fulfillable"]
        )
        result = generate_sequential_order_map(df, temp_dir)
        assert len(result) == 3
        assert set(result.values()) == {1, 2, 3}

    def test_only_fulfillable_orders_included(self, temp_dir):
        df = make_df(
            ["ORD-1", "ORD-2", "ORD-3"],
            ["Fulfillable", "Not Fulfillable", "Fulfillable"]
        )
        result = generate_sequential_order_map(df, temp_dir)
        assert "ORD-2" not in result
        assert len(result) == 2

    def test_natural_sort_order(self, temp_dir):
        df = make_df(
            ["ORD-10", "ORD-2", "ORD-1"],
            ["Fulfillable", "Fulfillable", "Fulfillable"]
        )
        result = generate_sequential_order_map(df, temp_dir)
        assert result["ORD-1"] < result["ORD-2"] < result["ORD-10"]

    def test_saves_to_json(self, temp_dir):
        df = make_df(["ORD-X"], ["Fulfillable"])
        generate_sequential_order_map(df, temp_dir)
        json_path = temp_dir / "analysis" / "sequential_order.json"
        assert json_path.exists()

    def test_returns_dict(self, temp_dir):
        df = make_df(["ORD-1"], ["Fulfillable"])
        result = generate_sequential_order_map(df, temp_dir)
        assert isinstance(result, dict)

    def test_empty_dataframe_returns_empty_map(self, temp_dir):
        df = make_df([], [])
        result = generate_sequential_order_map(df, temp_dir)
        assert result == {}

    def test_reuses_existing_map_by_default(self, temp_dir):
        df = make_df(["ORD-1", "ORD-2"], ["Fulfillable", "Fulfillable"])
        first_result = generate_sequential_order_map(df, temp_dir)

        # Add more orders — should be ignored (map already exists)
        df2 = make_df(
            ["ORD-1", "ORD-2", "ORD-3"],
            ["Fulfillable", "Fulfillable", "Fulfillable"]
        )
        second_result = generate_sequential_order_map(df2, temp_dir)

        assert second_result == first_result  # Map not regenerated

    def test_force_regenerate_overwrites(self, temp_dir):
        df1 = make_df(["ORD-1"], ["Fulfillable"])
        generate_sequential_order_map(df1, temp_dir)

        df2 = make_df(["ORD-1", "ORD-2"], ["Fulfillable", "Fulfillable"])
        result = generate_sequential_order_map(df2, temp_dir, force_regenerate=True)

        assert len(result) == 2

    def test_duplicate_order_numbers_get_one_slot(self, temp_dir):
        # Multiple rows per order (one order = multiple SKUs)
        df = pd.DataFrame({
            "Order_Number": ["ORD-1", "ORD-1", "ORD-2"],
            "SKU": ["A", "B", "C"],
            "Order_Fulfillment_Status": ["Fulfillable", "Fulfillable", "Fulfillable"],
        })
        result = generate_sequential_order_map(df, temp_dir)
        assert len(result) == 2
        assert "ORD-1" in result
        assert "ORD-2" in result


class TestLoadSequentialOrderMap:

    def test_round_trip_save_and_load(self, temp_dir):
        df = make_df(["ORD-A", "ORD-B"], ["Fulfillable", "Fulfillable"])
        generated = generate_sequential_order_map(df, temp_dir)
        loaded = load_sequential_order_map(temp_dir)
        assert loaded == generated

    def test_returns_empty_dict_if_missing(self, temp_dir):
        # No file has been generated
        result = load_sequential_order_map(temp_dir)
        assert result == {}

    def test_handles_corrupted_json(self, temp_dir):
        json_path = temp_dir / "analysis" / "sequential_order.json"
        json_path.parent.mkdir(parents=True, exist_ok=True)
        json_path.write_text("not valid json", encoding="utf-8")
        result = load_sequential_order_map(temp_dir)
        assert result == {}


class TestGetSequentialNumber:

    def test_returns_correct_number(self, temp_dir):
        df = make_df(["ORD-A", "ORD-B", "ORD-C"], ["Fulfillable"] * 3)
        order_map = generate_sequential_order_map(df, temp_dir)
        for order_num, expected_seq in order_map.items():
            assert get_sequential_number(order_num, temp_dir) == expected_seq

    def test_returns_none_for_unknown_order(self, temp_dir):
        df = make_df(["ORD-1"], ["Fulfillable"])
        generate_sequential_order_map(df, temp_dir)
        assert get_sequential_number("ORD-UNKNOWN", temp_dir) is None

    def test_returns_none_when_no_map_exists(self, temp_dir):
        assert get_sequential_number("ORD-1", temp_dir) is None
