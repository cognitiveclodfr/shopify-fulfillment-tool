import os
import xlrd
import logging
from xlutils.copy import copy

logger = logging.getLogger("ShopifyToolLogger")


def create_stock_export(analysis_df, template_file, output_file, report_name="Stock Export", filters=None):
    """
    Creates a stock export file by writing data into an existing .xls template file.
    """
    try:
        logger.info(f"--- Creating report: '{report_name}' ---")

        if not os.path.exists(template_file) or os.path.getsize(template_file) == 0:
            logger.error(f"Template file '{template_file}' not found or is empty.")
            return

        # Build the query string to filter the DataFrame
        query_parts = ["Order_Fulfillment_Status == 'Fulfillable'"]
        if filters:
            for f in filters:
                field = f.get("field")
                operator = f.get("operator")
                value = f.get("value")

                if not all([field, operator, value is not None]):
                    logger.warning(f"Skipping invalid filter: {f}")
                    continue

                # Correctly quote string values for the query
                if isinstance(value, str):
                    formatted_value = repr(value)
                else:
                    # For lists (for 'in'/'not in') and numbers, no extra quotes are needed.
                    formatted_value = value

                query_parts.append(f"`{field}` {operator} {formatted_value}")

        full_query = " & ".join(query_parts)
        filtered_items = analysis_df.query(full_query).copy()

        if filtered_items.empty:
            logger.warning(f"Report '{report_name}': No items found matching the criteria.")
            return

        # Summarize quantities by SKU
        sku_summary = filtered_items.groupby("SKU")["Quantity"].sum().astype(int).reset_index()
        sku_summary = sku_summary[sku_summary["Quantity"] > 0]

        if sku_summary.empty:
            logger.warning(f"Report '{report_name}': No items with a positive quantity to export.")
            return

        logger.info(f"Found {len(sku_summary)} unique SKUs to write for report '{report_name}'.")

        try:
            # Open the template file for reading
            rb = xlrd.open_workbook(template_file, formatting_info=True)
        except xlrd.biffh.XLRDError as e:
            logger.error(f"Cannot read template file '{template_file}'. The file may be corrupt. Details: {e}")
            return

        # Create a writable copy of the template
        wb = copy(rb)
        sheet_to_write = wb.get_sheet(0)

        # Write the summarized data into the sheet
        for index, row in sku_summary.iterrows():
            sheet_to_write.write(index + 1, 0, row["SKU"])
            sheet_to_write.write(index + 1, 1, row["Quantity"])
            sheet_to_write.write(index + 1, 2, "бройка")  # This is a specific required value.

        wb.save(output_file)
        logger.info(f"Stock export '{report_name}' created successfully.")

    except Exception as e:
        logger.error(f"Error while creating stock export '{report_name}': {e}")
