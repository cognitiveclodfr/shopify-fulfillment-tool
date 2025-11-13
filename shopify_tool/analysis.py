import pandas as pd
import numpy as np


def _generalize_shipping_method(method):
    """Standardizes raw shipping method names to a consistent format.

    Takes a raw shipping method string, converts it to lowercase, and maps it
    to a standardized provider name (e.g., 'dhl express' becomes 'DHL').
    If the method is not recognized, it returns a title-cased version of the
    input. Handles NaN values by returning 'Unknown'.

    Args:
        method (str | float): The raw shipping method from the orders file.
            Can be a float (NaN) for empty values.

    Returns:
        str: The standardized shipping provider name.
    """
    if pd.isna(method):
        return "Unknown"
    method = str(method).lower()
    if not method:
        return "Unknown"
    if "dhl" in method:
        return "DHL"
    if "dpd" in method:
        return "DPD"
    if "international shipping" in method:
        return "PostOne"
    return method.title()


def run_analysis(stock_df, orders_df, history_df, column_mappings=None):
    """Performs the core fulfillment analysis and simulation.

    This function is the heart of the fulfillment logic. It takes raw data,
    cleans it, and simulates the stock allocation process.

    The process includes:
    1.  Applying column mappings to standardize column names from various sources
    2.  Cleaning and standardizing columns in orders and stock DataFrames.
    3.  Prioritizing orders for fulfillment, typically processing multi-item
        orders first to maximize the number of complete orders shipped.
    4.  Iterating through prioritized orders, checking stock availability, and
        allocating stock for fulfillable orders.
    5.  Calculating the final stock levels after the simulation.
    6.  Enriching the data with additional information like shipping provider,
        order type (Single/Multi), and repeat order status.
    7.  Generating summary reports for fulfilled and missing items.
    8.  Calculating final statistics.

    This function operates purely on DataFrames and does not perform any
    file I/O.

    Args:
        stock_df (pd.DataFrame): DataFrame with stock levels for each SKU.
            Column names will be mapped according to column_mappings['stock'].
        orders_df (pd.DataFrame): DataFrame with all order line items.
            Column names will be mapped according to column_mappings['orders'].
        history_df (pd.DataFrame): DataFrame with previously fulfilled order
            numbers. Requires an 'Order_Number' column.
        column_mappings (dict, optional): Dictionary with 'orders' and 'stock' keys,
            each containing a mapping of CSV column names to internal standard names.
            Example: {"orders": {"Name": "Order_Number", "Lineitem sku": "SKU"},
                     "stock": {"Артикул": "SKU", "Наличност": "Stock"}}
            If None, uses default Shopify/Bulgarian mappings for backward compatibility.

    Returns:
        tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, dict]:
            A tuple containing four elements:
            - final_df (pd.DataFrame): The main DataFrame with detailed results
              for every line item, including the calculated
              'Order_Fulfillment_Status'.
            - summary_present_df (pd.DataFrame): A summary of all SKUs that
              will be fulfilled, aggregated by quantity.
            - summary_missing_df (pd.DataFrame): A summary of SKUs in
              unfulfillable orders that were out of stock.
            - stats (dict): A dictionary containing key statistics about the
              fulfillment analysis (e.g., total orders completed).
    """
    # --- Step 0: Apply Column Mappings ---
    # Check if DataFrames already have internal names (backward compatibility for tests)
    orders_has_internal_names = all(
        col in orders_df.columns for col in ["Order_Number", "SKU", "Quantity"]
    )
    stock_has_internal_names = all(
        col in stock_df.columns for col in ["SKU", "Stock"]
    )

    # If DataFrames already have internal names, skip mapping
    if orders_has_internal_names and stock_has_internal_names and column_mappings is None:
        # Already using internal names (e.g., in tests), no mapping needed
        pass
    else:
        # Apply column mappings
        # Default mappings for backward compatibility (Shopify + Bulgarian warehouse)
        if column_mappings is None:
            column_mappings = {
                "orders": {
                    "Name": "Order_Number",
                    "Lineitem sku": "SKU",
                    "Lineitem quantity": "Quantity",
                    "Lineitem name": "Product_Name",
                    "Shipping Method": "Shipping_Method",
                    "Shipping Country": "Shipping_Country",
                    "Tags": "Tags",
                    "Notes": "Notes",
                    "Total": "Total_Price"
                },
                "stock": {
                    "Артикул": "SKU",
                    "Име": "Product_Name",
                    "Наличност": "Stock"
                }
            }

        # Get mappings for orders and stock
        orders_mappings = column_mappings.get("orders", {})
        stock_mappings = column_mappings.get("stock", {})

        # Apply mappings to orders DataFrame
        # Only rename columns that exist in the DataFrame AND are different from internal names
        orders_rename_map = {csv_col: internal_col for csv_col, internal_col in orders_mappings.items()
                             if csv_col in orders_df.columns and csv_col != internal_col}
        if orders_rename_map:
            orders_df = orders_df.rename(columns=orders_rename_map)

        # Apply mappings to stock DataFrame
        stock_rename_map = {csv_col: internal_col for csv_col, internal_col in stock_mappings.items()
                            if csv_col in stock_df.columns and csv_col != internal_col}
        if stock_rename_map:
            stock_df = stock_df.rename(columns=stock_rename_map)

    # --- Step 1: Data Cleaning (now using internal standard names) ---
    # Forward-fill order-level columns
    if "Order_Number" in orders_df.columns:
        orders_df["Order_Number"] = orders_df["Order_Number"].ffill()
    if "Shipping_Method" in orders_df.columns:
        orders_df["Shipping_Method"] = orders_df["Shipping_Method"].ffill()
    if "Shipping_Country" in orders_df.columns:
        orders_df["Shipping_Country"] = orders_df["Shipping_Country"].ffill()
    if "Total_Price" in orders_df.columns:
        orders_df["Total_Price"] = orders_df["Total_Price"].ffill()

    # Keep only relevant columns (internal names)
    columns_to_keep = [
        "Order_Number",
        "SKU",
        "Quantity",
        "Shipping_Method",
        "Shipping_Country",
        "Product_Name",
        "Tags",
        "Notes",
        "Total_Price",
    ]
    # Filter for existing columns only
    columns_to_keep_existing = [col for col in columns_to_keep if col in orders_df.columns]
    orders_clean_df = orders_df[columns_to_keep_existing].copy()
    orders_clean_df = orders_clean_df.dropna(subset=["SKU"])

    # CRITICAL: Normalize SKU to standard format for consistent merging
    # This handles float artifacts (5170.0 → "5170"), whitespace, and leading zeros
    from .csv_utils import normalize_sku
    orders_clean_df["SKU"] = orders_clean_df["SKU"].apply(normalize_sku)

    # Clean stock DataFrame (internal names)
    required_stock_cols = ["SKU", "Stock"]
    stock_cols_to_keep = [col for col in ["SKU", "Product_Name", "Stock"] if col in stock_df.columns]

    # Verify required columns exist
    missing_stock_cols = [col for col in required_stock_cols if col not in stock_df.columns]
    if missing_stock_cols:
        raise ValueError(f"Missing required columns in stock DataFrame after mapping: {missing_stock_cols}")

    stock_clean_df = stock_df[stock_cols_to_keep].copy()
    stock_clean_df = stock_clean_df.dropna(subset=["SKU"])
    stock_clean_df = stock_clean_df.drop_duplicates(subset=["SKU"], keep="first")

    # CRITICAL: Normalize SKU to standard format for consistent merging
    # This handles float artifacts (5170.0 → "5170"), whitespace, and leading zeros
    stock_clean_df["SKU"] = stock_clean_df["SKU"].apply(normalize_sku)

    # --- Set/Bundle Decoding ---
    # Expand sets into component SKUs before fulfillment simulation
    from .set_decoder import decode_sets_in_orders
    import logging
    logger = logging.getLogger(__name__)

    set_decoders = column_mappings.get("set_decoders", {}) if column_mappings else {}
    if set_decoders:
        logger.info(f"Decoding sets: {len(set_decoders)} definitions")
        orders_clean_df = decode_sets_in_orders(orders_clean_df, set_decoders)
        logger.info(f"Orders after expansion: {len(orders_clean_df)} rows")
    else:
        # No sets defined - add tracking columns anyway for consistency
        orders_clean_df["Original_SKU"] = orders_clean_df["SKU"]
        orders_clean_df["Original_Quantity"] = orders_clean_df["Quantity"]
        orders_clean_df["Is_Set_Component"] = False

    # --- Fulfillment Simulation ---
    order_item_counts = orders_clean_df.groupby("Order_Number").size().rename("item_count")
    orders_with_counts = pd.merge(orders_clean_df, order_item_counts, on="Order_Number")
    prioritized_orders = (
        orders_with_counts[["Order_Number", "item_count"]]
        .drop_duplicates()
        .sort_values(by=["item_count", "Order_Number"], ascending=[False, True])
    )

    live_stock = pd.Series(stock_clean_df.Stock.values, index=stock_clean_df.SKU).to_dict()
    fulfillment_results = {}

    for order_number in prioritized_orders["Order_Number"]:
        order_items = orders_with_counts[orders_with_counts["Order_Number"] == order_number]
        can_fulfill_order = True
        # Перевіряємо, чи можна виконати замовлення
        for _, item in order_items.iterrows():
            sku, required_qty = item["SKU"], item["Quantity"]
            if required_qty > live_stock.get(sku, 0):
                can_fulfill_order = False
                break
        # Якщо так, списуємо товари
        if can_fulfill_order:
            fulfillment_results[order_number] = "Fulfillable"
            for _, item in order_items.iterrows():
                live_stock[item["SKU"]] -= item["Quantity"]
        else:
            fulfillment_results[order_number] = "Not Fulfillable"

    # Calculate final stock levels after fulfillment
    final_stock_levels = pd.Series(live_stock, name="Final_Stock").reset_index().rename(columns={"index": "SKU"})

    # --- Final Report Generation ---
    # Merge orders with stock data
    # If both have Product_Name, prefer the one from orders (use suffixes to handle conflict)
    has_product_name_in_orders = "Product_Name" in orders_clean_df.columns
    has_product_name_in_stock = "Product_Name" in stock_clean_df.columns

    if has_product_name_in_orders and has_product_name_in_stock:
        # Both have Product_Name - use suffixes and prefer orders
        final_df = pd.merge(orders_clean_df, stock_clean_df, on="SKU", how="left", suffixes=('', '_stock'))
        # Drop stock Product_Name, keep orders Product_Name
        if 'Product_Name_stock' in final_df.columns:
            final_df = final_df.drop(columns=['Product_Name_stock'])
    else:
        # Simple merge - no conflict
        final_df = pd.merge(orders_clean_df, stock_clean_df, on="SKU", how="left")

    # --- Add Warehouse_Name column from stock file ---
    # Create stock name lookup dictionary
    if "Product_Name" in stock_clean_df.columns:
        stock_lookup = dict(zip(
            stock_clean_df["SKU"],
            stock_clean_df["Product_Name"]
        ))

        logger.info(f"Creating Warehouse_Name lookup: {len(stock_lookup)} SKUs")

        # Add Warehouse_Name column by mapping SKU
        final_df["Warehouse_Name"] = final_df["SKU"].map(stock_lookup)

        # Fill N/A for SKUs not found in stock
        final_df["Warehouse_Name"] = final_df["Warehouse_Name"].fillna("N/A")

        # Log statistics
        matched = (final_df["Warehouse_Name"] != "N/A").sum()
        total = len(final_df)
        logger.info(f"Warehouse names: {matched}/{total} SKUs matched")
    else:
        # No Product_Name in stock file
        logger.warning("Stock file has no Product_Name column, using N/A")
        final_df["Warehouse_Name"] = "N/A"

    final_df = pd.merge(final_df, order_item_counts, on="Order_Number")
    # Merge final stock levels to the main dataframe
    final_df = pd.merge(final_df, final_stock_levels, on="SKU", how="left")
    final_df["Final_Stock"] = final_df["Final_Stock"].fillna(
        final_df["Stock"]
    )  # If an item was not fulfilled, its final stock is its initial stock
    final_df["Order_Type"] = np.where(final_df["item_count"] > 1, "Multi", "Single")
    final_df["Stock"] = final_df["Stock"].fillna(0)
    # Use Shipping_Method with underscore (internal name)
    if "Shipping_Method" in final_df.columns:
        final_df["Shipping_Provider"] = final_df["Shipping_Method"].apply(_generalize_shipping_method)
    else:
        final_df["Shipping_Provider"] = "Unknown"
    final_df["Order_Fulfillment_Status"] = final_df["Order_Number"].map(fulfillment_results)
    # Use Shipping_Country with underscore (internal name)
    if "Shipping_Country" in final_df.columns:
        final_df["Destination_Country"] = np.where(final_df["Shipping_Provider"] == "DHL", final_df["Shipping_Country"], "")
    else:
        final_df["Destination_Country"] = ""
    final_df["System_note"] = np.where(final_df["Order_Number"].isin(history_df["Order_Number"]), "Repeat", "")
    final_df["Stock_Alert"] = ""  # Initialize the column
    final_df["Status_Note"] = ""  # Initialize column for user-defined rule tags

    # Initialize Source column (all orders start as "Order")
    final_df["Source"] = "Order"

    output_columns = [
        "Order_Number",
        "Order_Type",
        "SKU",
        "Product_Name",
        "Warehouse_Name",  # NEW: From stock file
        "Quantity",
        "Stock",
        "Final_Stock",
        "Source",  # NEW: "Order" or "Manual"
        "Stock_Alert",
        "Order_Fulfillment_Status",
        "Shipping_Provider",
        "Destination_Country",
        "Shipping_Method",
        "Tags",
        "Notes",
        "System_note",
        "Status_Note",
    ]
    if "Total_Price" in final_df.columns:
        # Insert 'Total_Price' into the list at a specific position for consistent column order.
        # Placed after 'Quantity'.
        output_columns.insert(6, "Total_Price")

    # Filter the list to include only columns that actually exist in the DataFrame.
    # This prevents errors if a column is unexpectedly missing.
    final_output_columns = [col for col in output_columns if col in final_df.columns]
    final_df = final_df[final_output_columns].copy()  # Use .copy() to avoid SettingWithCopyWarning

    # --- Summary Reports Generation ---
    present_df = final_df[final_df["Order_Fulfillment_Status"] == "Fulfillable"].copy()

    # Group by SKU and Product_Name if available, otherwise just SKU
    if "Product_Name" in present_df.columns:
        summary_present_df = present_df.groupby(["SKU", "Product_Name"], as_index=False)["Quantity"].sum()
        summary_present_df = summary_present_df.rename(columns={"Product_Name": "Name", "Quantity": "Total Quantity"})
        summary_present_df = summary_present_df[["Name", "SKU", "Total Quantity"]]
    else:
        summary_present_df = present_df.groupby(["SKU"], as_index=False)["Quantity"].sum()
        summary_present_df["Name"] = "N/A"
        summary_present_df = summary_present_df.rename(columns={"Quantity": "Total Quantity"})
        summary_present_df = summary_present_df[["Name", "SKU", "Total Quantity"]]

    # --- New logic for Summary_Missing ---
    # 1. Get all items from orders that could not be fulfilled.
    not_fulfilled_df = final_df[final_df["Order_Fulfillment_Status"] == "Not Fulfillable"].copy()

    # 2. Identify items that are "truly missing" by comparing required quantity vs initial stock.
    truly_missing_df = not_fulfilled_df[not_fulfilled_df["Quantity"] > not_fulfilled_df["Stock"]].copy()

    # 3. Create the summary report from this filtered data.
    if not truly_missing_df.empty:
        # Handle Product_Name if available, otherwise use N/A
        if "Product_Name" in truly_missing_df.columns:
            truly_missing_df["Product_Name"] = truly_missing_df["Product_Name"].fillna("N/A")
            summary_missing_df = truly_missing_df.groupby(["SKU", "Product_Name"], as_index=False)["Quantity"].sum()
            summary_missing_df = summary_missing_df.rename(columns={"Product_Name": "Name", "Quantity": "Total Quantity"})
            summary_missing_df = summary_missing_df[["Name", "SKU", "Total Quantity"]]
        else:
            summary_missing_df = truly_missing_df.groupby(["SKU"], as_index=False)["Quantity"].sum()
            summary_missing_df["Name"] = "N/A"
            summary_missing_df = summary_missing_df.rename(columns={"Quantity": "Total Quantity"})
            summary_missing_df = summary_missing_df[["Name", "SKU", "Total Quantity"]]
    else:
        summary_missing_df = pd.DataFrame(columns=["Name", "SKU", "Total Quantity"])

    # --- Statistics Calculation ---
    stats = recalculate_statistics(final_df)

    return final_df, summary_present_df, summary_missing_df, stats


def recalculate_statistics(df):
    """Calculates statistics based on the provided analysis DataFrame.

    Aggregates data from the main analysis DataFrame to produce a summary
    of key metrics, such as the number of completed orders, total items,
    and a breakdown of orders per shipping courier.

    Args:
        df (pd.DataFrame): The main analysis DataFrame, which must contain
            'Order_Fulfillment_Status', 'Order_Number', 'Quantity',
            'Shipping_Provider', and 'System_note' columns.

    Returns:
        dict: A dictionary containing key statistics, including:
            - 'total_orders_completed' (int)
            - 'total_orders_not_completed' (int)
            - 'total_items_to_write_off' (int)
            - 'total_items_not_to_write_off' (int)
            - 'couriers_stats' (list[dict] | None): A list of dictionaries,
              each representing a courier's stats, or None if no orders
              were completed.
    """
    # Validate DataFrame has required columns
    required_cols = ["Order_Fulfillment_Status", "Order_Number", "Quantity", "Shipping_Provider", "System_note"]
    missing = [col for col in required_cols if col not in df.columns]

    if missing:
        import logging
        logger = logging.getLogger("ShopifyToolLogger")
        logger.error(f"Missing required columns in DataFrame: {missing}")
        logger.error(f"Available columns: {list(df.columns)}")
        raise ValueError(f"DataFrame missing required columns: {missing}")

    stats = {}
    completed_orders_df = df[df["Order_Fulfillment_Status"] == "Fulfillable"].copy()
    not_completed_orders_df = df[df["Order_Fulfillment_Status"] == "Not Fulfillable"]

    stats["total_orders_completed"] = int(completed_orders_df["Order_Number"].nunique())
    stats["total_orders_not_completed"] = int(not_completed_orders_df["Order_Number"].nunique())
    stats["total_items_to_write_off"] = int(completed_orders_df["Quantity"].sum())
    stats["total_items_not_to_write_off"] = int(not_completed_orders_df["Quantity"].sum())

    courier_stats = []
    if not completed_orders_df.empty:
        # Fill NA to include 'Unknown' providers in the stats
        completed_orders_df.loc[:, "Shipping_Provider"] = completed_orders_df["Shipping_Provider"].fillna("Unknown")
        grouped_by_courier = completed_orders_df.groupby("Shipping_Provider")
        for provider, group in grouped_by_courier:
            courier_data = {
                "courier_id": provider,
                "orders_assigned": int(group["Order_Number"].nunique()),
                "repeated_orders_found": int(group[group["System_note"] == "Repeat"]["Order_Number"].nunique()),
            }
            courier_stats.append(courier_data)
    # Per instructions, use null (None) if no stats are available
    stats["couriers_stats"] = courier_stats if courier_stats else None

    return stats


def toggle_order_fulfillment(df, order_number):
    """Manually toggles the fulfillment status of an order and recalculates stock.

    This function allows a user to manually override the automated fulfillment
    decision for a single order.

    - If an order is 'Fulfillable', it will be changed to 'Not Fulfillable',
      and the stock allocated to it will be returned to the pool (i.e.,
      'Final_Stock' for the affected SKUs will be increased).
    - If an order is 'Not Fulfillable', it will be changed to 'Fulfillable'.
      This is a "force-fulfill" action. The function first checks if there is
      enough 'Final_Stock' to cover the order. If not, it fails. If there is
      enough stock, it deducts the required quantities from 'Final_Stock'.

    The function operates on and returns a modified copy of the input DataFrame.

    Args:
        df (pd.DataFrame): The main analysis DataFrame.
        order_number (str): The order number to toggle.

    Returns:
        tuple[bool, str | None, pd.DataFrame]: A tuple containing:
            - success (bool): True if the toggle was successful, False otherwise.
            - error_message (str | None): An error message if success is False.
            - updated_df (pd.DataFrame): The modified DataFrame. If the toggle
              fails, this is the original, unmodified DataFrame.
    """
    if df is None or order_number not in df["Order_Number"].values:
        return False, "Order number not found.", df

    # Find current status (assuming all rows for an order have the same status)
    current_status = df.loc[df["Order_Number"] == order_number, "Order_Fulfillment_Status"].iloc[0]

    if current_status == "Fulfillable":
        # --- Logic to UN-FULFILL an order ---
        new_status = "Not Fulfillable"
        order_items = df.loc[df["Order_Number"] == order_number]

        # Aggregate quantities for each SKU in the order
        stock_to_return = order_items.groupby("SKU")["Quantity"].sum()

        for sku, quantity in stock_to_return.items():
            # Add the quantity back to the 'Final_Stock' for all rows with this SKU
            df.loc[df["SKU"] == sku, "Final_Stock"] += quantity
    else:
        # --- Logic to FORCE-FULFILL an order ---
        new_status = "Fulfillable"
        order_items = df.loc[df["Order_Number"] == order_number]
        items_needed = order_items.groupby("SKU")["Quantity"].sum()

        # Pre-flight check for stock availability
        lacking_skus = []
        for sku, needed_qty in items_needed.items():
            # Check if the SKU is even in our dataframe (for the unlisted stock case)
            if sku not in df["SKU"].unique():
                continue  # This is an unlisted item, we assume it's on hand

            # Get current final stock for this SKU
            current_stock = df.loc[df["SKU"] == sku, "Final_Stock"].iloc[0]

            if needed_qty > current_stock:
                lacking_skus.append(sku)

        if lacking_skus:
            error_message = f"Cannot force fulfill. Insufficient stock for SKUs: {', '.join(lacking_skus)}"
            return False, error_message, df  # Abort the toggle

        # If check passes, deduct stock
        for sku, needed_qty in items_needed.items():
            # For unlisted SKUs, we need to add them to the df to track their negative stock
            if sku not in df["SKU"].unique():
                # Find one of the order rows to copy base data from
                template_row = order_items.iloc[0].to_dict()
                new_row = {key: (None if key not in ["SKU", "Quantity"] else template_row[key]) for key in df.columns}
                new_row.update({"SKU": sku, "Quantity": 0, "Stock": 0, "Final_Stock": 0})
                # Use pd.concat instead of df.loc[len(df)] for robustness
                df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)

            df.loc[df["SKU"] == sku, "Final_Stock"] -= needed_qty

    # Update the DataFrame with the new status
    df.loc[df["Order_Number"] == order_number, "Order_Fulfillment_Status"] = new_status

    return True, None, df
