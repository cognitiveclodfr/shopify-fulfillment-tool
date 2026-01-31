import pytest
import pandas as pd
from shopify_tool.rules import RuleEngine


@pytest.fixture
def sample_df():
    """Provides a sample DataFrame for testing."""
    data = {
        "Order_Number": ["#1001", "#1001", "#1002", "#1003", "#1004"],
        "Order_Type": ["Single", "Single", "Multi", "Multi", "Single"],
        "Shipping_Provider": ["DHL", "DHL", "PostOne", "DPD", "DHL"],
        "Total_Price": [50, 50, 150, 200, 80],
        "Tags": ["Tag1", "Tag1", "", "Urgent", ""],
        "Status_Note": ["", "", "Repeat", "", "Repeat"],
        "Order_Fulfillment_Status": ["Fulfillable", "Fulfillable", "Fulfillable", "Not Fulfillable", "Fulfillable"],
        "SKU": ["SKU-A", "SKU-B", "SKU-C", "SKU-D", "SKU-E"],
        "Quantity": [1, 1, 2, 3, 1],
    }
    return pd.DataFrame(data)


def test_add_tag_with_simple_rule(sample_df):
    """
    Tests a simple rule to add a tag to the Status_Note column.
    """
    rules = [
        {
            "name": "Tag DHL Orders",
            "match": "ALL",
            "conditions": [{"field": "Shipping_Provider", "operator": "equals", "value": "DHL"}],
            "actions": [{"type": "ADD_TAG", "value": "DHL-SHIP"}],
        }
    ]

    engine = RuleEngine(rules)
    result_df = engine.apply(sample_df.copy())

    # Check that rows with 'DHL' got the new note
    dhl_rows = result_df[result_df["Shipping_Provider"] == "DHL"]
    assert all(dhl_rows["Status_Note"].str.contains("DHL-SHIP"))

    # Check that other rows did not get the note
    other_rows = result_df[result_df["Shipping_Provider"] != "DHL"]
    assert not any(other_rows["Status_Note"].str.contains("DHL-SHIP"))

    # Check that a pre-existing note was preserved
    assert "Repeat, DHL-SHIP" in result_df.loc[4, "Status_Note"]


def test_add_internal_tag_with_multiple_conditions_all(sample_df):
    """
    Tests a rule with multiple 'AND' conditions using ADD_INTERNAL_TAG.
    """
    rules = [
        {
            "name": "High Priority Multi-Item Orders",
            "match": "ALL",  # AND
            "conditions": [
                {"field": "Order_Type", "operator": "equals", "value": "Multi"},
                {"field": "Total_Price", "operator": "is greater than", "value": 100},
            ],
            "actions": [{"type": "ADD_INTERNAL_TAG", "value": "priority:high"}],
        }
    ]

    engine = RuleEngine(rules)
    result_df = engine.apply(sample_df.copy())

    # Order #1002 and #1003 should have the tag
    assert "priority:high" in result_df.loc[result_df["Order_Number"] == "#1002", "Internal_Tags"].iloc[0]
    assert "priority:high" in result_df.loc[result_df["Order_Number"] == "#1003", "Internal_Tags"].iloc[0]

    # Others should not have the tag
    assert "priority:high" not in result_df.loc[result_df["Order_Number"] == "#1001", "Internal_Tags"].iloc[0]
    assert "priority:high" not in result_df.loc[result_df["Order_Number"] == "#1004", "Internal_Tags"].iloc[0]


def test_set_status_with_multiple_conditions_any(sample_df):
    """
    Tests a rule with multiple 'OR' conditions.
    """
    rules = [
        {
            "name": "Review DPD or Urgent Orders",
            "match": "ANY",  # OR
            "conditions": [
                {"field": "Shipping_Provider", "operator": "equals", "value": "DPD"},
                {"field": "Tags", "operator": "contains", "value": "Urgent"},
            ],
            "actions": [{"type": "SET_STATUS", "value": "Manual Review"}],
        }
    ]

    engine = RuleEngine(rules)
    result_df = engine.apply(sample_df.copy())

    # Order #1003 matches both conditions
    assert result_df.loc[result_df["Order_Number"] == "#1003", "Order_Fulfillment_Status"].iloc[0] == "Manual Review"

    # Check non-matching orders
    assert result_df.loc[result_df["Order_Number"] == "#1001", "Order_Fulfillment_Status"].iloc[0] == "Fulfillable"
    assert result_df.loc[result_df["Order_Number"] == "#1002", "Order_Fulfillment_Status"].iloc[0] == "Fulfillable"


def test_no_action_if_no_match(sample_df):
    """
    Ensures no changes are made if no rules match.
    """
    rules = [
        {
            "name": "Non-existent condition",
            "match": "ALL",
            "conditions": [{"field": "Shipping_Provider", "operator": "equals", "value": "FedEx"}],
            "actions": [{"type": "ADD_TAG", "value": "FEDEX-SHIP"}],
        }
    ]

    original_df = sample_df.copy()
    engine = RuleEngine(rules)
    result_df = engine.apply(original_df.copy())

    # The DataFrame should be identical to the original
    pd.testing.assert_frame_equal(original_df, result_df, check_like=True)


def test_empty_rules_config(sample_df):
    """
    Tests that the engine handles an empty or invalid rules list gracefully.
    """
    original_df = sample_df.copy()

    # Test with empty list
    engine_empty = RuleEngine([])
    result_df_empty = engine_empty.apply(original_df.copy())
    pd.testing.assert_frame_equal(original_df, result_df_empty)

    # Test with None
    engine_none = RuleEngine(None)
    result_df_none = engine_none.apply(original_df.copy())
    pd.testing.assert_frame_equal(original_df, result_df_none)


def test_rules_with_empty_conditions(sample_df):
    """
    Tests that a rule with no conditions does not match any rows.
    """
    rules = [
        {
            "name": "Rule with no conditions",
            "match": "ALL",
            "conditions": [],
            "actions": [{"type": "ADD_TAG", "value": "SHOULD-NOT-BE-ADDED"}],
        }
    ]

    engine = RuleEngine(rules)
    result_df = engine.apply(sample_df.copy())

    assert not any(result_df["Tags"].str.contains("SHOULD-NOT-BE-ADDED", na=False))


@pytest.mark.parametrize(
    "operator,value,expected_matches",
    [
        ("equals", "DHL", ["#1001", "#1004"]),
        ("does not equal", "DHL", ["#1002", "#1003"]),
        ("contains", "pos", ["#1002"]),
        ("does not contain", "pos", ["#1001", "#1003", "#1004"]),
        ("starts with", "Post", ["#1002"]),
        ("ends with", "One", ["#1002"]),
        ("is empty", "", ["#1002", "#1004"]),  # Tags is empty
        ("is not empty", "", ["#1001", "#1003"]),  # Tags is not empty
    ],
)
def test_all_string_operators(sample_df, operator, value, expected_matches):
    """Tests all string-based operators of the rule engine via parametrization."""
    field = "Shipping_Provider"
    if "empty" in operator:
        field = "Tags"  # 'is empty' needs a field with empty values

    rules = [
        {
            "match": "ALL",
            "conditions": [{"field": field, "operator": operator, "value": value}],
            "actions": [{"type": "ADD_INTERNAL_TAG", "value": "matched"}],
        }
    ]
    engine = RuleEngine(rules)
    result_df = engine.apply(sample_df.copy())

    matched_orders = result_df[result_df["Internal_Tags"].str.contains("matched", na=False)]["Order_Number"].unique()
    assert sorted(matched_orders) == sorted(expected_matches)


@pytest.mark.parametrize(
    "operator,value,expected_matches",
    [
        ("is greater than", 100, ["#1002", "#1003"]),
        ("is less than", 100, ["#1001", "#1004"]),
    ],
)
def test_all_numeric_operators(sample_df, operator, value, expected_matches):
    """Tests all numeric operators of the rule engine via parametrization."""
    rules = [
        {
            "match": "ALL",
            "conditions": [{"field": "Total_Price", "operator": operator, "value": value}],
            "actions": [{"type": "ADD_INTERNAL_TAG", "value": "matched"}],
        }
    ]
    engine = RuleEngine(rules)
    result_df = engine.apply(sample_df.copy())

    matched_orders = result_df[result_df["Internal_Tags"].str.contains("matched", na=False)]["Order_Number"].unique()
    assert sorted(matched_orders) == sorted(expected_matches)


def test_rule_with_invalid_field(sample_df):
    """Tests that a rule with a non-existent field is skipped gracefully."""
    original_df = sample_df.copy()
    rules = [{"conditions": [{"field": "NonExistentField", "operator": "equals", "value": "a"}]}]
    engine = RuleEngine(rules)
    result_df = engine.apply(sample_df.copy())
    pd.testing.assert_frame_equal(original_df, result_df)


def test_prepare_df_for_actions_creates_columns(sample_df):
    """Tests that the _prepare_df_for_actions method creates missing columns."""
    df = pd.DataFrame({"Order_Number": ["#1001"]})
    rules = [
        {"actions": [{"type": "ADD_TAG"}]},
        {"actions": [{"type": "ADD_INTERNAL_TAG"}]},
    ]
    engine = RuleEngine(rules)
    engine._prepare_df_for_actions(df)
    assert "Status_Note" in df.columns
    assert "Internal_Tags" in df.columns


def test_exclude_from_report_action(sample_df):
    """Tests using ADD_INTERNAL_TAG for exclude_from_report metadata."""
    rules = [
        {
            "conditions": [{"field": "Order_Number", "operator": "equals", "value": "#1002"}],
            "actions": [{"type": "ADD_INTERNAL_TAG", "value": "exclude_from_report"}],
        }
    ]
    engine = RuleEngine(rules)
    result_df = engine.apply(sample_df.copy())
    assert "exclude_from_report" in result_df.loc[result_df["Order_Number"] == "#1002", "Internal_Tags"].iloc[0]
    assert "exclude_from_report" not in result_df.loc[result_df["Order_Number"] != "#1002", "Internal_Tags"].iloc[0]


def test_add_tag_to_nan_note(sample_df):
    """Tests that the ADD_TAG action works correctly on a cell with a NaN/null value."""
    df = sample_df.copy()
    # Force a NaN value into the Status_Note column
    df.loc[0, "Status_Note"] = pd.NA

    rules = [
        {
            "conditions": [{"field": "Order_Number", "operator": "equals", "value": "#1001"}],
            "actions": [{"type": "ADD_TAG", "value": "NewTag"}],
        }
    ]
    engine = RuleEngine(rules)
    result_df = engine.apply(df)

    # The note for order #1001 should now be 'NewTag'
    note = result_df.loc[result_df["Order_Number"] == "#1001", "Status_Note"].iloc[0]
    assert note == "NewTag"


# =============================================================================
# NEW TESTS FOR ORDER-LEVEL RULES
# =============================================================================


@pytest.fixture
def order_level_sample_df():
    """Provides a sample DataFrame for testing order-level rules."""
    data = {
        "Order_Number": ["#1001", "#1001", "#1001", "#1002", "#1002", "#1003"],
        "SKU": ["HAT-001", "GLOVES-001", "SCARF-001", "OVERSIZED_001", "HAT-002", "HAT-003"],
        "Product_Name": ["Hat", "Gloves", "Scarf", "Oversized Item", "Hat 2", "Hat 3"],
        "Quantity": [1, 1, 1, 1, 2, 5],
        "Total_Price": [10.0, 15.0, 12.0, 150.0, 20.0, 50.0],
        "Status_Note": ["", "", "", "", "", ""],
    }
    return pd.DataFrame(data)


def test_order_level_item_count(order_level_sample_df):
    """Tests order-level rule with item_count condition."""
    rules = [
        {
            "name": "Small bag for few items",
            "level": "order",
            "match": "ALL",
            "conditions": [
                {"field": "item_count", "operator": "is less than or equal", "value": "3"}
            ],
            "actions": [
                {"type": "ADD_INTERNAL_TAG", "value": "packaging:small_bag"}
            ]
        }
    ]

    engine = RuleEngine(rules)
    result_df = engine.apply(order_level_sample_df.copy())

    # Order #1001 has 3 items, first row should get packaging:small_bag tag
    order_1001 = result_df[result_df["Order_Number"] == "#1001"]
    assert "packaging:small_bag" in order_1001.iloc[0]["Internal_Tags"]

    # Order #1002 has 2 items, first row should get packaging:small_bag tag
    order_1002 = result_df[result_df["Order_Number"] == "#1002"]
    assert "packaging:small_bag" in order_1002.iloc[0]["Internal_Tags"]

    # Order #1003 has 1 item, first row should get packaging:small_bag tag
    order_1003 = result_df[result_df["Order_Number"] == "#1003"]
    assert "packaging:small_bag" in order_1003.iloc[0]["Internal_Tags"]


def test_order_level_has_sku(order_level_sample_df):
    """Tests order-level rule with has_sku condition."""
    rules = [
        {
            "name": "Box for oversized",
            "level": "order",
            "match": "ANY",
            "conditions": [
                {"field": "has_sku", "operator": "equals", "value": "OVERSIZED_001"}
            ],
            "actions": [
                {"type": "ADD_INTERNAL_TAG", "value": "packaging:box"},
                {"type": "ADD_ORDER_TAG", "value": "OVERSIZED"}
            ]
        }
    ]

    engine = RuleEngine(rules)
    result_df = engine.apply(order_level_sample_df.copy())

    # Order #1002 has OVERSIZED_001, first row should get packaging:box tag and OVERSIZED tag
    order_1002 = result_df[result_df["Order_Number"] == "#1002"]
    assert "packaging:box" in order_1002.iloc[0]["Internal_Tags"]
    assert "OVERSIZED" in order_1002.iloc[0]["Status_Note"]

    # Other orders should not have these (checking first row)
    order_1001 = result_df[result_df["Order_Number"] == "#1001"]
    assert "packaging:box" not in order_1001.iloc[0]["Internal_Tags"]


def test_order_level_total_quantity(order_level_sample_df):
    """Tests order-level rule with total_quantity condition."""
    rules = [
        {
            "name": "High quantity orders",
            "level": "order",
            "match": "ALL",
            "conditions": [
                {"field": "total_quantity", "operator": "is greater than or equal", "value": "5"}
            ],
            "actions": [
                {"type": "ADD_ORDER_TAG", "value": "HIGH_QTY"}
            ]
        }
    ]

    engine = RuleEngine(rules)
    result_df = engine.apply(order_level_sample_df.copy())

    # Order #1003 has quantity=5, first row should get HIGH_QTY tag
    order_1003 = result_df[result_df["Order_Number"] == "#1003"]
    assert "HIGH_QTY" in order_1003.iloc[0]["Status_Note"]

    # Order #1001 has total quantity=3, should not get tag
    order_1001 = result_df[result_df["Order_Number"] == "#1001"]
    assert "HIGH_QTY" not in order_1001.iloc[0]["Status_Note"]


def test_order_and_article_level_rules_together(order_level_sample_df):
    """Tests that both order-level and article-level rules work together."""
    rules = [
        # Order-level rule
        {
            "name": "Small bag for few items",
            "level": "order",
            "match": "ALL",
            "conditions": [
                {"field": "item_count", "operator": "is less than or equal", "value": "6"}
            ],
            "actions": [
                {"type": "ADD_INTERNAL_TAG", "value": "packaging:small_bag"}
            ]
        },
        # Article-level rule
        {
            "name": "High value items",
            "level": "article",
            "match": "ALL",
            "conditions": [
                {"field": "Total_Price", "operator": "is greater than", "value": "100"}
            ],
            "actions": [
                {"type": "ADD_TAG", "value": "HIGH_VALUE"}
            ]
        }
    ]

    engine = RuleEngine(rules)
    result_df = engine.apply(order_level_sample_df.copy())

    # All orders' FIRST ROW should have packaging:small_bag tag (order-level)
    for order_num in result_df["Order_Number"].unique():
        order = result_df[result_df["Order_Number"] == order_num]
        assert "packaging:small_bag" in order.iloc[0]["Internal_Tags"]

    # Only OVERSIZED_001 row should have HIGH_VALUE tag (article-level)
    high_value_rows = result_df[result_df["Status_Note"].str.contains("HIGH_VALUE", na=False)]
    assert len(high_value_rows) == 1
    assert high_value_rows["SKU"].iloc[0] == "OVERSIZED_001"


def test_new_operators_greater_than_or_equal():
    """Tests the new >= operator."""
    data = {
        "Order_Number": ["#2001", "#2002", "#2003"],
        "SKU": ["A", "B", "C"],
        "Quantity": [3, 5, 7],
        "Status_Note": ["", "", ""],
    }
    df = pd.DataFrame(data)

    rules = [
        {
            "name": "Test >=",
            "level": "article",
            "match": "ALL",
            "conditions": [
                {"field": "Quantity", "operator": "is greater than or equal", "value": "5"}
            ],
            "actions": [
                {"type": "ADD_TAG", "value": "QTY_GTE_5"}
            ]
        }
    ]

    engine = RuleEngine(rules)
    result_df = engine.apply(df)

    # Only rows with Quantity >= 5 should have the tag
    assert "QTY_GTE_5" not in result_df.iloc[0]["Status_Note"]  # 3
    assert "QTY_GTE_5" in result_df.iloc[1]["Status_Note"]  # 5
    assert "QTY_GTE_5" in result_df.iloc[2]["Status_Note"]  # 7


def test_new_operators_less_than_or_equal():
    """Tests the new <= operator."""
    data = {
        "Order_Number": ["#2001", "#2002", "#2003"],
        "SKU": ["A", "B", "C"],
        "Quantity": [3, 5, 7],
        "Status_Note": ["", "", ""],
    }
    df = pd.DataFrame(data)

    rules = [
        {
            "name": "Test <=",
            "level": "article",
            "match": "ALL",
            "conditions": [
                {"field": "Quantity", "operator": "is less than or equal", "value": "5"}
            ],
            "actions": [
                {"type": "ADD_TAG", "value": "QTY_LTE_5"}
            ]
        }
    ]

    engine = RuleEngine(rules)
    result_df = engine.apply(df)

    # Only rows with Quantity <= 5 should have the tag
    assert "QTY_LTE_5" in result_df.iloc[0]["Status_Note"]  # 3
    assert "QTY_LTE_5" in result_df.iloc[1]["Status_Note"]  # 5
    assert "QTY_LTE_5" not in result_df.iloc[2]["Status_Note"]  # 7


def test_order_level_backwards_compatibility(sample_df):
    """Tests that rules without 'level' field default to article-level."""
    rules = [
        {
            "name": "Tag DHL Orders",
            "match": "ALL",
            # No "level" field - should default to "article"
            "conditions": [{"field": "Shipping_Provider", "operator": "equals", "value": "DHL"}],
            "actions": [{"type": "ADD_TAG", "value": "DHL-SHIP"}],
        }
    ]

    engine = RuleEngine(rules)
    result_df = engine.apply(sample_df.copy())

    # Should work the same as before (article-level)
    dhl_rows = result_df[result_df["Shipping_Provider"] == "DHL"]
    assert all(dhl_rows["Status_Note"].str.contains("DHL-SHIP"))


def test_add_internal_tag_for_packaging(order_level_sample_df):
    """Tests using ADD_INTERNAL_TAG for packaging metadata."""
    rules = [
        {
            "name": "Test packaging tag",
            "level": "order",
            "match": "ALL",
            "conditions": [
                {"field": "item_count", "operator": "is greater than", "value": "0"}
            ],
            "actions": [
                {"type": "ADD_INTERNAL_TAG", "value": "packaging:test_bag"}
            ]
        }
    ]

    engine = RuleEngine(rules)
    result_df = engine.apply(order_level_sample_df.copy())

    # All rows should have the Internal_Tags column
    assert "Internal_Tags" in result_df.columns

    # First row of each order should have packaging:test_bag tag
    for order_num in result_df["Order_Number"].unique():
        order = result_df[result_df["Order_Number"] == order_num]
        assert "packaging:test_bag" in order.iloc[0]["Internal_Tags"]


def test_add_order_tag_action(order_level_sample_df):
    """Tests the ADD_ORDER_TAG action adds tags without duplicates."""
    rules = [
        {
            "name": "Test order tag",
            "level": "order",
            "match": "ALL",
            "conditions": [
                {"field": "item_count", "operator": "is greater than", "value": "0"}
            ],
            "actions": [
                {"type": "ADD_ORDER_TAG", "value": "ORDER_TAG"}
            ]
        }
    ]

    engine = RuleEngine(rules)
    result_df = engine.apply(order_level_sample_df.copy())

    # First row of each order should have ORDER_TAG in Status_Note
    for order_num in result_df["Order_Number"].unique():
        order = result_df[result_df["Order_Number"] == order_num]
        assert "ORDER_TAG" in order.iloc[0]["Status_Note"]

    # Apply rules again - should not duplicate tags
    result_df2 = engine.apply(result_df)
    for order_num in result_df2["Order_Number"].unique():
        order = result_df2[result_df2["Order_Number"] == order_num]
        note = order.iloc[0]["Status_Note"]
        assert note.count("ORDER_TAG") == 1  # Should only appear once


def test_add_tag_in_order_level_rule_applies_to_all_rows(order_level_sample_df):
    """Tests that ADD_TAG in order-level rule applies to ALL rows of the order.

    This is important for packing list filtering - we don't want to lose unmarked items.
    """
    rules = [
        {
            "name": "Tag orders with oversized items",
            "level": "order",
            "match": "ANY",
            "conditions": [
                {"field": "has_sku", "operator": "equals", "value": "OVERSIZED_001"}
            ],
            "actions": [
                {"type": "ADD_TAG", "value": "HAS_OVERSIZED"}
            ]
        }
    ]

    engine = RuleEngine(rules)
    result_df = engine.apply(order_level_sample_df.copy())

    # Order #1002 has OVERSIZED_001, so ALL its rows should have the tag
    order_1002 = result_df[result_df["Order_Number"] == "#1002"]
    for idx, row in order_1002.iterrows():
        assert "HAS_OVERSIZED" in row["Status_Note"], f"Row {idx} missing HAS_OVERSIZED tag"

    # Other orders should not have the tag
    order_1001 = result_df[result_df["Order_Number"] == "#1001"]
    for idx, row in order_1001.iterrows():
        assert "HAS_OVERSIZED" not in row["Status_Note"], f"Row {idx} should not have HAS_OVERSIZED tag"


def test_mixed_actions_in_order_level_rule(order_level_sample_df):
    """Tests order-level rule with both ADD_TAG (all rows) and ADD_INTERNAL_TAG (first row)."""
    rules = [
        {
            "name": "Large orders get special treatment",
            "level": "order",
            "match": "ALL",
            "conditions": [
                {"field": "item_count", "operator": "is greater than or equal", "value": "3"}
            ],
            "actions": [
                {"type": "ADD_TAG", "value": "LARGE_ORDER"},  # Should apply to all rows
                {"type": "ADD_INTERNAL_TAG", "value": "packaging:large_bag"},  # Should apply to first row only
                {"type": "ADD_ORDER_TAG", "value": "BULK"}  # Should apply to first row only
            ]
        }
    ]

    engine = RuleEngine(rules)
    result_df = engine.apply(order_level_sample_df.copy())

    # Order #1001 has 3 items - should match
    order_1001 = result_df[result_df["Order_Number"] == "#1001"]

    # ADD_TAG should be on ALL rows
    for idx, row in order_1001.iterrows():
        assert "LARGE_ORDER" in row["Status_Note"], f"Row {idx} missing LARGE_ORDER tag"

    # ADD_INTERNAL_TAG and ADD_ORDER_TAG should be on FIRST row only
    assert "packaging:large_bag" in order_1001.iloc[0]["Internal_Tags"]
    assert "BULK" in order_1001.iloc[0]["Status_Note"]

    # Other rows should not have packaging tag
    for i in range(1, len(order_1001)):
        assert "packaging:large_bag" not in order_1001.iloc[i]["Internal_Tags"]

    # Order #1003 has 1 item - should NOT match
    order_1003 = result_df[result_df["Order_Number"] == "#1003"]
    assert "LARGE_ORDER" not in order_1003.iloc[0]["Status_Note"]


# =============================================================================
# TESTS FOR EXTENDED HAS_SKU OPERATORS
# =============================================================================


def test_order_level_has_sku_starts_with():
    """Tests has_sku with 'starts with' operator for SKU prefixes."""
    data = {
        "Order_Number": ["#1001", "#1001", "#1002", "#1002"],
        "SKU": ["01-FACE-1001", "05-ADD-5001", "02-FACE-1001", "02-FACE-1002"],
        "Status_Note": ["", "", "", ""],
    }
    df = pd.DataFrame(data)

    rules = [
        {
            "name": "Box items only",
            "level": "order",
            "match": "ALL",
            "conditions": [
                {"field": "has_sku", "operator": "starts with", "value": "01-"}
            ],
            "actions": [
                {"type": "ADD_ORDER_TAG", "value": "BOX_ONLY"}
            ]
        }
    ]

    engine = RuleEngine(rules)
    result_df = engine.apply(df)

    # Order #1001 has SKU starting with "01-", should get tag
    order_1001 = result_df[result_df["Order_Number"] == "#1001"]
    assert "BOX_ONLY" in order_1001.iloc[0]["Status_Note"]

    # Order #1002 has only "02-" SKUs, should NOT get tag
    order_1002 = result_df[result_df["Order_Number"] == "#1002"]
    assert "BOX_ONLY" not in order_1002.iloc[0]["Status_Note"]


def test_order_level_has_sku_mixed_detection():
    """Tests detection of orders with both box and bag items."""
    data = {
        "Order_Number": ["#1001", "#1001", "#1002", "#1003", "#1003"],
        "SKU": ["01-FACE-1001", "02-FACE-1001", "01-FACE-1001", "02-FACE-1001", "02-FACE-1002"],
        "Status_Note": ["", "", "", "", ""],
    }
    df = pd.DataFrame(data)

    rules = [
        {
            "name": "Mixed orders",
            "level": "order",
            "match": "ALL",
            "conditions": [
                {"field": "has_sku", "operator": "starts with", "value": "01-"},
                {"field": "has_sku", "operator": "starts with", "value": "02-"}
            ],
            "actions": [
                {"type": "ADD_ORDER_TAG", "value": "MIXED"}
            ]
        }
    ]

    engine = RuleEngine(rules)
    result_df = engine.apply(df)

    # Order #1001 has both 01- and 02- SKUs
    order_1001 = result_df[result_df["Order_Number"] == "#1001"]
    assert "MIXED" in order_1001.iloc[0]["Status_Note"]

    # Order #1002 has only 01- SKUs
    order_1002 = result_df[result_df["Order_Number"] == "#1002"]
    assert "MIXED" not in order_1002.iloc[0]["Status_Note"]

    # Order #1003 has only 02- SKUs
    order_1003 = result_df[result_df["Order_Number"] == "#1003"]
    assert "MIXED" not in order_1003.iloc[0]["Status_Note"]


def test_order_level_has_sku_negative_operators():
    """Tests has_sku with negative operators."""
    data = {
        "Order_Number": ["#1001", "#1001", "#1002"],
        "SKU": ["01-FACE-1001", "02-FACE-1001", "03-OTHER-001"],
        "Status_Note": ["", "", ""],
    }
    df = pd.DataFrame(data)

    rules = [
        {
            "name": "No mask items",
            "level": "order",
            "match": "ALL",
            "conditions": [
                {"field": "has_sku", "operator": "does not contain", "value": "02-FACE-"}
            ],
            "actions": [
                {"type": "ADD_ORDER_TAG", "value": "NO_MASKS"}
            ]
        }
    ]

    engine = RuleEngine(rules)
    result_df = engine.apply(df)

    # Order #1001 has 02-FACE- SKU, should NOT get tag
    order_1001 = result_df[result_df["Order_Number"] == "#1001"]
    assert "NO_MASKS" not in order_1001.iloc[0]["Status_Note"]

    # Order #1002 has no 02-FACE- SKU, should get tag
    order_1002 = result_df[result_df["Order_Number"] == "#1002"]
    assert "NO_MASKS" in order_1002.iloc[0]["Status_Note"]


def test_ui_field_selector_includes_order_level_fields():
    """Tests that get_available_rule_fields includes order-level fields."""
    from gui.settings_window_pyside import SettingsWindow

    # Create minimal test setup
    window = SettingsWindow(
        client_id="test",
        client_config={},
        profile_manager=None,
        analysis_df=None
    )

    fields = window.get_available_rule_fields()

    # Order-level fields must be present
    assert "item_count" in fields
    assert "total_quantity" in fields
    assert "has_sku" in fields

    # Should appear before article-level fields
    item_count_idx = fields.index("item_count")
    sku_idx = fields.index("SKU")
    assert item_count_idx < sku_idx


def test_deprecated_action_types_log_warnings(sample_df, caplog):
    """Verify that deprecated action types log warnings and are skipped."""
    import logging

    rules = [
        {
            "name": "Test deprecated actions",
            "match": "ALL",
            "conditions": [
                {"field": "Order_Number", "operator": "equals", "value": "#1001"}
            ],
            "actions": [
                {"type": "SET_PRIORITY", "value": "High"},
                {"type": "EXCLUDE_FROM_REPORT"},
                {"type": "SET_PACKAGING_TAG", "value": "BOX"},
                {"type": "EXCLUDE_SKU", "value": "SKU-A"},
            ],
        }
    ]

    engine = RuleEngine(rules)

    with caplog.at_level(logging.WARNING):
        result_df = engine.apply(sample_df.copy())

    # Verify warnings were logged for all deprecated actions
    assert any("SET_PRIORITY" in record.message for record in caplog.records)
    assert any("EXCLUDE_FROM_REPORT" in record.message for record in caplog.records)
    assert any("SET_PACKAGING_TAG" in record.message for record in caplog.records)
    assert any("EXCLUDE_SKU" in record.message for record in caplog.records)

    # Verify actions were NOT executed (columns not created)
    assert "Priority" not in result_df.columns
    assert "_is_excluded" not in result_df.columns
    assert "Packaging_Tags" not in result_df.columns


# ====================================================================
# NEW OPERATORS TESTS (v1.9.0)
# ====================================================================


@pytest.fixture
def date_sample_df():
    """Provides a sample DataFrame with date fields for testing date operators."""
    data = {
        "Order_Number": ["#2001", "#2002", "#2003", "#2004", "#2005"],
        "Order_Date": ["2024-01-15", "2024-01-30", "2024-02-15", "30/01/2024", "15.02.2024"],
        "Shipping_Provider": ["DHL", "PostOne", "DPD", "DHL", "PostOne"],
        "Total_Price": [50, 75, 100, 125, 150],
        "SKU": ["SKU-1234", "SKU-ABCD", "OTHER-001", "SKU-5678", "MISC-999"],
        "Status_Note": ["", "", "", "", ""],
        "Internal_Tags": ["[]", "[]", "[]", "[]", "[]"],
    }
    return pd.DataFrame(data)


# --- List Operators Tests ---


@pytest.mark.parametrize(
    "operator,value,expected_matches",
    [
        ("in list", "DHL,PostOne", ["#1001", "#1002", "#1004"]),
        ("in list", "DHL, PostOne, DPD", ["#1001", "#1002", "#1003", "#1004"]),
        ("in list", "dhl,postone", ["#1001", "#1002", "#1004"]),  # Case insensitive
        ("in list", " DHL , PostOne ", ["#1001", "#1002", "#1004"]),  # Whitespace handling
        ("in list", "FedEx", []),  # No matches
        ("not in list", "DHL,PostOne", ["#1003"]),
        ("not in list", "DPD", ["#1001", "#1002", "#1004"]),
    ],
)
def test_list_operators(sample_df, operator, value, expected_matches):
    """Tests 'in list' and 'not in list' operators with various inputs."""
    rules = [
        {
            "match": "ALL",
            "conditions": [{"field": "Shipping_Provider", "operator": operator, "value": value}],
            "actions": [{"type": "ADD_INTERNAL_TAG", "value": "matched"}],
        }
    ]
    engine = RuleEngine(rules)
    result_df = engine.apply(sample_df.copy())

    matched_orders = result_df[result_df["Internal_Tags"].str.contains("matched", na=False)]["Order_Number"].unique()
    assert sorted(matched_orders) == sorted(expected_matches)


def test_list_operators_empty_value(sample_df):
    """Test 'in list' operator with empty value."""
    rules = [
        {
            "match": "ALL",
            "conditions": [{"field": "Shipping_Provider", "operator": "in list", "value": ""}],
            "actions": [{"type": "ADD_INTERNAL_TAG", "value": "matched"}],
        }
    ]
    engine = RuleEngine(rules)
    result_df = engine.apply(sample_df.copy())

    # Should not match any rows
    matched_orders = result_df[result_df["Internal_Tags"].str.contains("matched", na=False)]
    assert len(matched_orders) == 0


# --- Range Operators Tests ---


@pytest.mark.parametrize(
    "operator,value,expected_matches",
    [
        ("between", "50-150", ["#1001", "#1002", "#1004"]),
        ("between", "100-200", ["#1002", "#1003"]),
        ("between", "50-50", ["#1001"]),  # Exact match (inclusive)
        ("between", "60-140", ["#1004"]),  # Only #1004 has Total_Price=80
        ("not between", "50-150", ["#1003"]),
        ("not between", "100-200", ["#1001", "#1004"]),
    ],
)
def test_range_operators_numeric(sample_df, operator, value, expected_matches):
    """Tests 'between' and 'not between' operators with numeric values."""
    rules = [
        {
            "match": "ALL",
            "conditions": [{"field": "Total_Price", "operator": operator, "value": value}],
            "actions": [{"type": "ADD_INTERNAL_TAG", "value": "matched"}],
        }
    ]
    engine = RuleEngine(rules)
    result_df = engine.apply(sample_df.copy())

    matched_orders = result_df[result_df["Internal_Tags"].str.contains("matched", na=False)]["Order_Number"].unique()
    assert sorted(matched_orders) == sorted(expected_matches)


@pytest.mark.parametrize(
    "invalid_range",
    [
        "100-10",  # Reversed range
        "10-",     # Missing end
        "-100",    # Missing start
        "abc-xyz", # Non-numeric
        "invalid", # Invalid format
        "",        # Empty
    ],
)
def test_range_operators_invalid_input(sample_df, invalid_range, caplog):
    """Test 'between' operator with invalid range formats."""
    import logging

    rules = [
        {
            "match": "ALL",
            "conditions": [{"field": "Total_Price", "operator": "between", "value": invalid_range}],
            "actions": [{"type": "ADD_INTERNAL_TAG", "value": "matched"}],
        }
    ]
    engine = RuleEngine(rules)

    with caplog.at_level(logging.WARNING):
        result_df = engine.apply(sample_df.copy())

    # Should not match any rows
    matched_orders = result_df[result_df["Internal_Tags"].str.contains("matched", na=False)]
    assert len(matched_orders) == 0

    # Should log warning for non-empty invalid inputs
    if invalid_range and invalid_range.strip():
        assert any("Invalid range" in record.message or "range format" in record.message for record in caplog.records)


# --- Date Operators Tests ---


@pytest.mark.parametrize(
    "operator,value,expected_matches",
    [
        ("date before", "2024-01-30", ["#2001"]),
        ("date before", "2024-02-01", ["#2001", "#2002", "#2004"]),
        ("date after", "2024-01-30", ["#2003", "#2005"]),
        ("date after", "2024-01-14", ["#2001", "#2002", "#2003", "#2004", "#2005"]),
        ("date equals", "2024-01-30", ["#2002", "#2004"]),
        ("date equals", "2024-02-15", ["#2003", "#2005"]),
        ("date equals", "2024-01-15", ["#2001"]),
    ],
)
def test_date_operators(date_sample_df, operator, value, expected_matches):
    """Tests 'date before', 'date after', and 'date equals' operators."""
    rules = [
        {
            "match": "ALL",
            "conditions": [{"field": "Order_Date", "operator": operator, "value": value}],
            "actions": [{"type": "ADD_INTERNAL_TAG", "value": "matched"}],
        }
    ]
    engine = RuleEngine(rules)
    result_df = engine.apply(date_sample_df.copy())

    matched_orders = result_df[result_df["Internal_Tags"].str.contains("matched", na=False)]["Order_Number"].unique()
    assert sorted(matched_orders) == sorted(expected_matches)


def test_date_operators_multiple_formats(date_sample_df):
    """Test that date operators handle multiple date formats correctly."""
    # All dates should be normalized to same comparison format
    rules = [
        {
            "match": "ALL",
            "conditions": [{"field": "Order_Date", "operator": "date equals", "value": "30/01/2024"}],
            "actions": [{"type": "ADD_INTERNAL_TAG", "value": "matched"}],
        }
    ]
    engine = RuleEngine(rules)
    result_df = engine.apply(date_sample_df.copy())

    # Should match rows with "2024-01-30" and "30/01/2024"
    matched_orders = result_df[result_df["Internal_Tags"].str.contains("matched", na=False)]["Order_Number"].unique()
    assert sorted(matched_orders) == sorted(["#2002", "#2004"])


@pytest.mark.parametrize(
    "invalid_date",
    [
        "not-a-date",
        "2024-13-45",  # Invalid month/day
        "32/01/2024",  # Invalid day
        "",
        "invalid",
    ],
)
def test_date_operators_invalid_input(date_sample_df, invalid_date, caplog):
    """Test date operators with invalid date formats."""
    import logging

    rules = [
        {
            "match": "ALL",
            "conditions": [{"field": "Order_Date", "operator": "date before", "value": invalid_date}],
            "actions": [{"type": "ADD_INTERNAL_TAG", "value": "matched"}],
        }
    ]
    engine = RuleEngine(rules)

    with caplog.at_level(logging.WARNING):
        result_df = engine.apply(date_sample_df.copy())

    # Should not match any rows
    matched_orders = result_df[result_df["Internal_Tags"].str.contains("matched", na=False)]
    assert len(matched_orders) == 0

    # Should log warning
    if invalid_date and invalid_date not in ["", "not-a-date", "invalid"]:
        assert any("Invalid rule date" in record.message for record in caplog.records)


# --- Regex Operator Tests ---


@pytest.mark.parametrize(
    "pattern,expected_matches",
    [
        (r"^SKU-\d{4}$", ["#2001", "#2004"]),
        (r"SKU-", ["#2001", "#2002", "#2004"]),  # Contains "SKU-"
        (r"^SKU-[A-Z]{4}$", ["#2002"]),
        (r"^OTHER", ["#2003"]),
        (r"-999$", ["#2005"]),  # Ends with -999
        (r".*", ["#2001", "#2002", "#2003", "#2004", "#2005"]),  # Match all
    ],
)
def test_regex_operator(date_sample_df, pattern, expected_matches):
    """Tests 'matches regex' operator with various patterns."""
    rules = [
        {
            "match": "ALL",
            "conditions": [{"field": "SKU", "operator": "matches regex", "value": pattern}],
            "actions": [{"type": "ADD_INTERNAL_TAG", "value": "matched"}],
        }
    ]
    engine = RuleEngine(rules)
    result_df = engine.apply(date_sample_df.copy())

    matched_orders = result_df[result_df["Internal_Tags"].str.contains("matched", na=False)]["Order_Number"].unique()
    assert sorted(matched_orders) == sorted(expected_matches)


@pytest.mark.parametrize(
    "invalid_pattern",
    [
        "[invalid",     # Unclosed bracket
        "(?P<invalid",  # Unclosed group
        "*invalid",     # Invalid quantifier
        "(?P<>)",       # Empty group name
    ],
)
def test_regex_operator_invalid_pattern(date_sample_df, invalid_pattern, caplog):
    """Test 'matches regex' operator with invalid regex patterns."""
    import logging

    rules = [
        {
            "match": "ALL",
            "conditions": [{"field": "SKU", "operator": "matches regex", "value": invalid_pattern}],
            "actions": [{"type": "ADD_INTERNAL_TAG", "value": "matched"}],
        }
    ]
    engine = RuleEngine(rules)

    with caplog.at_level(logging.WARNING):
        result_df = engine.apply(date_sample_df.copy())

    # Should not match any rows
    matched_orders = result_df[result_df["Internal_Tags"].str.contains("matched", na=False)]
    assert len(matched_orders) == 0

    # Should log warning about invalid regex
    assert any("Invalid regex pattern" in record.message for record in caplog.records)


# --- Integration Test ---


def test_all_new_operators_integration(sample_df, date_sample_df):
    """Integration test combining all new operators in a realistic scenario."""
    # Combine both DataFrames for comprehensive testing
    combined_df = pd.concat([sample_df, date_sample_df], ignore_index=True)

    rules = [
        {
            "name": "List operator rule",
            "match": "ALL",
            "conditions": [{"field": "Shipping_Provider", "operator": "in list", "value": "DHL,PostOne"}],
            "actions": [{"type": "ADD_INTERNAL_TAG", "value": "priority_courier"}],
        },
        {
            "name": "Range operator rule",
            "match": "ALL",
            "conditions": [{"field": "Total_Price", "operator": "between", "value": "75-150"}],
            "actions": [{"type": "ADD_INTERNAL_TAG", "value": "mid_value"}],
        },
        {
            "name": "Regex operator rule",
            "match": "ALL",
            "conditions": [{"field": "SKU", "operator": "matches regex", "value": r"^SKU-\d{4}$"}],
            "actions": [{"type": "ADD_INTERNAL_TAG", "value": "standard_sku"}],
        },
    ]

    engine = RuleEngine(rules)
    result_df = engine.apply(combined_df.copy())

    # Verify multiple tags can be applied
    priority_count = result_df[result_df["Internal_Tags"].str.contains("priority_courier", na=False)]
    assert len(priority_count) > 0

    mid_value_count = result_df[result_df["Internal_Tags"].str.contains("mid_value", na=False)]
    assert len(mid_value_count) > 0

    standard_sku_count = result_df[result_df["Internal_Tags"].str.contains("standard_sku", na=False)]
    assert len(standard_sku_count) > 0

    # Verify tags don't interfere with each other
    assert len(result_df) == len(combined_df)


# ========== NEW ACTION TYPES TESTS (v1.10.0) ==========

# COPY_FIELD Tests
def test_copy_field_basic(sample_df):
    """Test COPY_FIELD copies values correctly."""
    rules = [{
        "conditions": [{"field": "Order_Number", "operator": "equals", "value": "#1001"}],
        "actions": [{"type": "COPY_FIELD", "source": "SKU", "target": "Backup_SKU"}]
    }]

    engine = RuleEngine(rules)
    result_df = engine.apply(sample_df.copy())

    assert "Backup_SKU" in result_df.columns

    # Matched rows
    matched = result_df[result_df["Order_Number"] == "#1001"]
    for _, row in matched.iterrows():
        assert row["Backup_SKU"] == row["SKU"]

    # Unmatched rows should be empty
    unmatched = result_df[result_df["Order_Number"] != "#1001"]
    for _, row in unmatched.iterrows():
        assert row["Backup_SKU"] == ""


def test_copy_field_missing_source(sample_df):
    """Test COPY_FIELD with missing source column."""
    rules = [{
        "conditions": [{"field": "Order_Number", "operator": "equals", "value": "#1001"}],
        "actions": [{"type": "COPY_FIELD", "source": "NonExistent", "target": "Target"}]
    }]

    engine = RuleEngine(rules)
    result_df = engine.apply(sample_df.copy())

    # Should not crash, Target column should not be created
    assert "Target" not in result_df.columns


def test_copy_field_overwrite_existing(sample_df):
    """Test COPY_FIELD overwrites existing target column."""
    df = sample_df.copy()
    df["Backup_SKU"] = "OLD_VALUE"

    rules = [{
        "conditions": [{"field": "Order_Number", "operator": "equals", "value": "#1001"}],
        "actions": [{"type": "COPY_FIELD", "source": "SKU", "target": "Backup_SKU"}]
    }]

    engine = RuleEngine(rules)
    result_df = engine.apply(df)

    matched = result_df[result_df["Order_Number"] == "#1001"]
    for _, row in matched.iterrows():
        assert row["Backup_SKU"] == row["SKU"]
        assert row["Backup_SKU"] != "OLD_VALUE"


# SET_MULTI_TAGS Tests
def test_set_multi_tags_comma_separated(sample_df):
    """Test SET_MULTI_TAGS with comma-separated string."""
    rules = [{
        "conditions": [{"field": "Order_Number", "operator": "equals", "value": "#1001"}],
        "actions": [{"type": "SET_MULTI_TAGS", "value": "TAG1, TAG2, TAG3"}]
    }]

    engine = RuleEngine(rules)
    result_df = engine.apply(sample_df.copy())

    matched = result_df[result_df["Order_Number"] == "#1001"]
    for _, row in matched.iterrows():
        note = row["Status_Note"]
        assert "TAG1" in note
        assert "TAG2" in note
        assert "TAG3" in note


def test_set_multi_tags_no_duplicates(sample_df):
    """Test SET_MULTI_TAGS prevents duplicate tags."""
    df = sample_df.copy()
    df.loc[df["Order_Number"] == "#1001", "Status_Note"] = "TAG1, Existing"

    rules = [{
        "conditions": [{"field": "Order_Number", "operator": "equals", "value": "#1001"}],
        "actions": [{"type": "SET_MULTI_TAGS", "value": "TAG1, TAG2"}]
    }]

    engine = RuleEngine(rules)
    result_df = engine.apply(df)

    matched = result_df[result_df["Order_Number"] == "#1001"]
    for _, row in matched.iterrows():
        note = row["Status_Note"]
        # TAG1 should appear only once
        assert note.count("TAG1") == 1
        assert "TAG2" in note
        assert "Existing" in note


def test_set_multi_tags_list_format(sample_df):
    """Test SET_MULTI_TAGS with list format."""
    rules = [{
        "conditions": [{"field": "Order_Number", "operator": "equals", "value": "#1001"}],
        "actions": [{"type": "SET_MULTI_TAGS", "tags": ["ALPHA", "BETA", "GAMMA"]}]
    }]

    engine = RuleEngine(rules)
    result_df = engine.apply(sample_df.copy())

    matched = result_df[result_df["Order_Number"] == "#1001"]
    for _, row in matched.iterrows():
        note = row["Status_Note"]
        assert "ALPHA" in note
        assert "BETA" in note
        assert "GAMMA" in note


# ALERT_NOTIFICATION Tests
def test_alert_notification_info(sample_df, caplog):
    """Test ALERT_NOTIFICATION logs info messages."""
    import logging

    rules = [{
        "conditions": [{"field": "Order_Number", "operator": "equals", "value": "#1001"}],
        "actions": [{
            "type": "ALERT_NOTIFICATION",
            "message": "Test alert",
            "severity": "info"
        }]
    }]

    with caplog.at_level(logging.INFO):
        engine = RuleEngine(rules)
        engine.apply(sample_df.copy())

    assert "Test alert" in caplog.text
    assert "RULE ALERT" in caplog.text


def test_alert_notification_warning(sample_df, caplog):
    """Test ALERT_NOTIFICATION logs warning messages."""
    import logging

    rules = [{
        "conditions": [{"field": "Order_Number", "operator": "equals", "value": "#1001"}],
        "actions": [{
            "type": "ALERT_NOTIFICATION",
            "message": "Warning message",
            "severity": "warning"
        }]
    }]

    with caplog.at_level(logging.WARNING):
        engine = RuleEngine(rules)
        engine.apply(sample_df.copy())

    assert "Warning message" in caplog.text


def test_alert_notification_error(sample_df, caplog):
    """Test ALERT_NOTIFICATION logs error messages."""
    import logging

    rules = [{
        "conditions": [{"field": "Order_Number", "operator": "equals", "value": "#1001"}],
        "actions": [{
            "type": "ALERT_NOTIFICATION",
            "message": "Error message",
            "severity": "error"
        }]
    }]

    with caplog.at_level(logging.ERROR):
        engine = RuleEngine(rules)
        engine.apply(sample_df.copy())

    assert "Error message" in caplog.text


# CALCULATE Tests
@pytest.mark.parametrize("operation,expected", [
    ("add", 11),       # 10 + 1
    ("subtract", 9),   # 10 - 1
    ("multiply", 10),  # 10 * 1
    ("divide", 10.0),    # 10 / 1
])
def test_calculate_operations(sample_df, operation, expected):
    """Test CALCULATE with different operations."""
    df = sample_df.copy()
    df["Value1"] = 10
    df["Value2"] = 1

    rules = [{
        "conditions": [{"field": "Order_Number", "operator": "equals", "value": "#1001"}],
        "actions": [{
            "type": "CALCULATE",
            "operation": operation,
            "field1": "Value1",
            "field2": "Value2",
            "target": "Result"
        }]
    }]

    engine = RuleEngine(rules)
    result_df = engine.apply(df)

    matched = result_df[result_df["Order_Number"] == "#1001"]
    for _, row in matched.iterrows():
        assert row["Result"] == expected


def test_calculate_division_by_zero(sample_df):
    """Test CALCULATE handles division by zero."""
    df = sample_df.copy()
    df["Value1"] = 10
    df["Value2"] = 0

    rules = [{
        "conditions": [{"field": "Order_Number", "operator": "equals", "value": "#1001"}],
        "actions": [{
            "type": "CALCULATE",
            "operation": "divide",
            "field1": "Value1",
            "field2": "Value2",
            "target": "Result"
        }]
    }]

    engine = RuleEngine(rules)
    result_df = engine.apply(df)

    matched = result_df[result_df["Order_Number"] == "#1001"]
    for _, row in matched.iterrows():
        assert pd.isna(row["Result"])  # Should be NaN


def test_calculate_with_quantity(sample_df):
    """Test CALCULATE using existing Quantity field."""
    df = sample_df.copy()
    df["Price"] = 10.5

    rules = [{
        "conditions": [{"field": "Order_Number", "operator": "equals", "value": "#1001"}],
        "actions": [{
            "type": "CALCULATE",
            "operation": "multiply",
            "field1": "Quantity",
            "field2": "Price",
            "target": "Line_Total"
        }]
    }]

    engine = RuleEngine(rules)
    result_df = engine.apply(df)

    matched = result_df[result_df["Order_Number"] == "#1001"]
    for _, row in matched.iterrows():
        expected = row["Quantity"] * row["Price"]
        assert row["Line_Total"] == expected


# ADD_PRODUCT Tests
def test_add_product_basic(sample_df):
    """Test ADD_PRODUCT adds new rows."""
    original_len = len(sample_df)

    # #1001 has 2 rows
    rules = [{
        "conditions": [{"field": "Order_Number", "operator": "equals", "value": "#1001"}],
        "actions": [{"type": "ADD_PRODUCT", "sku": "BONUS-001", "quantity": 1}]
    }]

    engine = RuleEngine(rules)
    result_df = engine.apply(sample_df.copy())

    # Should add 2 bonus rows (one per matched row)
    assert len(result_df) == original_len + 2

    bonus_rows = result_df[result_df["SKU"] == "BONUS-001"]
    assert len(bonus_rows) == 2
    assert all(bonus_rows["Order_Number"] == "#1001")
    assert all(bonus_rows["Quantity"] == 1)


def test_add_product_quantity(sample_df):
    """Test ADD_PRODUCT respects quantity parameter."""
    rules = [{
        "conditions": [{"field": "Order_Number", "operator": "equals", "value": "#1001"}],
        "actions": [{"type": "ADD_PRODUCT", "sku": "BONUS-001", "quantity": 5}]
    }]

    engine = RuleEngine(rules)
    result_df = engine.apply(sample_df.copy())

    bonus_rows = result_df[result_df["SKU"] == "BONUS-001"]
    assert all(bonus_rows["Quantity"] == 5)


def test_add_product_tagging(sample_df):
    """Test ADD_PRODUCT tags new rows with rule_added_product."""
    df = sample_df.copy()
    # Додамо Internal_Tags колонку якщо її немає
    if "Internal_Tags" not in df.columns:
        df["Internal_Tags"] = "[]"

    rules = [{
        "conditions": [{"field": "Order_Number", "operator": "equals", "value": "#1001"}],
        "actions": [{"type": "ADD_PRODUCT", "sku": "BONUS-001", "quantity": 1}]
    }]

    engine = RuleEngine(rules)
    result_df = engine.apply(df)

    bonus_rows = result_df[result_df["SKU"] == "BONUS-001"]
    for _, row in bonus_rows.iterrows():
        assert "rule_added_product" in row["Internal_Tags"]


def test_add_product_clears_status_note(sample_df):
    """Test ADD_PRODUCT clears Status_Note for new rows."""
    df = sample_df.copy()
    df.loc[df["Order_Number"] == "#1001", "Status_Note"] = "EXISTING_TAG"

    rules = [{
        "conditions": [{"field": "Order_Number", "operator": "equals", "value": "#1001"}],
        "actions": [{"type": "ADD_PRODUCT", "sku": "BONUS-001", "quantity": 1}]
    }]

    engine = RuleEngine(rules)
    result_df = engine.apply(df)

    bonus_rows = result_df[result_df["SKU"] == "BONUS-001"]
    for _, row in bonus_rows.iterrows():
        assert row["Status_Note"] == ""


def test_add_product_multiple_orders(sample_df):
    """Test ADD_PRODUCT works with multiple matching orders."""
    rules = [{
        "conditions": [{"field": "Total_Price", "operator": "is greater than", "value": "60"}],
        "actions": [{"type": "ADD_PRODUCT", "sku": "GIFT-001", "quantity": 1}]
    }]

    engine = RuleEngine(rules)
    result_df = engine.apply(sample_df.copy())

    # Should add gift products for orders with Total_Price > 60
    gift_rows = result_df[result_df["SKU"] == "GIFT-001"]
    assert len(gift_rows) > 0

    # Verify all gifts have correct quantity
    assert all(gift_rows["Quantity"] == 1)


def test_add_product_uses_stock_data(sample_df):
    """Test ADD_PRODUCT uses Product_Name and Warehouse_Name from existing SKU in stock."""
    df = sample_df.copy()

    # Add a product with specific warehouse info to simulate stock data
    df.loc[len(df)] = {
        "Order_Number": "#9999",  # Different order
        "Order_Type": "Single",
        "Shipping_Provider": "DHL",
        "Total_Price": 10,
        "Tags": "",
        "Status_Note": "",
        "Order_Fulfillment_Status": "Fulfillable",
        "SKU": "BONUS-SKU",
        "Quantity": 100,  # Stock quantity
    }

    # Add Warehouse_Name and Product_Name columns
    df["Warehouse_Name"] = df["SKU"].copy()
    df["Product_Name"] = df["SKU"].copy()

    # Set specific values for our stock SKU
    df.loc[df["SKU"] == "BONUS-SKU", "Warehouse_Name"] = "Special Warehouse"
    df.loc[df["SKU"] == "BONUS-SKU", "Product_Name"] = "Bonus Product"
    df.loc[df["SKU"] == "BONUS-SKU", "Stock"] = 500

    # Now add this product to order #1001
    rules = [{
        "conditions": [{"field": "Order_Number", "operator": "equals", "value": "#1001"}],
        "actions": [{"type": "ADD_PRODUCT", "sku": "BONUS-SKU", "quantity": 1}]
    }]

    engine = RuleEngine(rules)
    result_df = engine.apply(df)

    # Find added bonus products in order #1001
    bonus_in_order = result_df[(result_df["SKU"] == "BONUS-SKU") & (result_df["Order_Number"] == "#1001")]

    assert len(bonus_in_order) == 2  # #1001 has 2 rows, so 2 bonus products added

    # Verify that Warehouse_Name and Product_Name come from stock data, not from order rows
    for _, row in bonus_in_order.iterrows():
        assert row["Warehouse_Name"] == "Special Warehouse", f"Expected 'Special Warehouse', got '{row['Warehouse_Name']}'"
        assert row["Product_Name"] == "Bonus Product", f"Expected 'Bonus Product', got '{row['Product_Name']}'"
        assert row["Quantity"] == 1  # Quantity from action, not stock
        if "Stock" in row:
            assert row["Stock"] == 500  # Stock value from stock data


# Integration Test
def test_all_new_actions_integration(sample_df):
    """Integration test using all 5 new action types."""
    df = sample_df.copy()
    df["Price"] = 10.0

    rules = [
        {
            "name": "Test all actions",
            "conditions": [{"field": "Order_Number", "operator": "equals", "value": "#1001"}],
            "actions": [
                {"type": "COPY_FIELD", "source": "SKU", "target": "Original_SKU"},
                {"type": "CALCULATE", "operation": "multiply", "field1": "Quantity", "field2": "Price", "target": "Total"},
                {"type": "SET_MULTI_TAGS", "value": "PROCESSED, CALCULATED"},
                {"type": "ALERT_NOTIFICATION", "message": "Integration test", "severity": "info"},
                {"type": "ADD_PRODUCT", "sku": "BONUS-001", "quantity": 1},
            ]
        }
    ]

    engine = RuleEngine(rules)
    result_df = engine.apply(df)

    # Verify COPY_FIELD
    assert "Original_SKU" in result_df.columns

    # Verify CALCULATE
    assert "Total" in result_df.columns
    matched = result_df[(result_df["Order_Number"] == "#1001") & (result_df["SKU"] != "BONUS-001")]
    for _, row in matched.iterrows():
        assert row["Total"] == row["Quantity"] * row["Price"]

    # Verify SET_MULTI_TAGS
    for _, row in matched.iterrows():
        assert "PROCESSED" in row["Status_Note"]
        assert "CALCULATED" in row["Status_Note"]

    # Verify ADD_PRODUCT
    bonus_rows = result_df[result_df["SKU"] == "BONUS-001"]
    assert len(bonus_rows) == 2  # #1001 has 2 original rows
