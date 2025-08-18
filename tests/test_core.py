import sys
import os
import pandas as pd

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from shopify_tool import core


def make_stock_df():
    return pd.DataFrame({
        'Артикул': ['02-FACE-1001', 'SKU-2'],
        'Име': ['Mask A', 'Item 2'],
        'Наличност': [5, 10]
    })


def make_orders_df():
    return pd.DataFrame({
        'Name': ['1001', '1002'],
        'Lineitem sku': ['02-FACE-1001', 'SKU-2'],
        'Lineitem quantity': [2, 1],
        'Shipping Method': ['dhl', 'dpd'],
        'Shipping Country': ['BG', 'BG'],
        'Tags': ['', ''],
        'Notes': ['', '']
    })


def test_run_full_analysis_basic():
    stock_df = make_stock_df()
    orders_df = make_orders_df()
    # set threshold to 4 so final stock 3 will be flagged as Low Stock
    config = {'settings': {'low_stock_threshold': 4}, 'tagging_rules': {}}
    # inject test dfs
    config['test_stock_df'] = stock_df
    config['test_orders_df'] = orders_df
    config['test_history_df'] = pd.DataFrame({'Order_Number': []})

    success, output_path, final_df, stats = core.run_full_analysis(None, None, None, ';', config)
    assert success
    assert output_path is None
    assert 'Final_Stock' in final_df.columns
    # low stock alert should appear for SKU with final stock below threshold
    mask_rows = final_df[final_df['SKU'] == '02-FACE-1001']
    assert any(mask_rows['Stock_Alert'].str.contains('Low Stock'))
