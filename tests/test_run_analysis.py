
import sys
import os
import pandas as pd
import pytest
# Додаємо корінь проекту у sys.path для коректного імпорту
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from shopify_tool.analysis import run_analysis

def make_test_data():
    # Stock: 2 items, one with zero stock
    stock_df = pd.DataFrame({
        'Артикул': ['SKU1', 'SKU2'],
        'Име': ['Product 1', 'Product 2'],
        'Наличност': [5, 0]
    })
    # Orders: 2 orders, one fulfillable, one not
    orders_df = pd.DataFrame({
        'Name': ['Order1', 'Order2'],
        'Lineitem sku': ['SKU1', 'SKU2'],
        'Lineitem quantity': [3, 2],
        'Shipping Method': ['dhl express', 'DPD Standard'],
        'Shipping Country': ['BG', 'RO'],
        'Tags': ['', ''],
        'Notes': ['', '']
    })
    # History: empty for simplicity
    history_df = pd.DataFrame({'Order_Number': []})
    return stock_df, orders_df, history_df

def test_run_analysis_basic():
    stock_df, orders_df, history_df = make_test_data()
    final_df, summary_present_df, summary_missing_df, stats = run_analysis(stock_df, orders_df, history_df)
    # Check fulfillment status
    assert final_df.loc[final_df['Order_Number'] == 'Order1', 'Order_Fulfillment_Status'].iloc[0] == 'Fulfillable'
    assert final_df.loc[final_df['Order_Number'] == 'Order2', 'Order_Fulfillment_Status'].iloc[0] == 'Not Fulfillable'
    # Check summary_present_df
    assert summary_present_df['SKU'].tolist() == ['SKU1']
    # Check summary_missing_df
    assert summary_missing_df['SKU'].tolist() == ['SKU2']
    assert summary_missing_df['Total Quantity'].iloc[0] == 2
    # Check stats
    assert stats['total_orders_completed'] == 1
    assert stats['total_orders_not_completed'] == 1
