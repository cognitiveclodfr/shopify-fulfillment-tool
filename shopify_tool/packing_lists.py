import pandas as pd
import os
import logging
from datetime import datetime

logger = logging.getLogger('ShopifyToolLogger')

def create_packing_list(analysis_df, output_file, report_name="Packing List", filters=None, exclude_skus=None):
    """
    Creates a versatile packing list in .xlsx format with advanced formatting.
    """
    try:
        logger.info(f"--- Creating report: '{report_name}' ---")

        # Build the query string to filter the DataFrame
        query_parts = ["Order_Fulfillment_Status == 'Fulfillable'"]
        if filters: # In this version, filters is a LIST of objects
            for f in filters:
                field, op, value = f.get('field'), f.get('operator'), f.get('value')
                if not all([field, op, value is not None]):
                    logger.warning(f"Skipping invalid filter rule: {f}")
                    continue

                # Format value for query string, escaping quotes in strings
                if op in ['in', 'not in']:
                    value_formatted = f"{tuple(value)}"
                else:
                    if isinstance(value, str):
                        value_formatted = f"'{value.replace('\'', '\\\'')}'"
                    else:
                        value_formatted = value

                query_parts.append(f"`{field}` {op} {value_formatted}")

        full_query = " & ".join(query_parts)
        logger.info(f"Applying query: {full_query}")
        filtered_orders = analysis_df.query(full_query).copy()

        # Exclude specified SKUs if any are provided
        if exclude_skus and not filtered_orders.empty:
            logger.info(f"Excluding SKUs: {exclude_skus}")
            filtered_orders = filtered_orders[~filtered_orders['SKU'].isin(exclude_skus)]

        if filtered_orders.empty:
            logger.warning(f"Report '{report_name}': No orders found matching the criteria.")
            return

        logger.info(f"Found {filtered_orders['Order_Number'].nunique()} orders for the report.")

        # Fill NaN values to avoid issues during processing
        for col in ['Destination_Country', 'Product_Name', 'SKU']:
            filtered_orders[col] = filtered_orders[col].fillna('')

        # Sort the list for optimal packing order
        provider_map = {'DHL': 0, 'PostOne': 1, 'DPD': 2}
        filtered_orders['sort_priority'] = filtered_orders['Shipping_Provider'].map(provider_map).fillna(3)
        sorted_list = filtered_orders.sort_values(by=['sort_priority', 'Order_Number', 'SKU'])
        
        # Show destination country only for the first item of an order
        sorted_list['Destination_Country'] = sorted_list['Destination_Country'].where(~sorted_list['Order_Number'].duplicated(), '')

        # Define the columns for the final print list
        columns_for_print = ['Destination_Country', 'Order_Number', 'SKU', 'Product_Name', 'Quantity', 'Shipping_Provider']
        print_list = sorted_list[columns_for_print]

        generation_timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        output_filename = os.path.basename(output_file)
        
        # Rename columns to embed metadata into the header
        rename_map = {
            "Shipping_Provider": generation_timestamp,
            "Product_Name": output_filename
        }
        print_list = print_list.rename(columns=rename_map)
        
        logger.info("Creating Excel file...")
        with pd.ExcelWriter(output_file, engine='xlsxwriter') as writer:
            sheet_name = os.path.splitext(output_filename)[0]
            print_list.to_excel(writer, sheet_name=sheet_name, index=False)

            workbook = writer.book
            worksheet = writer.sheets[sheet_name]

            # --- Excel Formatting ---
            header_format = workbook.add_format({'bold': True, 'font_size': 10, 'align': 'center', 'valign': 'vcenter', 'border': 2, 'bg_color': '#F2F2F2'})
            
            for col_num, value in enumerate(print_list.columns):
                worksheet.write(0, col_num, value, header_format)

            # Define cell formats for different row positions (top, middle, bottom of an order)
            formats = {
                'top': {'top': 2, 'left': 1, 'right': 1, 'bottom': 1, 'bottom_color': '#DCDCDC'},
                'middle': {'left': 1, 'right': 1, 'bottom': 1, 'bottom_color': '#DCDCDC'},
                'bottom': {'bottom': 2, 'left': 1, 'right': 1},
                'full': {'border': 2}
            }
            cell_formats = {}
            for key, base_props in formats.items():
                props_default = {**base_props, 'valign': 'vcenter'}
                cell_formats[key] = workbook.add_format(props_default)
                props_centered = {**props_default, 'align': 'center'}
                cell_formats[key + '_centered'] = workbook.add_format(props_centered)

            # Apply borders to group items by order number
            order_boundaries = print_list['Order_Number'].ne(print_list['Order_Number'].shift()).cumsum()
            for row_num in range(len(print_list)):
                is_top = (row_num == 0) or (order_boundaries.iloc[row_num] != order_boundaries.iloc[row_num - 1])
                is_bottom = (row_num == len(print_list) - 1) or (order_boundaries.iloc[row_num] != order_boundaries.iloc[row_num + 1])
                
                row_type = 'full' if is_top and is_bottom else 'top' if is_top else 'bottom' if is_bottom else 'middle'

                for col_num, col_name in enumerate(print_list.columns):
                    original_col_name = columns_for_print[col_num]
                    fmt_key = row_type + '_centered' if original_col_name in ['Destination_Country', 'Quantity'] else row_type
                    worksheet.write(row_num + 1, col_num, print_list.iloc[row_num, col_num], cell_formats[fmt_key])

            # Auto-adjust column widths
            for i, col in enumerate(print_list.columns):
                max_len = max(print_list[col].astype(str).map(len).max(), len(col)) + 2
                original_col_name = columns_for_print[i]
                if original_col_name == 'Destination_Country': max_len = 5
                elif original_col_name == 'Product_Name': max_len = min(max_len, 45)
                elif original_col_name == 'SKU': max_len = min(max_len, 25)
                worksheet.set_column(i, i, max_len)

            # Set print settings
            worksheet.set_paper(9)  # A4 paper
            worksheet.set_landscape()
            worksheet.repeat_rows(0)  # Repeat header row
            worksheet.fit_to_pages(1, 0)  # Fit to 1 page wide

        logger.info(f"Report '{report_name}' created successfully.")

    except Exception as e:
        logger.error(f"ERROR while creating packing list: {e}")
