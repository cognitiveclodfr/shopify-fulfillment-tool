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

