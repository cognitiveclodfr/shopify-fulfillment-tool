"""Stock Export Generator - Courier-Specific Inventory Allocation Files.

This module generates stock export files that inform couriers (DHL, DPD, PostOne)
about which products and quantities have been allocated for their shipments.
These files are typically imported into courier systems or warehouse management
software.

Purpose:
    After fulfillment analysis determines which orders can be shipped, this
    module creates per-courier inventory lists showing exactly which SKUs and
    quantities are being sent with that courier. This helps with:
    - Courier capacity planning
    - Warehouse pre-picking
    - Integration with courier pickup systems
    - Stock reconciliation

File Format:
    Exports are generated in legacy Excel format (.xls) for compatibility with
    older warehouse systems. The format is minimal:
    - Column 1: Артикул (SKU) - Product identifier
    - Column 2: Наличност (Stock) - Quantity allocated

    Note: Column names are in Bulgarian/Cyrillic to match courier system
          expectations. This is intentional for this specific use case.

Algorithm:
    1. Filter analysis DataFrame by provided criteria (e.g., Shipping_Provider == "DHL")
    2. Group filtered items by SKU, summing quantities
    3. Create simple two-column DataFrame
    4. Export to .xls format

Key Differences from Packing Lists:
    - Packing lists: Order-centric (for warehouse pickers)
    - Stock exports: SKU-centric (for courier/system integration)

    Packing List: Order #123 needs SKU-A×2, SKU-B×1
    Stock Export: SKU-A: 50 total, SKU-B: 30 total (across all orders)

Performance:
    - Very fast (aggregation is O(n) where n = number of items)
    - Typical generation time: <0.5 seconds for 1000+ items
    - .xls format slightly slower than .xlsx but more compatible

Filtering Example:
    >>> # Export only DHL stock
    >>> create_stock_export(
    ...     analysis_df,
    ...     "output/DHL_stock_2024-01-15.xls",
    ...     report_name="DHL Stock Export",
    ...     filters=[{"field": "Shipping_Provider", "operator": "==", "value": "DHL"}]
    ... )

    Result: DHL_stock_2024-01-15.xls with:
    Артикул    | Наличност
    -----------|----------
    SKU-001    | 25
    SKU-002    | 12
    SKU-003    | 8

Implementation Notes:
    - Uses xlwt engine for .xls (legacy Excel format)
    - Handles edge case where xlwt engine not registered in pandas
    - Creates empty file with headers if no matching items
    - Filters out SKUs with zero or negative quantities

Integration Points:
    - Called by core.create_stock_export_report()
    - Configured via settings_window_pyside.py (Stock Exports tab)
    - Filters defined in config['stock_exports'] list

Related:
    - packing_lists.py: Order-level reports for warehouse picking
    - core.py: Report orchestration
    - settings_window_pyside.py: Stock export template configuration
"""

import logging
import pandas as pd

logger = logging.getLogger("ShopifyToolLogger")


def create_stock_export(analysis_df, output_file, report_name="Stock Export", filters=None):
    """Creates a stock export .xls file from scratch.

    This function generates a stock export file programmatically using pandas,
    eliminating the need for a physical template file. The structure is
    hard-coded to ensure consistency.

    Key steps in the process:
    1.  **Filtering**: It filters the main analysis DataFrame to include only
        'Fulfillable' orders that match the provided filter criteria.
    2.  **Summarization**: It summarizes the filtered data, calculating the total
        quantity for each unique SKU.
    3.  **DataFrame Creation**: It creates a new DataFrame with the required
        columns: 'Артикул' (for SKU) and 'Наличност' (for quantity).
    4.  **Saving**: The new DataFrame is saved to the specified .xls output file.

    Args:
        analysis_df (pd.DataFrame): The main DataFrame from the fulfillment
            analysis.
        output_file (str): The full path where the new .xls file will be saved.
        report_name (str, optional): The name of the report, used for logging.
            Defaults to "Stock Export".
        filters (list[dict], optional): A list of dictionaries defining filter
            conditions to apply before summarizing the data. Defaults to None.
    """
    try:
        logger.info(f"--- Creating report: '{report_name}' ---")

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
            # Still create an empty file with headers
            export_df = pd.DataFrame(columns=["Артикул", "Наличност"])
        else:
            # Summarize quantities by SKU
            sku_summary = filtered_items.groupby("SKU")["Quantity"].sum().astype(int).reset_index()
            sku_summary = sku_summary[sku_summary["Quantity"] > 0]

            if sku_summary.empty:
                logger.warning(f"Report '{report_name}': No items with a positive quantity to export.")
                export_df = pd.DataFrame(columns=["Артикул", "Наличност"])
            else:
                logger.info(f"Found {len(sku_summary)} unique SKUs to write for report '{report_name}'.")
                # Create the final DataFrame in the required format
                export_df = pd.DataFrame(
                    {
                        "Артикул": sku_summary["SKU"],
                        "Наличност": sku_summary["Quantity"],
                    }
                )

        # Save to an .xls file
        try:
            with pd.ExcelWriter(output_file, engine="xlwt") as writer:
                export_df.to_excel(writer, index=False, sheet_name="Sheet1")
            logger.info(f"Stock export '{report_name}' created successfully at '{output_file}'.")
        except Exception as e:
            # Fallback for environments where xlwt might not be properly registered
            if "No Excel writer 'xlwt'" in str(e):
                logger.warning("Pandas failed to find 'xlwt' engine. Trying direct save with xlwt.")
                import xlwt
                workbook = xlwt.Workbook()
                sheet = workbook.add_sheet('Sheet1')

                # Write header
                for col_num, value in enumerate(export_df.columns):
                    sheet.write(0, col_num, value)

                # Write data
                for row_num, row in export_df.iterrows():
                    for col_num, value in enumerate(row):
                        sheet.write(row_num + 1, col_num, value)

                workbook.save(output_file)
                logger.info(
                    f"Stock export '{report_name}' created successfully at '{output_file}' using direct xlwt save."
                )
            else:
                raise e

    except Exception as e:
        logger.error(f"Error while creating stock export '{report_name}': {e}")
