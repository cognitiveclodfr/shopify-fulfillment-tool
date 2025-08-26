import sys
import os
import pandas as pd
import xlwt

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


def test_full_run_with_file_io(tmp_path):
    """
    An integration-style test for the core module that uses the file system.
    """
    # 1. Setup temporary file structure
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    templates_dir = tmp_path / "templates"
    templates_dir.mkdir()

    # 2. Create mock input files
    stock_df = make_stock_df()
    stock_file = tmp_path / "stock.csv"
    stock_df.to_csv(stock_file, index=False, sep=';')

    orders_df = make_orders_df()
    orders_file = tmp_path / "orders.csv"
    orders_df.to_csv(orders_file, index=False)

    # Create a dummy template for the stock export
    dummy_template_path = templates_dir / "dummy_template.xls"
    # Create a valid, empty .xls file that xlrd can read
    workbook = xlwt.Workbook()
    workbook.add_sheet('Sheet1')
    workbook.save(dummy_template_path)


    # 3. Create a config dictionary pointing to our temp files
    config = {
        "settings": {"stock_csv_delimiter": ";", "low_stock_threshold": 4},
        "column_mappings": {
            "orders_required": ["Name", "Lineitem sku"],
            "stock_required": ["Артикул", "Наличност"]
        },
        "rules": [],
        "packing_lists": [
            {
                "name": "Test Packing List",
                "output_filename": "test_packing_list.xlsx",
                "filters": []
            }
        ],
        "stock_exports": [
            {
                "name": "Test Stock Export",
                "template": "dummy_template.xls",
                "filters": []
            }
        ]
    }

    # 4. Run the main analysis function
    success, analysis_path, final_df, stats = core.run_full_analysis(
        str(stock_file), str(orders_file), str(output_dir), ';', config
    )

    # 5. Assert main analysis results
    assert success
    assert os.path.exists(analysis_path)
    assert "fulfillment_analysis.xlsx" in analysis_path

    # 6. Run report generation functions
    # Packing List
    packing_report_config = config['packing_lists'][0]
    # IMPORTANT: core.py now expects the output_filename to be a full path
    # But settings window saves a relative path. The logic in gui_main combines them.
    # We must replicate that logic here for the test.
    packing_report_config['output_filename'] = str(output_dir / packing_report_config['output_filename'])

    pack_success, pack_msg = core.create_packing_list_report(final_df, packing_report_config)
    assert pack_success
    assert os.path.exists(packing_report_config['output_filename'])

    # Stock Export
    export_report_config = config['stock_exports'][0]
    export_success, export_msg = core.create_stock_export_report(
        final_df, export_report_config, str(templates_dir), str(output_dir)
    )
    assert export_success
    # The output filename is generated dynamically, so we need to find it
    output_files = os.listdir(output_dir)
    assert any("dummy_template" in f for f in output_files)
