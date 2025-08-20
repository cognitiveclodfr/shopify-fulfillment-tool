import pytest
import pandas as pd
from shopify_tool.rules import RuleEngine

@pytest.fixture
def sample_df():
    """Provides a sample DataFrame for testing."""
    data = {
        'Order_Number': ['#1001', '#1001', '#1002', '#1003', '#1004'],
        'Order_Type': ['Single', 'Single', 'Multi', 'Multi', 'Single'],
        'Shipping_Provider': ['DHL', 'DHL', 'PostOne', 'DPD', 'DHL'],
        'Total_Price': [50, 50, 150, 200, 80],
        'Tags': ['Tag1', 'Tag1', '', 'Urgent', ''],
        'Order_Fulfillment_Status': ['Fulfillable', 'Fulfillable', 'Fulfillable', 'Not Fulfillable', 'Fulfillable'],
        'SKU': ['SKU-A', 'SKU-B', 'SKU-C', 'SKU-D', 'SKU-E'],
        'Quantity': [1, 1, 2, 3, 1]
    }
    return pd.DataFrame(data)

def test_add_tag_with_simple_rule(sample_df):
    """
    Tests a simple rule to add a tag based on a single condition.
    """
    rules = [
        {
            "name": "Tag DHL Orders",
            "match": "ALL",
            "conditions": [
                { "field": "Shipping_Provider", "operator": "equals", "value": "DHL" }
            ],
            "actions": [
                { "type": "ADD_TAG", "value": "DHL-SHIP" }
            ]
        }
    ]

    engine = RuleEngine(rules)
    result_df = engine.apply(sample_df.copy())

    # Check that rows with 'DHL' got the new tag
    dhl_rows = result_df[result_df['Shipping_Provider'] == 'DHL']
    assert all(dhl_rows['Tags'].str.contains('DHL-SHIP'))

    # Check that other rows did not get the tag
    other_rows = result_df[result_df['Shipping_Provider'] != 'DHL']
    assert not any(other_rows['Tags'].str.contains('DHL-SHIP'))

def test_set_priority_with_multiple_conditions_all(sample_df):
    """
    Tests a rule with multiple 'AND' conditions.
    """
    rules = [
        {
            "name": "High Priority Multi-Item Orders",
            "match": "ALL", # AND
            "conditions": [
                { "field": "Order_Type", "operator": "equals", "value": "Multi" },
                { "field": "Total_Price", "operator": "is greater than", "value": 100 }
            ],
            "actions": [
                { "type": "SET_PRIORITY", "value": "High" }
            ]
        }
    ]

    engine = RuleEngine(rules)
    result_df = engine.apply(sample_df.copy())

    # Order #1002 and #1003 should match
    assert result_df.loc[result_df['Order_Number'] == '#1002', 'Priority'].iloc[0] == 'High'
    assert result_df.loc[result_df['Order_Number'] == '#1003', 'Priority'].iloc[0] == 'High'

    # Others should not match
    assert result_df.loc[result_df['Order_Number'] == '#1001', 'Priority'].iloc[0] == 'Normal'
    assert result_df.loc[result_df['Order_Number'] == '#1004', 'Priority'].iloc[0] == 'Normal'

def test_set_status_with_multiple_conditions_any(sample_df):
    """
    Tests a rule with multiple 'OR' conditions.
    """
    rules = [
        {
            "name": "Review DPD or Urgent Orders",
            "match": "ANY", # OR
            "conditions": [
                { "field": "Shipping_Provider", "operator": "equals", "value": "DPD" },
                { "field": "Tags", "operator": "contains", "value": "Urgent" }
            ],
            "actions": [
                { "type": "SET_STATUS", "value": "Manual Review" }
            ]
        }
    ]

    engine = RuleEngine(rules)
    result_df = engine.apply(sample_df.copy())

    # Order #1003 matches both conditions
    assert result_df.loc[result_df['Order_Number'] == '#1003', 'Order_Fulfillment_Status'].iloc[0] == 'Manual Review'

    # Check non-matching orders
    assert result_df.loc[result_df['Order_Number'] == '#1001', 'Order_Fulfillment_Status'].iloc[0] == 'Fulfillable'
    assert result_df.loc[result_df['Order_Number'] == '#1002', 'Order_Fulfillment_Status'].iloc[0] == 'Fulfillable'

def test_no_action_if_no_match(sample_df):
    """
    Ensures no changes are made if no rules match.
    """
    rules = [
        {
            "name": "Non-existent condition",
            "match": "ALL",
            "conditions": [
                { "field": "Shipping_Provider", "operator": "equals", "value": "FedEx" }
            ],
            "actions": [
                { "type": "ADD_TAG", "value": "FEDEX-SHIP" }
            ]
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
            "conditions": [
                { "field": "SKU", "operator": "equals", "value": "SKU-C" }
            ],
            "actions": [
                { "type": "EXCLUDE_SKU", "value": "SKU-C" }
            ]
        }
    ]

    engine = RuleEngine(rules)
    result_df = engine.apply(sample_df.copy())

    # The quantity for SKU-C in order #1002 should now be 0
    sku_c_row = result_df[result_df['SKU'] == 'SKU-C']
    assert sku_c_row['Quantity'].iloc[0] == 0
    assert 'SKU_EXCLUDED' in sku_c_row['Status_Note'].iloc[0]

    # Other quantities should be unaffected
    assert result_df.loc[result_df['SKU'] == 'SKU-A', 'Quantity'].iloc[0] == 1
    assert result_df.loc[result_df['SKU'] == 'SKU-D', 'Quantity'].iloc[0] == 3

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
            "actions": [
                { "type": "ADD_TAG", "value": "SHOULD-NOT-BE-ADDED" }
            ]
        }
    ]

    engine = RuleEngine(rules)
    result_df = engine.apply(sample_df.copy())

    assert not any(result_df['Tags'].str.contains('SHOULD-NOT-BE-ADDED', na=False))
