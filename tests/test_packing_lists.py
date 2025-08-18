import sys
import os
import pandas as pd

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from shopify_tool import packing_lists


def test_create_packing_list_minimal(tmp_path):
    # Build a small DataFrame that matches the analysis_df shape
    df = pd.DataFrame({
        'Order_Fulfillment_Status': ['Fulfillable', 'Fulfillable'],
        'Order_Number': ['A1', 'A1'],
        'SKU': ['S1', 'S2'],
        'Product_Name': ['P1', 'P2'],
        'Quantity': [1, 2],
        'Shipping_Provider': ['DHL', 'DHL'],
        'Destination_Country': ['BG', '']
    })

    out_file = tmp_path / "packing_test.xlsx"
    packing_lists.create_packing_list(df, str(out_file), report_name="TestReport", filters=None)
    assert out_file.exists()
