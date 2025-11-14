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


def test_set_priority_with_multiple_conditions_all(sample_df):
    """
    Tests a rule with multiple 'AND' conditions.
    """
    rules = [
        {
            "name": "High Priority Multi-Item Orders",
            "match": "ALL",  # AND
            "conditions": [
                {"field": "Order_Type", "operator": "equals", "value": "Multi"},
                {"field": "Total_Price", "operator": "is greater than", "value": 100},
            ],
            "actions": [{"type": "SET_PRIORITY", "value": "High"}],
        }
    ]

    engine = RuleEngine(rules)
    result_df = engine.apply(sample_df.copy())

    # Order #1002 and #1003 should match
    assert result_df.loc[result_df["Order_Number"] == "#1002", "Priority"].iloc[0] == "High"
    assert result_df.loc[result_df["Order_Number"] == "#1003", "Priority"].iloc[0] == "High"

    # Others should not match
    assert result_df.loc[result_df["Order_Number"] == "#1001", "Priority"].iloc[0] == "Normal"
    assert result_df.loc[result_df["Order_Number"] == "#1004", "Priority"].iloc[0] == "Normal"


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


def test_exclude_sku_action(sample_df):
    """
    Tests the 'EXCLUDE_SKU' action.
    This action should set the quantity of the matching SKU to 0.
    """
    rules = [
        {
            "name": "Exclude SKU-C from all orders",
            "match": "ALL",
            "conditions": [{"field": "SKU", "operator": "equals", "value": "SKU-C"}],
            "actions": [{"type": "EXCLUDE_SKU", "value": "SKU-C"}],
        }
    ]

    engine = RuleEngine(rules)
    result_df = engine.apply(sample_df.copy())

    # The quantity for SKU-C in order #1002 should now be 0
    sku_c_row = result_df[result_df["SKU"] == "SKU-C"]
    assert sku_c_row["Quantity"].iloc[0] == 0
    assert "SKU_EXCLUDED" in sku_c_row["Status_Note"].iloc[0]

    # Other quantities should be unaffected
    assert result_df.loc[result_df["SKU"] == "SKU-A", "Quantity"].iloc[0] == 1
    assert result_df.loc[result_df["SKU"] == "SKU-D", "Quantity"].iloc[0] == 3


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
            "actions": [{"type": "SET_PRIORITY", "value": "Match"}],
        }
    ]
    engine = RuleEngine(rules)
    result_df = engine.apply(sample_df.copy())

    matched_orders = result_df[result_df["Priority"] == "Match"]["Order_Number"].unique()
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
            "actions": [{"type": "SET_PRIORITY", "value": "Match"}],
        }
    ]
    engine = RuleEngine(rules)
    result_df = engine.apply(sample_df.copy())

    matched_orders = result_df[result_df["Priority"] == "Match"]["Order_Number"].unique()
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
        {"actions": [{"type": "SET_PRIORITY"}]},
        {"actions": [{"type": "ADD_TAG"}]},
        {"actions": [{"type": "EXCLUDE_FROM_REPORT"}]},
    ]
    engine = RuleEngine(rules)
    engine._prepare_df_for_actions(df)
    assert "Priority" in df.columns
    assert "Status_Note" in df.columns
    assert "_is_excluded" in df.columns


def test_exclude_from_report_action(sample_df):
    """Tests the EXCLUDE_FROM_REPORT action sets the internal flag correctly."""
    rules = [
        {
            "conditions": [{"field": "Order_Number", "operator": "equals", "value": "#1002"}],
            "actions": [{"type": "EXCLUDE_FROM_REPORT"}],
        }
    ]
    engine = RuleEngine(rules)
    result_df = engine.apply(sample_df.copy())
    assert result_df.loc[result_df["Order_Number"] == "#1002", "_is_excluded"].all()
    assert not result_df.loc[result_df["Order_Number"] != "#1002", "_is_excluded"].any()


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
                {"type": "SET_PACKAGING_TAG", "value": "SMALL_BAG"}
            ]
        }
    ]

    engine = RuleEngine(rules)
    result_df = engine.apply(order_level_sample_df.copy())

    # Order #1001 has 3 items, should get SMALL_BAG
    order_1001 = result_df[result_df["Order_Number"] == "#1001"]
    assert all(order_1001["Packaging_Tags"] == "SMALL_BAG")

    # Order #1002 has 2 items, should get SMALL_BAG
    order_1002 = result_df[result_df["Order_Number"] == "#1002"]
    assert all(order_1002["Packaging_Tags"] == "SMALL_BAG")

    # Order #1003 has 1 item, should get SMALL_BAG
    order_1003 = result_df[result_df["Order_Number"] == "#1003"]
    assert all(order_1003["Packaging_Tags"] == "SMALL_BAG")


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
                {"type": "SET_PACKAGING_TAG", "value": "BOX"},
                {"type": "ADD_ORDER_TAG", "value": "OVERSIZED"}
            ]
        }
    ]

    engine = RuleEngine(rules)
    result_df = engine.apply(order_level_sample_df.copy())

    # Order #1002 has OVERSIZED_001, should get BOX and OVERSIZED tag
    order_1002 = result_df[result_df["Order_Number"] == "#1002"]
    assert all(order_1002["Packaging_Tags"] == "BOX")
    assert all(order_1002["Status_Note"].str.contains("OVERSIZED"))

    # Other orders should not have these
    order_1001 = result_df[result_df["Order_Number"] == "#1001"]
    assert not any(order_1001["Packaging_Tags"] == "BOX")


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

    # Order #1003 has quantity=5, should get HIGH_QTY tag
    order_1003 = result_df[result_df["Order_Number"] == "#1003"]
    assert all(order_1003["Status_Note"].str.contains("HIGH_QTY"))

    # Order #1001 has total quantity=3, should not get tag
    order_1001 = result_df[result_df["Order_Number"] == "#1001"]
    assert not any(order_1001["Status_Note"].str.contains("HIGH_QTY"))


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
                {"type": "SET_PACKAGING_TAG", "value": "SMALL_BAG"}
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

    # All orders should have SMALL_BAG (order-level)
    assert all(result_df["Packaging_Tags"] == "SMALL_BAG")

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


def test_set_packaging_tag_action(order_level_sample_df):
    """Tests the SET_PACKAGING_TAG action creates and sets the column correctly."""
    rules = [
        {
            "name": "Test packaging tag",
            "level": "order",
            "match": "ALL",
            "conditions": [
                {"field": "item_count", "operator": "is greater than", "value": "0"}
            ],
            "actions": [
                {"type": "SET_PACKAGING_TAG", "value": "TEST_TAG"}
            ]
        }
    ]

    engine = RuleEngine(rules)
    result_df = engine.apply(order_level_sample_df.copy())

    # All rows should have the Packaging_Tags column
    assert "Packaging_Tags" in result_df.columns

    # All rows should have TEST_TAG
    assert all(result_df["Packaging_Tags"] == "TEST_TAG")


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

    # All rows should have ORDER_TAG in Status_Note
    assert all(result_df["Status_Note"].str.contains("ORDER_TAG"))

    # Apply rules again - should not duplicate tags
    result_df2 = engine.apply(result_df)
    for note in result_df2["Status_Note"]:
        assert note.count("ORDER_TAG") == 1  # Should only appear once
