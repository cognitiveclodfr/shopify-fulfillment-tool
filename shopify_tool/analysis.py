import pandas as pd
import numpy as np
import os
from datetime import datetime

def _generalize_shipping_method(method):
    """
    Standardizes shipping method names.
    """
    if pd.isna(method):
        return 'Unknown'
    method = str(method).lower()
    if 'dhl' in method:
        return 'DHL'
    if 'dpd' in method:
        return 'DPD'
    if 'international shipping' in method:
        return 'PostOne'
    return method.title()

def run_analysis(stock_file_path, orders_file_path, output_file_path, stock_delimiter=';'):
    """
    Performs a full analysis, creating a report with 4 sheets and history tracking.
    """
    try:
        print("Step 1: Loading and preparing data...")
        if not os.path.exists(stock_file_path) or not os.path.exists(orders_file_path):
            print("ERROR: One or both input files were not found.")
            return
        stock_df = pd.read_csv(stock_file_path, delimiter=stock_delimiter)
        orders_df = pd.read_csv(orders_file_path)
        print("Data loaded successfully.")
        
        # ⭐ NEW: Load fulfillment history
        history_path = 'fulfillment_history.csv'
        try:
            history_df = pd.read_csv(history_path)
            print(f"Loaded {len(history_df)} records from fulfillment history.")
        except FileNotFoundError:
            history_df = pd.DataFrame(columns=['Order_Number', 'Execution_Date'])
            print("Fulfillment history not found. A new one will be created.")

        # --- Data Cleaning ---
        orders_df['Name'] = orders_df['Name'].ffill()
        orders_df['Shipping Method'] = orders_df['Shipping Method'].ffill()
        orders_df['Shipping Country'] = orders_df['Shipping Country'].ffill()
        
        columns_to_keep = ['Name', 'Lineitem sku', 'Lineitem quantity', 'Shipping Method', 'Shipping Country', 'Tags', 'Notes']
        orders_clean_df = orders_df[columns_to_keep].copy()
        orders_clean_df.rename(columns={'Name': 'Order_Number', 'Lineitem sku': 'SKU', 'Lineitem quantity': 'Quantity'}, inplace=True)
        orders_clean_df.dropna(subset=['SKU'], inplace=True)

        stock_clean_df = stock_df[['Артикул', 'Име', 'Наличност']].copy()
        stock_clean_df.rename(columns={'Артикул': 'SKU', 'Име': 'Product_Name', 'Наличност': 'Stock'}, inplace=True)
        stock_clean_df.dropna(subset=['SKU'], inplace=True)
        stock_clean_df.drop_duplicates(subset=['SKU'], keep='first', inplace=True)
        
        # --- Simulation ---
        print("Step 2: Simulating order fulfillment...")
        order_item_counts = orders_clean_df.groupby('Order_Number').size().rename('item_count')
        orders_with_counts = pd.merge(orders_clean_df, order_item_counts, on='Order_Number')
        prioritized_orders = orders_with_counts[['Order_Number', 'item_count']].drop_duplicates().sort_values(by=['item_count', 'Order_Number'], ascending=[False, True])
        live_stock = pd.Series(stock_clean_df.Stock.values, index=stock_clean_df.SKU).to_dict()
        fulfillment_results = {}
        for order_number in prioritized_orders['Order_Number']:
            order_items = orders_with_counts[orders_with_counts['Order_Number'] == order_number]
            can_fulfill_order = True
            for _, item in order_items.iterrows():
                sku, required_qty = item['SKU'], item['Quantity']
                if required_qty > live_stock.get(sku, 0):
                    can_fulfill_order = False
                    break
            if can_fulfill_order:
                fulfillment_results[order_number] = 'Fulfillable'
                for _, item in order_items.iterrows():
                    live_stock[item['SKU']] -= item['Quantity']
            else:
                fulfillment_results[order_number] = 'Not Fulfillable'

        # --- Main Report Generation ---
        print("Step 3: Generating the main report...")
        final_df = pd.merge(orders_clean_df, stock_clean_df, on='SKU', how='left')
        final_df = pd.merge(final_df, order_item_counts, on='Order_Number')
        final_df['Order_Type'] = np.where(final_df['item_count'] > 1, 'Multi', 'Single')
        final_df['Stock'].fillna(0, inplace=True)
        final_df['Shipping_Provider'] = final_df['Shipping Method'].apply(_generalize_shipping_method)
        final_df['Order_Fulfillment_Status'] = final_df['Order_Number'].map(fulfillment_results)
        final_df['Destination_Country'] = np.where(final_df['Shipping_Provider'] == 'DHL', final_df['Shipping Country'], '')
        
        # ⭐ NEW: Add Status_Note for repeat orders
        final_df['Status_Note'] = np.where(final_df['Order_Number'].isin(history_df['Order_Number']), 'Repeat', '')
        
        output_columns = ['Order_Number', 'Order_Type', 'SKU', 'Product_Name', 'Quantity', 'Stock', 'Order_Fulfillment_Status', 'Shipping_Provider', 'Destination_Country', 'Shipping Method', 'Tags', 'Notes', 'Status_Note']
        final_df = final_df[output_columns]

        # --- Generating Summary Reports ---
        print("Step 4: Generating summary reports...")
        present_df = final_df[final_df['Order_Fulfillment_Status'] == 'Fulfillable'].copy()
        summary_present_df = present_df.groupby(['SKU', 'Product_Name'], as_index=False)['Quantity'].sum()
        summary_present_df.rename(columns={'Product_Name': 'Name', 'Quantity': 'Total Quantity'}, inplace=True)
        summary_present_df = summary_present_df[['Name', 'SKU', 'Total Quantity']]

        missing_df = final_df[final_df['Order_Fulfillment_Status'] == 'Not Fulfillable'].copy()
        missing_df['Product_Name'].fillna('N/A', inplace=True)
        summary_missing_df = missing_df.groupby(['SKU', 'Product_Name'], as_index=False)['Quantity'].sum()
        summary_missing_df.rename(columns={'Product_Name': 'Name', 'Quantity': 'Total Quantity'}, inplace=True)
        summary_missing_df = summary_missing_df[['Name', 'SKU', 'Total Quantity']]

        # --- Writing all sheets to one file ---
        print("Step 5: Saving the report to Excel...")
        with pd.ExcelWriter(output_file_path, engine='xlsxwriter') as writer:
            final_df.to_excel(writer, sheet_name='fulfillment_analysis', index=False)
            summary_present_df.to_excel(writer, sheet_name='Summary_Present', index=False)
            summary_missing_df.to_excel(writer, sheet_name='Summary_Missing', index=False)
            
            workbook = writer.book
            report_info_sheet = workbook.add_worksheet('Report Info')
            generation_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            report_info_sheet.write('A1', 'Report Generated On:')
            report_info_sheet.write('B1', generation_time)
            report_info_sheet.set_column('A:B', 25)

            worksheet = writer.sheets['fulfillment_analysis']
            highlight_format = workbook.add_format({'bg_color': '#FFC7CE', 'font_color': '#9C0006'})
            for idx, col in enumerate(final_df):
                max_len = max((final_df[col].astype(str).map(len).max(), len(str(col)))) + 2
                worksheet.set_column(idx, idx, max_len)
            for row_num, status in enumerate(final_df['Order_Fulfillment_Status']):
                if status == 'Not Fulfillable':
                    worksheet.set_row(row_num + 1, None, highlight_format)
        
        print(f"Step 6: Done! Analysis file saved to '{output_file_path}'")
        
        # ⭐ NEW: Update fulfillment history
        newly_fulfilled = final_df[final_df['Order_Fulfillment_Status'] == 'Fulfillable'][['Order_Number']].drop_duplicates()
        if not newly_fulfilled.empty:
            newly_fulfilled['Execution_Date'] = datetime.now().strftime("%Y-%m-%d")
            updated_history = pd.concat([history_df, newly_fulfilled]).drop_duplicates(subset=['Order_Number'], keep='last')
            updated_history.to_csv(history_path, index=False)
            print(f"Updated fulfillment history with {len(newly_fulfilled)} new records.")

    except Exception as e:
        print(f"An unexpected error occurred during analysis: {e}")
