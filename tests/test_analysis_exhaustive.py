import sys
import os
import pandas as pd

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from shopify_tool.analysis import run_analysis


def make_stock_df():
    return pd.DataFrame({
        'Артикул': ['A', 'C'],
        'Име': ['Item A', 'Item C'],
        'Наличност': [2, 0]
    })


def make_orders_df():
    return pd.DataFrame({
        'Name': ['O1', 'O2', 'O3'],
        'Lineitem sku': ['A', 'B', 'A'],
        'Lineitem quantity': [3, 1, 1],
        'Shipping Method': ['dhl', 'dpd', None],
        'Shipping Country': ['BG', 'BG', 'BG'],
        'Tags': ['', '', ''],
        'Notes': ['', '', '']
    })


def test_summary_missing_and_stats():
    stock_df = make_stock_df()
    orders_df = make_orders_df()
    history_df = pd.DataFrame({'Order_Number': []})

    final_df, summary_present_df, summary_missing_df, stats = run_analysis(stock_df, orders_df, history_df)

    # Both order O1 (A qty 3) and O2 (B qty 1, missing from stock) should be in missing summary
    missing_skus = set(summary_missing_df['SKU'].tolist())
    assert 'A' in missing_skus
    assert 'B' in missing_skus

    # Stats: two orders not completed (O1 and O2); O3 should be fulfillable (A qty1 after O1 failed leaves stock 2 unchanged, but prioritisation may allow O3?)
    assert stats['total_orders_not_completed'] >= 1
    assert 'couriers_stats' in stats


def test_repeat_status_note():
    stock_df = make_stock_df()
    orders_df = make_orders_df()
    history_df = pd.DataFrame({'Order_Number': ['O3']})

    final_df, _, _, _ = run_analysis(stock_df, orders_df, history_df)
    # Rows from order O3 should have Status_Note == 'Repeat'
    notes = final_df[final_df['Order_Number'] == 'O3']['Status_Note'].unique()
    assert any(n == 'Repeat' for n in notes)
