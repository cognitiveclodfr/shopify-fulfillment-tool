import pandas as pd
import os
import xlrd
from xlutils.copy import copy

def create_stock_export(analysis_df, template_file, output_file, report_name="Stock Export", filters=None):
    try:
        print(f"\n--- Creating report: '{report_name}' ---")

        if not os.path.exists(template_file) or os.path.getsize(template_file) == 0:
            print(f"ERROR: Template file '{template_file}' not found or is empty.")
            return

        query_parts = ["Order_Fulfillment_Status == 'Fulfillable'"]
        if filters:
            for key, value in filters.items():
                query_parts.append(f"`{key}` in {value}" if isinstance(value, list) else f"`{key}` == '{value}'")
        
        full_query = " & ".join(query_parts)
        filtered_items = analysis_df.query(full_query).copy()

        if filtered_items.empty:
            print("Result: No items found matching the criteria.")
            return

        sku_summary = filtered_items.groupby('SKU')['Quantity'].sum().astype(int).reset_index()
        sku_summary = sku_summary[sku_summary['Quantity'] > 0]
        
        if sku_summary.empty:
            print("Result: No items with a positive quantity to export.")
            return
            
        print(f"Found {len(sku_summary)} unique SKUs to write.")

        try:
            rb = xlrd.open_workbook(template_file, formatting_info=True)
        except xlrd.biffh.XLRDError as e:
            print(f"ERROR: Cannot read template file '{template_file}'. The file may be corrupt.")
            print(f"   Details: {e}")
            return

        wb = copy(rb)
        sheet_to_write = wb.get_sheet(0)

        for index, row in sku_summary.iterrows():
            sheet_to_write.write(index + 1, 0, row['SKU'])
            sheet_to_write.write(index + 1, 1, row['Quantity'])
            sheet_to_write.write(index + 1, 2, 'бройка') # This seems to be a specific identifier, left as is.
            
        wb.save(output_file)
        print(f"Result: Success! File created: '{output_file}'")

    except Exception as e:
        print(f"ERROR while creating stock export: {e}")
