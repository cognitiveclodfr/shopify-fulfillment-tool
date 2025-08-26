import pytest
import pandas as pd
import sys
import os

# Add the project root to the Python path to allow for correct module imports
# This ensures that we can import from the 'shopify_tool' package
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from shopify_tool.analysis import _generalize_shipping_method

# Test cases for the _generalize_shipping_method function
# We use @pytest.mark.parametrize to run the same test with different inputs and expected outputs.
# This is an efficient way to test multiple scenarios.
@pytest.mark.parametrize("input_method, expected_output", [
    ("dhl express", "DHL"),
    ("some other dhl service", "DHL"),
    ("DPD Standard", "DPD"),
    ("dpd", "DPD"),
    ("international shipping", "PostOne"),
    ("Some Custom Method", "Some Custom Method"),
    ("unknown", "Unknown"),
    (None, "Unknown"),
    (pd.NA, "Unknown"),
    ("", ""), # An empty string should remain an empty string, or be handled as 'Unknown'
])
def test_generalize_shipping_method(input_method, expected_output):
    """
    Tests the _generalize_shipping_method function with various inputs.
    
    Args:
        input_method (str or None): The raw shipping method string to test.
        expected_output (str): The expected standardized string.
    """
    # The assert statement checks if the function's output matches the expected output.
    # If they don't match, pytest will report a failure.
    assert _generalize_shipping_method(input_method) == expected_output


from shopify_tool.analysis import run_analysis

def test_fulfillment_prioritization_logic():
    """
    Tests that the fulfillment logic correctly prioritizes orders based on:
    1. Multi-item orders before single-item orders.
    2. Older orders (lower order number) before newer orders.
    """
    # Create a stock of 4 for a single SKU. This is the key to the test.
    # It's enough to fulfill the two multi-item orders (2+2=4), but not any of the single-item orders.
    stock_df = pd.DataFrame({
        'Артикул': ['SKU-1'],
        'Име': ['Test Product'],
        'Наличност': [4]
    })

    # Create four orders for the same SKU with different priorities
    # Order 1001: Older, Multi-item (2 items) - Priority 1
    # Order 1002: Newer, Multi-item (2 items) - Priority 2
    # Order 1003: Older, Single-item (1 item) - Priority 3
    # Order 1004: Newer, Single-item (1 item) - Priority 4
    orders_df = pd.DataFrame({
        'Name': ['1002', '1002', '1001', '1001', '1004', '1003'],
        'Lineitem sku': ['SKU-1', 'SKU-1', 'SKU-1', 'SKU-1', 'SKU-1', 'SKU-1'],
        'Lineitem quantity': [1, 1, 1, 1, 1, 1], # Each row is one item
        'Shipping Method': ['dhl'] * 6,
        'Shipping Country': ['BG'] * 6,
        'Tags': [''] * 6,
        'Notes': [''] * 6
    })

    # Empty history
    history_df = pd.DataFrame(columns=['Order_Number', 'Execution_Date'])

    # With stock of 5, only the two multi-item orders should be fulfilled (2+2=4 items)
    # The single-item orders should not be fulfilled.
    final_df, _, _, _ = run_analysis(stock_df, orders_df, history_df)

    # Check status of each order
    status_map = final_df.drop_duplicates(subset=['Order_Number']).set_index('Order_Number')['Order_Fulfillment_Status']

    assert status_map['1001'] == 'Fulfillable' # Priority 1
    assert status_map['1002'] == 'Fulfillable' # Priority 2
    assert status_map['1003'] == 'Not Fulfillable' # Priority 3
    assert status_map['1004'] == 'Not Fulfillable' # Priority 4


def test_summary_missing_report():
    """
    Tests that the summary_missing_df is correctly generated for items that
    are missing because the required quantity exceeds the initial stock.
    """
    stock_df = pd.DataFrame({'Артикул': ['SKU-1'], 'Име': ['P1'], 'Наличност': [5]})
    orders_df = pd.DataFrame({
        'Name': ['1001'],
        'Lineitem sku': ['SKU-1'],
        'Lineitem quantity': [10], # Require 10, but only 5 are in stock
        'Shipping Method': ['dhl'],
        'Shipping Country': ['BG'],
        'Tags': [''],
        'Notes': ['']
    })
    history_df = pd.DataFrame(columns=['Order_Number', 'Execution_Date'])

    _, _, summary_missing_df, _ = run_analysis(stock_df, orders_df, history_df)

    assert not summary_missing_df.empty
    assert len(summary_missing_df) == 1
    assert summary_missing_df.iloc[0]['SKU'] == 'SKU-1'
    assert summary_missing_df.iloc[0]['Total Quantity'] == 10
