import sys
import os
import pandas as pd

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from shopify_tool.core import _apply_tagging_rules


def make_final_df():
    return pd.DataFrame({
        'Order_Number': ['T1', 'T1', 'T2', 'T3'],
        'SKU': ['02-FACE-1001', 'SKU-X', '02-FACE-1002', '02-FACE-1003'],
        'Status_Note': ['', '', '', '']
    })


def test_apply_tagging_rules_single_special():
    df = make_final_df()
    config = {'tagging_rules': {'special_sku_tags': {'02-FACE-1001': 'MASK'}, 'composite_order_tag': 'BOX'}}
    out = _apply_tagging_rules(df.copy(), config)
    # Order T1 contains special SKU and another SKU -> should have MASK and BOX
    notes_t1 = out[out['Order_Number'] == 'T1']['Status_Note'].iloc[0]
    assert 'MASK' in notes_t1
    assert 'BOX' in notes_t1


def test_apply_tagging_rules_multiple_orders():
    df = make_final_df()
    config = {'tagging_rules': {'special_sku_tags': {'02-FACE-1002': 'MASK', '02-FACE-1003': 'MASK'}, 'composite_order_tag': 'BOX'}}
    out = _apply_tagging_rules(df.copy(), config)
    # T2 has only special SKU -> MASK only
    notes_t2 = out[out['Order_Number'] == 'T2']['Status_Note'].iloc[0]
    assert notes_t2 == 'MASK'
    # T3 has only special SKU -> MASK only
    notes_t3 = out[out['Order_Number'] == 'T3']['Status_Note'].iloc[0]
    assert notes_t3 == 'MASK'
