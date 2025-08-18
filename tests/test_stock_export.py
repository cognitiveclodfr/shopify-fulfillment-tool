import sys
import os
import pandas as pd

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from shopify_tool import stock_export


def test_create_stock_export_no_template(tmp_path):
    df = pd.DataFrame({
        'Order_Fulfillment_Status': ['Fulfillable'],
        'SKU': ['S1'],
        'Quantity': [1]
    })
    # Use a template path that doesn't exist
    template = str(tmp_path / "nonexistent_template.xls")
    out_file = str(tmp_path / "out.xls")
    # Should not raise, just print error and return
    stock_export.create_stock_export(df, template, out_file, report_name="TestStockExport", filters=None)
    # No file should be created
    assert not os.path.exists(out_file)
