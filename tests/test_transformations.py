import pandas as pd
import pytest
from shopify_tool.transformations import apply_set_decoding, apply_packaging_rules

@pytest.fixture
def sample_orders_df():
    """Create a sample DataFrame for testing."""
    data = {
        'Order_Number': ['#1001', '#1001', '#1002', '#1003'],
        'SKU': ['ITEM_A', 'SET_1', 'ITEM_B', 'SET_1'],
        'Quantity': [1, 1, 2, 2],
        'Product_Name': ['Item A', 'The Main Set', 'Item B', 'The Main Set'],
        'Notes': ['', '', 'Some note', '']
    }
    return pd.DataFrame(data)

def test_apply_set_decoding_single_set(sample_orders_df):
    """Test that a single set is correctly decoded."""
    decoding_rules = [
        {
            "set_sku": "SET_1",
            "components": {
                "COMP_A": 1,
                "COMP_B": 2
            }
        }
    ]

    transformed_df = apply_set_decoding(sample_orders_df, decoding_rules)

    # Check that original sets are gone
    assert 'SET_1' not in transformed_df['SKU'].values

    # Check that components are added
    assert 'COMP_A' in transformed_df['SKU'].values
    assert 'COMP_B' in transformed_df['SKU'].values

    # Check quantities for order #1001
    comp_a_row = transformed_df[(transformed_df['Order_Number'] == '#1001') & (transformed_df['SKU'] == 'COMP_A')]
    assert comp_a_row['Quantity'].iloc[0] == 1

    # Check quantities for order #1003 (original set quantity was 2)
    comp_b_row = transformed_df[(transformed_df['Order_Number'] == '#1003') & (transformed_df['SKU'] == 'COMP_B')]
    assert comp_b_row['Quantity'].iloc[0] == 4 # 2 * 2

    # Check that other items are preserved
    assert 'ITEM_A' in transformed_df['SKU'].values
    assert 'ITEM_B' in transformed_df['SKU'].values

    # Check total rows: 2 original non-set rows + 2 components * 2 sets = 6 rows
    assert len(transformed_df) == 6

def test_apply_set_decoding_no_rules():
    """Test that the DataFrame is unchanged when no rules are provided."""
    df = pd.DataFrame({'SKU': ['A'], 'Quantity': [1]})
    transformed_df = apply_set_decoding(df.copy(), [])
    pd.testing.assert_frame_equal(df, transformed_df)

def test_apply_set_decoding_no_matching_sets(sample_orders_df):
    """Test that the DataFrame is unchanged if no sets in the orders match the rules."""
    decoding_rules = [{"set_sku": "SET_NONEXISTENT", "components": {"COMP_X": 1}}]
    transformed_df = apply_set_decoding(sample_orders_df.copy(), decoding_rules)
    pd.testing.assert_frame_equal(sample_orders_df, transformed_df)


@pytest.fixture
def sample_orders_for_packaging():
    """Create a sample DataFrame for packaging rule testing."""
    data = {
        'Order_Number': ['#1', '#2', '#2', '#3', '#3', '#3'],
        'SKU': ['A', 'B', 'C', 'D', 'E', 'F'],
        'Quantity': [1, 1, 1, 1, 1, 1],
    }
    return pd.DataFrame(data)

def test_apply_packaging_rules_multi_item(sample_orders_for_packaging):
    """Test that a packaging item is added to multi-item orders."""
    packaging_rules = [
        {
            "name": "Box for Multi",
            "conditions": [{"field": "Order_Type", "operator": "==", "value": "Multi"}],
            "action": {"type": "ADD_PACKAGING_ITEM", "sku": "BOX_M", "quantity": 1}
        }
    ]

    transformed_df = apply_packaging_rules(sample_orders_for_packaging, packaging_rules)

    # Check that boxes were added for orders #2 and #3
    assert len(transformed_df[transformed_df['SKU'] == 'BOX_M']) == 2

    # Check that order #1 (single item) did not get a box
    assert not transformed_df[(transformed_df['Order_Number'] == '#1') & (transformed_df['SKU'] == 'BOX_M')].any().any()

    # Check total rows: 6 original + 2 boxes = 8 rows
    assert len(transformed_df) == 8

def test_apply_packaging_rules_single_item():
    """Test that a packaging item is added to single-item orders."""
    df = pd.DataFrame({'Order_Number': ['#1'], 'SKU': ['A'], 'Quantity': [1]})
    packaging_rules = [
        {
            "name": "Envelope for Single",
            "conditions": [{"field": "Order_Type", "operator": "==", "value": "Single"}],
            "action": {"type": "ADD_PACKAGING_ITEM", "sku": "ENVELOPE", "quantity": 1}
        }
    ]
    transformed_df = apply_packaging_rules(df, packaging_rules)
    assert 'ENVELOPE' in transformed_df['SKU'].values
    assert len(transformed_df) == 2

def test_apply_packaging_rules_no_rules(sample_orders_for_packaging):
    """Test that the DataFrame is unchanged when no packaging rules are provided."""
    transformed_df = apply_packaging_rules(sample_orders_for_packaging.copy(), [])
    pd.testing.assert_frame_equal(sample_orders_for_packaging, transformed_df)
