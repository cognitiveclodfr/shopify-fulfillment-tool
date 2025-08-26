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


import xlwt
import xlrd

def test_create_stock_export_success_path(tmp_path):
    """
    Tests the successful creation and content of a stock export file.
    """
    # 1. Create a sample analysis DataFrame
    analysis_df = pd.DataFrame({
        'Order_Fulfillment_Status': ['Fulfillable', 'Fulfillable', 'Fulfillable', 'Not Fulfillable'],
        'SKU':                      ['SKU-A', 'SKU-B', 'SKU-A', 'SKU-C'],
        'Quantity':                 [5,       3,       2,       10],
    })

    # 2. Create a valid .xls template file
    template_path = tmp_path / "template.xls"
    workbook = xlwt.Workbook()
    sheet = workbook.add_sheet('Sheet1')
    # Add some dummy header to ensure it's being read
    sheet.write(0, 0, 'SKU')
    sheet.write(0, 1, 'Quantity')
    sheet.write(0, 2, 'Unit')
    workbook.save(template_path)

    # 3. Define output path and call the function
    output_path = tmp_path / "stock_export_out.xls"
    stock_export.create_stock_export(analysis_df, str(template_path), str(output_path))

    # 4. Assertions
    assert os.path.exists(output_path)

    # 5. Read the output and validate its content
    book = xlrd.open_workbook(output_path)
    sheet = book.sheet_by_index(0)

    # Data should start from the second row (index 1)
    # Expected data: SKU-A: 5+2=7, SKU-B: 3. SKU-C is not fulfillable.
    # The order might not be guaranteed, so we check the content.

    # Row 1
    row1_sku = sheet.cell_value(1, 0)
    row1_qty = sheet.cell_value(1, 1)
    row1_unit = sheet.cell_value(1, 2)

    # Row 2
    row2_sku = sheet.cell_value(2, 0)
    row2_qty = sheet.cell_value(2, 1)

    # Create a dictionary from the results for easier assertion
    results = {
        row1_sku: row1_qty,
        row2_sku: row2_qty
    }

    assert len(results) == 2
    assert results['SKU-A'] == 7
    assert results['SKU-B'] == 3
    assert row1_unit == 'бройка' # Check the static value
