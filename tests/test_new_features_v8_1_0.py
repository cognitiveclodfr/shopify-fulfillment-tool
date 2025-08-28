import pytest
import pandas as pd
import sys
import os

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from shopify_tool import analysis, packing_lists, stock_export
from shopify_tool.rules import RuleEngine

@pytest.fixture
def sample_orders_df():
    """Provides a sample orders DataFrame for testing new features."""
    return pd.DataFrame({
        'Name': ['1001', '1001', '1002', '1003'],
        'Lineitem sku': ['SKU-A', 'SKU-B', 'SKU-A', 'SKU-C'],
        'Lineitem quantity': [1, 1, 2, 5],
        'Total': [150.0, 150.0, 50.0, 250.0],
        'Shipping Method': ['dhl'] * 4,
        'Shipping Country': ['BG'] * 4,
        'Tags': ['', 'tag1', '', ''],
        'Notes': ['note1', 'note1', '', '']
    })

@pytest.fixture
def sample_stock_df():
    """Provides a sample stock DataFrame."""
    return pd.DataFrame({
        'Артикул': ['SKU-A', 'SKU-B', 'SKU-C'],
        'Име': ['Product A', 'Product B', 'Product C'],
        'Наличност': [10, 10, 3] # Not enough stock for order 1003
    })

def test_system_note_and_total_price_columns_added(sample_orders_df, sample_stock_df):
    """
    Tests that run_analysis correctly adds the 'System_note' and 'Total Price' columns.
    """
    # Order 1001 is a repeat order
    history_df = pd.DataFrame({'Order_Number': ['1001'], 'Execution_Date': ['2023-01-01']})

    final_df, _, _, _ = analysis.run_analysis(sample_stock_df, sample_orders_df, history_df)

    # 1. Test for 'Total Price' column
    assert 'Total Price' in final_df.columns
    assert final_df[final_df['Order_Number'] == '1001']['Total Price'].iloc[0] == 150.0
    assert final_df[final_df['Order_Number'] == '1002']['Total Price'].iloc[0] == 50.0

    # 2. Test for 'System_note' column
    assert 'System_note' in final_df.columns
    # Check that order 1001 is marked as 'Repeat'
    assert final_df[final_df['Order_Number'] == '1001']['System_note'].iloc[0] == 'Repeat'
    # Check that other orders have an empty System_note
    assert final_df[final_df['Order_Number'] == '1002']['System_note'].iloc[0] == ''
    assert final_df[final_df['Order_Number'] == '1003']['System_note'].iloc[0] == ''

    # 3. Ensure 'Status_Note' is no longer present
    assert 'Status_Note' not in final_df.columns

def test_rule_engine_filter_by_order_number(sample_orders_df, sample_stock_df):
    """
    Tests that the RuleEngine can correctly filter by Order_Number.
    """
    history_df = pd.DataFrame(columns=['Order_Number', 'Execution_Date'])
    analysis_df, _, _, _ = analysis.run_analysis(sample_stock_df, sample_orders_df, history_df)

    # Rule: If Order_Number is '1002', add a tag 'Priority_Order'
    rules_config = [
        {
            "name": "Prioritize Order 1002",
            "match": "ALL",
            "conditions": [
                {"field": "Order_Number", "operator": "equals", "value": "1002"}
            ],
            "actions": [
                {"type": "ADD_TAG", "value": "Priority_Order"}
            ]
        }
    ]

    # The action adds to 'Status_Note', so we need to add it for the test
    if 'Status_Note' not in analysis_df.columns:
        analysis_df['Status_Note'] = ''

    engine = RuleEngine(rules_config)
    result_df = engine.apply(analysis_df)

    order_1002_notes = result_df[result_df['Order_Number'] == '1002']['Status_Note'].iloc[0]
    order_1001_notes = result_df[result_df['Order_Number'] == '1001']['Status_Note'].iloc[0]

    assert 'Priority_Order' in order_1002_notes
    assert 'Priority_Order' not in order_1001_notes

def test_packing_list_filter_by_order_number(tmp_path):
    """
    Tests that create_packing_list correctly filters by Order_Number.
    """
    analysis_df = pd.DataFrame({
        'Order_Number': ['1001', '1002', '1003'],
        'SKU': ['A', 'B', 'C'],
        'Order_Fulfillment_Status': ['Fulfillable', 'Fulfillable', 'Fulfillable'],
        'Shipping_Provider': ['DHL', 'DPD', 'DHL'],
        'Destination_Country': ['DE', 'FR', 'US'],
        'Product_Name': ['P_A', 'P_B', 'P_C'],
        'Quantity': [1,1,1]
    })

    output_file = tmp_path / "packing_list.xlsx"

    # Filter to only include order 1003
    report_config = {
        "name": "Test Order 1003",
        "output_filename": str(output_file),
        "filters": [
            {"field": "Order_Number", "operator": "==", "value": "1003"}
        ]
    }

    packing_lists.create_packing_list(analysis_df, str(output_file), report_config['name'], report_config['filters'])

    assert os.path.exists(output_file)

    # Read the output and verify its contents
    result_df = pd.read_excel(output_file)
    assert len(result_df) == 1
    assert str(result_df['Order_Number'].iloc[0]) == '1003'

def test_stock_export_filter_by_order_number(tmp_path):
    """
    Tests that create_stock_export correctly filters by Order_Number.
    """
    analysis_df = pd.DataFrame({
        'Order_Number': ['1001', '1002', '1003'],
        'SKU': ['SKU-A', 'SKU-B', 'SKU-A'], # Order 1003 contains SKU-A
        'Quantity': [1, 2, 3],
        'Order_Fulfillment_Status': ['Fulfillable', 'Fulfillable', 'Fulfillable']
    })

    # Create a valid .xls template file using xlwt
    import xlwt
    template_file = tmp_path / "template.xls"
    book = xlwt.Workbook()
    sheet = book.add_sheet('sheet1')
    sheet.write(0, 0, 'Артикул')
    sheet.write(0, 1, 'Количество')
    sheet.write(0, 2, 'Тип')
    book.save(str(template_file))

    # The function expects a full output file path, not a directory.
    output_file = tmp_path / "stock_export_output.xls"

    report_config = {
        "name": "Test Order 1003 Stock",
        "template": os.path.basename(template_file),
        "filters": [
            {"field": "Order_Number", "operator": "==", "value": "1003"}
        ]
    }

    # Call the function with the correct arguments
    stock_export.create_stock_export(
        analysis_df=analysis_df,
        template_file=str(template_file),
        output_file=str(output_file),
        report_name=report_config['name'],
        filters=report_config['filters']
    )

    assert os.path.exists(output_file)

    # Read the output file using xlrd
    import xlrd
    workbook = xlrd.open_workbook(str(output_file))
    sheet = workbook.sheet_by_index(0)

    # Expected result: SKU-A, quantity 3
    # Check row 2 (index 1)
    assert sheet.cell_value(1, 0) == 'SKU-A'
    assert sheet.cell_value(1, 1) == 3
