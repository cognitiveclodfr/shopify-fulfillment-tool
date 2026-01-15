import pandas as pd
import numpy as np
from typing import Tuple, Dict, List, Optional
import logging

logger = logging.getLogger(__name__)


def _clean_and_prepare_data(
    orders_df: pd.DataFrame,
    stock_df: pd.DataFrame,
    column_mappings: Optional[dict] = None
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Clean and standardize input data for analysis.

    Performs:
    - Apply column mappings from external sources to internal standard names
    - Handle NaN values in critical columns (forward-fill order-level columns)
    - Normalize column names and data types
    - Convert numeric columns (Quantity, Stock)
    - Normalize SKU format for consistent matching
    - Remove duplicates from stock data
    - Validate required columns exist
    - Expand sets/bundles into component SKUs

    Args:
        orders_df: Raw orders DataFrame with external column names
        stock_df: Raw stock DataFrame with external column names
        column_mappings: Configuration dictionary with column mappings and set decoders.
            Format: {
                "orders": {"External_Col": "Internal_Col", ...},
                "stock": {"External_Col": "Internal_Col", ...},
                "set_decoders": {...}
            }
            If None, uses default Shopify/Bulgarian mappings for backward compatibility.

    Returns:
        Tuple of (cleaned_orders_df, cleaned_stock_df)

    Raises:
        ValueError: If required columns missing after mapping
    """
    logger.debug("Phase 1/7: Cleaning and preparing data...")

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
                    "Total": "Total_Price",
                    "Subtotal": "Subtotal"
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
    if "Subtotal" in orders_df.columns:
        orders_df["Subtotal"] = orders_df["Subtotal"].ffill()

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
        "Subtotal",
    ]
    # Filter for existing columns only
    columns_to_keep_existing = [col for col in columns_to_keep if col in orders_df.columns]
    orders_clean_df = orders_df[columns_to_keep_existing].copy()

    # Mark rows without SKU but keep them (don't drop)
    orders_clean_df["Has_SKU"] = orders_clean_df["SKU"].notna()

    # Log warning about missing SKU rows
    missing_sku_mask = ~orders_clean_df["Has_SKU"]
    missing_sku_count = missing_sku_mask.sum()

    if missing_sku_count > 0:
        affected_orders = orders_clean_df.loc[missing_sku_mask, "Order_Number"].unique()
        logger.warning(
            f"Found {missing_sku_count} order rows without SKU "
            f"(typically shipping fees, discounts, or notes). "
            f"Affected orders: {affected_orders.tolist()[:10]}{'...' if len(affected_orders) > 10 else ''}"
        )

        # Fill missing SKU with placeholder
        orders_clean_df.loc[missing_sku_mask, "SKU"] = "NO_SKU"

        # Add descriptive product name if missing
        if "Product_Name" in orders_clean_df.columns:
            orders_clean_df.loc[missing_sku_mask, "Product_Name"] = \
                orders_clean_df.loc[missing_sku_mask, "Product_Name"].fillna("(No SKU - Shipping/Fee/Note)")

    # CRITICAL: Normalize SKU to standard format for consistent merging
    # This handles float artifacts (5170.0 → "5170"), whitespace, and leading zeros
    # Skip normalization for NO_SKU placeholder
    from .csv_utils import normalize_sku
    orders_clean_df.loc[orders_clean_df["Has_SKU"], "SKU"] = \
        orders_clean_df.loc[orders_clean_df["Has_SKU"], "SKU"].apply(normalize_sku)

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
    # Skip NO_SKU items (they don't participate in set expansion)
    from .set_decoder import decode_sets_in_orders

    set_decoders = column_mappings.get("set_decoders", {}) if column_mappings else {}
    if set_decoders:
        logger.info(f"Decoding sets: {len(set_decoders)} definitions")
        # Only expand sets for items with actual SKU (skip NO_SKU)
        items_with_sku = orders_clean_df[orders_clean_df["Has_SKU"] == True].copy()
        no_sku_items = orders_clean_df[orders_clean_df["Has_SKU"] == False].copy()

        expanded_items = decode_sets_in_orders(items_with_sku, set_decoders)

        # Add tracking columns to NO_SKU items for consistency
        if not no_sku_items.empty:
            no_sku_items["Original_SKU"] = no_sku_items["SKU"]
            no_sku_items["Original_Quantity"] = no_sku_items["Quantity"]
            no_sku_items["Is_Set_Component"] = False

        # Combine expanded items with NO_SKU items (unchanged)
        orders_clean_df = pd.concat([expanded_items, no_sku_items], ignore_index=True)
        logger.info(f"Orders after expansion: {len(orders_clean_df)} rows")
    else:
        # No sets defined - add tracking columns anyway for consistency
        orders_clean_df["Original_SKU"] = orders_clean_df["SKU"]
        orders_clean_df["Original_Quantity"] = orders_clean_df["Quantity"]
        orders_clean_df["Is_Set_Component"] = False

    logger.debug(f"Cleaned {len(orders_clean_df)} order rows, {len(stock_clean_df)} SKUs")
    return orders_clean_df, stock_clean_df


def _prioritize_orders(orders_df: pd.DataFrame) -> pd.DataFrame:
    """
    Prioritize orders to maximize fulfillment completion rate.

    Strategy:
    - Multi-item orders first (higher completion priority)
    - Then single-item orders
    - Within each group, sorted by order number for consistency

    This ensures maximum number of complete orders fulfilled.
    Uses VECTORIZED groupby operations instead of iterrows().

    Args:
        orders_df: Cleaned orders DataFrame

    Returns:
        DataFrame with columns ["Order_Number", "item_count"] in priority sequence

    Note:
        Multi-item orders are prioritized because completing them
        provides better customer satisfaction than partial fulfillment
        of multiple orders.
    """
    logger.debug("Phase 2/7: Prioritizing orders (multi-item first)...")

    # VECTORIZED: Count items per order using groupby
    order_item_counts = orders_df.groupby("Order_Number").size().rename("item_count")

    # Merge counts back to get unique orders with their counts
    orders_with_counts = pd.merge(orders_df, order_item_counts, on="Order_Number")

    # Get unique orders and sort by item count (descending), then by order number
    prioritized_orders = (
        orders_with_counts[["Order_Number", "item_count"]]
        .drop_duplicates()
        .sort_values(by=["item_count", "Order_Number"], ascending=[False, True])
    )

    logger.debug(f"Prioritized {len(prioritized_orders)} unique orders")
    return prioritized_orders


def _simulate_stock_allocation(
    orders_df: pd.DataFrame,
    stock_df: pd.DataFrame,
    prioritized_orders: pd.DataFrame
) -> Dict[str, str]:
    """
    Simulate stock allocation across prioritized orders.

    Algorithm:
    1. Initialize stock availability dict from stock DataFrame
    2. Process orders in priority sequence
    3. For each order, check if all items available
    4. Mark order as fulfillable/not fulfillable
    5. Deduct stock for fulfillable orders

    Skips items without SKU (Has_SKU=False) as they don't consume stock.

    Performance:
    Uses VECTORIZED operations where possible. The main loop iterates over
    unique orders (not individual items), which is necessary for the sequential
    stock allocation logic.

    Args:
        orders_df: Cleaned orders DataFrame with item counts
        stock_df: Stock availability DataFrame
        prioritized_orders: DataFrame with ["Order_Number", "item_count"] in priority order

    Returns:
        Dictionary mapping order_number to fulfillment status
        Format: {"ORDER-123": "Fulfillable", "ORDER-124": "Not Fulfillable"}

    Note:
        This is the core fulfillment simulation algorithm.
        Changes here affect all downstream reporting.
    """
    logger.debug("Phase 3/7: Simulating stock allocation...")

    # Filter out NO_SKU items before simulation (they don't consume stock)
    if "Has_SKU" in orders_df.columns:
        orders_for_simulation = orders_df[orders_df["Has_SKU"] == True].copy()
        no_sku_count = (~orders_df["Has_SKU"]).sum()
        if no_sku_count > 0:
            logger.debug(f"Skipping {no_sku_count} NO_SKU items from stock simulation")
    else:
        orders_for_simulation = orders_df.copy()

    # Initialize stock tracking - VECTORIZED dict creation
    live_stock = pd.Series(stock_df.Stock.values, index=stock_df.SKU).to_dict()
    fulfillment_results = {}

    # Add item_count to orders for filtering
    order_item_counts = orders_for_simulation.groupby("Order_Number").size().rename("item_count")
    orders_with_counts = pd.merge(orders_for_simulation, order_item_counts, on="Order_Number")

    # Iterate over prioritized orders (necessary for sequential allocation)
    for order_number in prioritized_orders["Order_Number"]:
        # Get all items for this order - VECTORIZED filter
        order_items = orders_with_counts[orders_with_counts["Order_Number"] == order_number]

        # Check if order can be fulfilled - VECTORIZED check
        # Group by SKU to handle multiple line items of same SKU
        required_quantities = order_items.groupby("SKU")["Quantity"].sum()

        can_fulfill_order = True
        unfulfillable_reasons = []

        for sku, required_qty in required_quantities.items():
            available = live_stock.get(sku, 0)
            if available == 0:
                unfulfillable_reasons.append(f"{sku}: Out of stock")
                can_fulfill_order = False
            elif required_qty > available:
                unfulfillable_reasons.append(
                    f"{sku}: Insufficient stock (need {int(required_qty)}, have {int(available)})"
                )
                can_fulfill_order = False

        # Update fulfillment status and deduct stock if fulfillable
        if can_fulfill_order:
            fulfillment_results[order_number] = {
                "fulfillable": True,
                "reason": ""
            }
            # Deduct stock - VECTORIZED operation
            for sku, qty in required_quantities.items():
                live_stock[sku] -= qty
        else:
            fulfillment_results[order_number] = {
                "fulfillable": False,
                "reason": "; ".join(unfulfillable_reasons)
            }

    fulfillable_count = sum(1 for result in fulfillment_results.values() if result.get("fulfillable", False))
    logger.debug(f"Fulfillable: {fulfillable_count}/{len(fulfillment_results)} orders")

    return fulfillment_results


def _calculate_final_stock(
    stock_df: pd.DataFrame,
    fulfillment_results: Dict[str, str],
    orders_df: pd.DataFrame
) -> pd.DataFrame:
    """
    Calculate final stock levels after fulfillment simulation.

    Recalculates stock by replaying the fulfillment decisions to determine
    remaining stock for each SKU.

    Args:
        stock_df: Initial stock DataFrame
        fulfillment_results: Dict of order_number -> status from simulation
        orders_df: Orders DataFrame

    Returns:
        DataFrame with columns ["SKU", "Final_Stock"]

    Note:
        This recreates the stock calculation based on fulfillment results.
    """
    logger.debug("Phase 4/7: Calculating final stock levels...")

    # Initialize final stock from initial stock
    live_stock = pd.Series(stock_df.Stock.values, index=stock_df.SKU).to_dict()

    # Replay fulfillment to calculate final stock
    for order_number, result in fulfillment_results.items():
        if result.get("fulfillable", False):
            # Get items for this order
            order_items = orders_df[orders_df["Order_Number"] == order_number]
            # Deduct stock - VECTORIZED groupby
            # Skip NO_SKU items (they don't consume stock)
            for sku, qty in order_items.groupby("SKU")["Quantity"].sum().items():
                if sku in live_stock:  # Only deduct if SKU exists in stock
                    live_stock[sku] -= qty

    # Convert to DataFrame
    final_stock_levels = pd.Series(live_stock, name="Final_Stock").reset_index().rename(columns={"index": "SKU"})

    logger.debug(f"Calculated final stock for {len(final_stock_levels)} SKUs")
    return final_stock_levels


def _detect_repeated_orders(
    final_df: pd.DataFrame,
    history_df: pd.DataFrame,
    repeat_window_days: int = 1
) -> pd.Series:
    """
    Detect orders that appear in historical fulfillment data within specified time window.

    Business Logic:
    An order is "repeated" if the same Order_Number appears in historical
    fulfillment data within the last N days.

    Args:
        final_df: Current orders DataFrame with Order_Number column
        history_df: Historical orders DataFrame with Order_Number, Execution_Date columns
        repeat_window_days: Number of days to look back (default: 1)

    Returns:
        pd.Series (string) with "Repeat" for repeated orders, "" otherwise

    Example:
        >>> repeated = _detect_repeated_orders(final_df, history_df, repeat_window_days=7)
        >>> final_df['System_note'] = repeated
    """
    logger.debug(f"Phase 5/7: Detecting repeated orders (window: {repeat_window_days} days)...")

    # Handle empty history or missing date column (backward compatibility)
    if history_df.empty or "Execution_Date" not in history_df.columns:
        logger.warning("History has no Execution_Date column, using full history")
        repeated_orders = history_df["Order_Number"].unique() if not history_df.empty else []
    else:
        # FILTER history by date window
        from datetime import datetime, timedelta

        try:
            # Parse dates (handle errors gracefully)
            history_df_copy = history_df.copy()
            history_df_copy["Execution_Date_Parsed"] = pd.to_datetime(
                history_df_copy["Execution_Date"],
                errors='coerce'
            )

            # Check if all dates are invalid (NaT)
            if history_df_copy["Execution_Date_Parsed"].isna().all():
                logger.warning("All dates in history are invalid, using full history")
                repeated_orders = history_df["Order_Number"].unique()
            else:
                # Normalize to date-only (remove time component) for consistent comparison
                history_df_copy["Execution_Date_Parsed"] = history_df_copy["Execution_Date_Parsed"].dt.normalize()

                # Filter by time window (normalize cutoff to midnight)
                cutoff_date = (datetime.now() - timedelta(days=repeat_window_days)).replace(hour=0, minute=0, second=0, microsecond=0)
                recent_history = history_df_copy[
                    history_df_copy["Execution_Date_Parsed"] >= cutoff_date
                ]

                repeated_orders = recent_history["Order_Number"].unique()

                logger.info(
                    f"Using {len(recent_history)} recent history records "
                    f"(total: {len(history_df)}, cutoff: {cutoff_date.strftime('%Y-%m-%d')})"
                )
        except Exception as e:
            logger.error(f"Failed to parse history dates: {e}", exc_info=True)
            # Fallback to full history
            repeated_orders = history_df["Order_Number"].unique()
            logger.warning("Falling back to full history due to date parsing error")

    # VECTORIZED: Check if Order_Number exists in filtered history
    repeated = np.where(
        final_df["Order_Number"].isin(repeated_orders),
        "Repeat",
        ""
    )

    repeated_count = (repeated == "Repeat").sum()
    logger.debug(f"Found {repeated_count} repeated orders within {repeat_window_days} days")

    return pd.Series(repeated, index=final_df.index)


def _migrate_packaging_tags(final_df: pd.DataFrame) -> pd.DataFrame:
    """
    Migrate Packaging_Tags to Internal_Tags system.

    This handles backward compatibility by migrating old packaging tags
    to the new structured tagging system.

    Args:
        final_df: DataFrame with potential Packaging_Tags column

    Returns:
        DataFrame with updated Internal_Tags column
    """
    logger.debug("Migrating Packaging_Tags to Internal_Tags (if present)...")

    # Migrate Packaging_Tags to Internal_Tags if it exists
    if "Packaging_Tags" in final_df.columns:
        from shopify_tool.tag_manager import add_tag

        logger.info("Migrating Packaging_Tags to Internal_Tags")

        # VECTORIZED approach: Apply function to each row
        # While apply() is not fully vectorized, it's better than iterrows()
        # and necessary here because add_tag modifies a JSON string
        def migrate_tag(row):
            packaging_tag = row["Packaging_Tags"]
            if pd.notna(packaging_tag) and packaging_tag != "":
                return add_tag(row["Internal_Tags"], str(packaging_tag))
            return row["Internal_Tags"]

        final_df["Internal_Tags"] = final_df.apply(migrate_tag, axis=1)
        logger.info("Packaging_Tags migration completed")

    return final_df


def _merge_results_to_dataframe(
    orders_df: pd.DataFrame,
    stock_df: pd.DataFrame,
    order_item_counts: pd.Series,
    final_stock_levels: pd.DataFrame,
    fulfillment_results: Dict[str, str],
    history_df: pd.DataFrame,
    courier_mappings: Optional[dict] = None,
    repeat_window_days: int = 1
) -> pd.DataFrame:
    """
    Merge all analysis results into final output DataFrame.

    Combines:
    - Original order data
    - Stock information
    - Fulfillment simulation results
    - Item counts
    - Final stock levels
    - Repeated orders flags
    - Courier mappings
    - All calculated fields

    Args:
        orders_df: Cleaned orders DataFrame
        stock_df: Cleaned stock DataFrame
        order_item_counts: Series with item counts per order
        final_stock_levels: DataFrame with final stock calculations
        fulfillment_results: Dict of order fulfillment statuses
        history_df: Historical fulfillment data
        courier_mappings: Optional courier mapping configuration

    Returns:
        Complete analyzed DataFrame ready for reporting

    Output Columns:
    - All original order columns
    - Stock, Final_Stock (from stock data)
    - Warehouse_Name (from stock data)
    - Order_Fulfillment_Status (from simulation)
    - Order_Type (Single/Multi)
    - Shipping_Provider (mapped)
    - Destination_Country
    - System_note (Repeat flag)
    - Stock_Alert, Status_Note (initialized)
    - Source (initialized to "Order")
    - Internal_Tags (structured tagging)
    """
    logger.debug("Phase 6/7: Merging results to final DataFrame...")

    # --- Merge orders with stock data ---
    # If both have Product_Name, prefer the one from orders (use suffixes to handle conflict)
    has_product_name_in_orders = "Product_Name" in orders_df.columns
    has_product_name_in_stock = "Product_Name" in stock_df.columns

    if has_product_name_in_orders and has_product_name_in_stock:
        # Both have Product_Name - use suffixes and prefer orders
        final_df = pd.merge(orders_df, stock_df, on="SKU", how="left", suffixes=('', '_stock'))
        # Drop stock Product_Name, keep orders Product_Name
        if 'Product_Name_stock' in final_df.columns:
            final_df = final_df.drop(columns=['Product_Name_stock'])
    else:
        # Simple merge - no conflict
        final_df = pd.merge(orders_df, stock_df, on="SKU", how="left")

    # --- Add Warehouse_Name column from stock file ---
    # Create stock name lookup dictionary
    if "Product_Name" in stock_df.columns:
        stock_lookup = dict(zip(
            stock_df["SKU"],
            stock_df["Product_Name"]
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

    # Merge item counts
    final_df = pd.merge(final_df, order_item_counts, on="Order_Number")

    # Merge final stock levels to the main dataframe
    final_df = pd.merge(final_df, final_stock_levels, on="SKU", how="left")
    final_df["Final_Stock"] = final_df["Final_Stock"].fillna(
        final_df["Stock"]
    )  # If an item was not fulfilled, its final stock is its initial stock

    # Add Order_Type (Single/Multi)
    final_df["Order_Type"] = np.where(final_df["item_count"] > 1, "Multi", "Single")

    # Fill missing stock with 0
    final_df["Stock"] = final_df["Stock"].fillna(0)

    # Use Shipping_Method with underscore (internal name)
    if "Shipping_Method" in final_df.columns:
        final_df["Shipping_Provider"] = final_df["Shipping_Method"].apply(
            lambda method: _generalize_shipping_method(method, courier_mappings)
        )
    else:
        final_df["Shipping_Provider"] = "Unknown"

    # Map fulfillment results
    # Extract status from the new dict structure
    def get_fulfillment_status(order_number):
        result = fulfillment_results.get(order_number, {})
        if isinstance(result, dict):
            return "Fulfillable" if result.get("fulfillable", False) else "Not Fulfillable"
        # Backward compatibility: if result is a string
        return result

    final_df["Order_Fulfillment_Status"] = final_df["Order_Number"].map(get_fulfillment_status)

    # Use Shipping_Country with underscore (internal name)
    if "Shipping_Country" in final_df.columns:
        final_df["Destination_Country"] = np.where(
            final_df["Shipping_Provider"] == "DHL",
            final_df["Shipping_Country"],
            ""
        )
    else:
        final_df["Destination_Country"] = ""

    # Detect repeated orders - VECTORIZED
    final_df["System_note"] = _detect_repeated_orders(final_df, history_df, repeat_window_days)

    # Add unfulfillable reasons to System_note
    def add_fulfillment_reason(row):
        order_number = row["Order_Number"]
        result = fulfillment_results.get(order_number, {})

        if isinstance(result, dict) and not result.get("fulfillable", True):
            reason = result.get("reason", "Unknown reason")
            existing_note = row["System_note"]

            # Append reason to existing note
            if pd.notna(existing_note) and existing_note != "":
                return f"{existing_note}; Cannot fulfill: {reason}"
            else:
                return f"Cannot fulfill: {reason}"

        return row["System_note"]

    final_df["System_note"] = final_df.apply(add_fulfillment_reason, axis=1)

    # Mark NO_SKU orders as Not Fulfillable with explanation
    if "Has_SKU" in final_df.columns:
        no_sku_mask = final_df["Has_SKU"] == False
        if no_sku_mask.any():
            final_df.loc[no_sku_mask, "Order_Fulfillment_Status"] = "Not Fulfillable"
            # Add NO_SKU tag to System_note
            final_df.loc[no_sku_mask, "System_note"] = final_df.loc[no_sku_mask, "System_note"].apply(
                lambda note: f"{note} [NO_SKU]" if pd.notna(note) and note != "" else "[NO_SKU]"
            )
            logger.info(f"Marked {no_sku_mask.sum()} NO_SKU items as Not Fulfillable")

    # Initialize additional columns
    final_df["Stock_Alert"] = ""  # Initialize the column
    final_df["Status_Note"] = ""  # Initialize column for user-defined rule tags

    # Initialize Source column (all orders start as "Order")
    final_df["Source"] = "Order"

    # Initialize Internal_Tags column (structured tagging system)
    final_df["Internal_Tags"] = "[]"

    # Migrate Packaging_Tags to Internal_Tags if it exists
    final_df = _migrate_packaging_tags(final_df)

    # Select and order output columns
    output_columns = [
        "Order_Number",
        "Order_Type",
        "SKU",
        "Product_Name",
        "Warehouse_Name",  # From stock file
        "Quantity",
        "Stock",
        "Final_Stock",
        "Source",  # "Order" or "Manual"
        "Stock_Alert",
        "Order_Fulfillment_Status",
        "Shipping_Provider",
        "Destination_Country",
        "Shipping_Method",
        "Tags",
        "Notes",
        "System_note",
        "Status_Note",
        "Internal_Tags",  # Structured tagging system
    ]
    if "Total_Price" in final_df.columns:
        # Insert 'Total_Price' into the list at a specific position for consistent column order.
        # Placed after 'Quantity'.
        output_columns.insert(6, "Total_Price")
    if "Subtotal" in final_df.columns:
        # Insert 'Subtotal' after Total_Price (position 7)
        output_columns.insert(7, "Subtotal")
    if "Has_SKU" in final_df.columns:
        # Insert 'Has_SKU' after SKU (position 3)
        output_columns.insert(3, "Has_SKU")

    # Filter the list to include only columns that actually exist in the DataFrame.
    # This prevents errors if a column is unexpectedly missing.
    final_output_columns = [col for col in output_columns if col in final_df.columns]
    final_df = final_df[final_output_columns].copy()  # Use .copy() to avoid SettingWithCopyWarning

    logger.debug(f"Final DataFrame: {len(final_df)} rows, {len(final_df.columns)} columns")
    return final_df


def _generate_summary_reports(
    final_df: pd.DataFrame
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Generate summary reports for fulfilled and missing items.

    Creates two summary DataFrames:
    1. Summary of items that will be fulfilled (from fulfillable orders)
    2. Summary of items that are truly missing (required > initial stock)

    Args:
        final_df: Complete analyzed DataFrame

    Returns:
        Tuple of (summary_present_df, summary_missing_df)

    Format:
        Both DataFrames have columns: ["Name", "SKU", "Total Quantity"]
    """
    logger.debug("Phase 7/7: Generating summary reports...")

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

    logger.debug(f"Summary present: {len(summary_present_df)} SKUs")
    logger.debug(f"Summary missing: {len(summary_missing_df)} SKUs")

    return summary_present_df, summary_missing_df


def _generalize_shipping_method(method, courier_mappings=None):
    """Standardizes raw shipping method names to a consistent format.

    Takes a raw shipping method string, converts it to lowercase, and maps it
    to a standardized provider name using either the provided courier_mappings
    or hardcoded fallback rules.

    The function supports two courier_mappings formats:
    1. New format (preferred):
       {"DHL": {"patterns": ["dhl", "dhl express"]}, "DPD": {"patterns": ["dpd"]}}
    2. Legacy format (for backward compatibility):
       {"dhl": "DHL", "dpd": "DPD"}

    If the method is not recognized, it returns a title-cased version of the
    input. Handles NaN values by returning 'Unknown'.

    Args:
        method (str | float): The raw shipping method from the orders file.
            Can be a float (NaN) for empty values.
        courier_mappings (dict, optional): Dictionary mapping courier patterns to
            standardized courier codes. If None or empty, uses hardcoded fallback
            rules for backward compatibility.

    Returns:
        str: The standardized shipping provider name.

    Examples:
        >>> _generalize_shipping_method("dhl express", {"DHL": {"patterns": ["dhl"]}})
        'DHL'
        >>> _generalize_shipping_method("custom courier", {})
        'Custom Courier'
        >>> _generalize_shipping_method(None)
        'Unknown'
    """
    # Handle NaN and empty values
    if pd.isna(method):
        return "Unknown"
    method_str = str(method)
    if not method_str.strip():
        return "Unknown"

    method_lower = method_str.lower()

    # If courier_mappings provided and not empty, use dynamic mapping
    if courier_mappings:
        # Check if new format (dict of dicts with "patterns" key)
        # or legacy format (simple dict mapping)
        for courier_code, mapping_data in courier_mappings.items():
            if isinstance(mapping_data, dict):
                # New format: {"DHL": {"patterns": ["dhl", "dhl express"]}}
                patterns = mapping_data.get("patterns", [])
                for pattern in patterns:
                    if pattern.lower() in method_lower:
                        return courier_code
            else:
                # Legacy format: {"dhl": "DHL"}
                # Check if the pattern (key) is in the method
                if courier_code.lower() in method_lower:
                    return mapping_data
    else:
        # Fallback to hardcoded rules for backward compatibility
        if "dhl" in method_lower:
            return "DHL"
        if "dpd" in method_lower:
            return "DPD"
        if "international shipping" in method_lower:
            return "PostOne"

    # If no match found, return title-cased version
    return method_str.title()


def run_analysis(stock_df, orders_df, history_df, column_mappings=None, courier_mappings=None, repeat_window_days=1):
    """
    Main analysis engine for order fulfillment simulation.

    Orchestrates complete analysis workflow through 7 specialized phases:
    1. Data cleaning and preparation
    2. Order prioritization (multi-item first strategy)
    3. Stock allocation simulation
    4. Final stock calculations
    5. Repeated orders detection
    6. Results merging to final DataFrame
    7. Summary statistics generation

    Algorithm:
    - Prioritizes multi-item orders for maximum completion rate
    - Simulates stock allocation in priority sequence
    - Tracks repeated orders against history
    - Provides comprehensive fulfillment analytics

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
        courier_mappings (dict, optional): Dictionary mapping courier patterns to
            standardized courier codes. Supports two formats:
            1. New: {"DHL": {"patterns": ["dhl", "dhl express"]}}
            2. Legacy: {"dhl": "DHL"}
            If None or empty, uses hardcoded fallback rules for backward compatibility.
        repeat_window_days (int, optional): Number of days to look back for repeat
            detection. Orders fulfilled within this window are marked as "Repeat".
            Default: 1 (only yesterday's fulfillments).

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

    Raises:
        ValueError: If data validation fails
        KeyError: If required columns missing

    Example:
        >>> final_df, present, missing, stats = run_analysis(
        ...     stock_df=stock,
        ...     orders_df=orders,
        ...     history_df=history
        ... )
    """
    logger.info("=" * 60)
    logger.info("STARTING ORDER FULFILLMENT ANALYSIS")
    logger.info("=" * 60)

    try:
        # Phase 1: Clean and prepare data
        logger.info("Phase 1/7: Data cleaning and preparation")
        orders_clean, stock_clean = _clean_and_prepare_data(
            orders_df, stock_df, column_mappings
        )

        # Phase 2: Prioritize orders
        logger.info("Phase 2/7: Order prioritization (multi-item first)")
        prioritized_orders = _prioritize_orders(orders_clean)

        # Phase 3: Simulate stock allocation
        logger.info("Phase 3/7: Stock allocation simulation")
        fulfillment_results = _simulate_stock_allocation(
            orders_clean, stock_clean, prioritized_orders
        )

        # Phase 4: Calculate final stock
        logger.info("Phase 4/7: Final stock calculations")
        final_stock = _calculate_final_stock(
            stock_clean, fulfillment_results, orders_clean
        )

        # Phase 5: Already handled in Phase 6 (_detect_repeated_orders is called there)
        # Phase 6: Merge all results
        logger.info("Phase 5/7: Merging results to final DataFrame")
        order_item_counts = orders_clean.groupby("Order_Number").size().rename("item_count")
        final_df = _merge_results_to_dataframe(
            orders_clean, stock_clean, order_item_counts, final_stock,
            fulfillment_results, history_df, courier_mappings, repeat_window_days
        )

        # Phase 7: Generate summary reports
        logger.info("Phase 6/7: Generating summary reports")
        summary_present_df, summary_missing_df = _generate_summary_reports(final_df)

        # Phase 8: Calculate statistics
        logger.info("Phase 7/7: Calculating statistics")
        stats = recalculate_statistics(final_df)

        logger.info("=" * 60)
        logger.info("ANALYSIS COMPLETED SUCCESSFULLY")
        logger.info(f"Total Orders Completed: {stats['total_orders_completed']}")
        logger.info(f"Total Orders Not Completed: {stats['total_orders_not_completed']}")
        logger.info("=" * 60)

        return final_df, summary_present_df, summary_missing_df, stats

    except ValueError as e:
        logger.error(f"Validation error during analysis: {e}")
        raise
    except KeyError as e:
        logger.error(f"Missing required column: {e}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error during analysis: {e}", exc_info=True)
        raise


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
            - 'tags_breakdown' (dict | None): Dictionary mapping tags to counts.
            - 'sku_summary' (list[dict] | None): List of SKU summary data.
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

    # === NEW: Tags Breakdown ===
    tags_breakdown = None
    if "Internal_Tags" in df.columns:
        try:
            # Parse all tags from Internal_Tags column (JSON format)
            from shopify_tool.tag_manager import parse_tags

            # Collect all tags across all orders
            all_tags = []
            for tags_json in df["Internal_Tags"].dropna():
                tags = parse_tags(tags_json)  # Returns list of tag strings
                all_tags.extend(tags)

            # Count occurrences
            from collections import Counter
            tag_counts = Counter(all_tags)

            # Convert to sorted dict (by count, descending)
            tags_breakdown = dict(sorted(
                tag_counts.items(),
                key=lambda x: x[1],
                reverse=True
            ))

            import logging
            logger = logging.getLogger("ShopifyToolLogger")
            logger.info(f"Tags breakdown calculated: {len(tags_breakdown)} unique tags")

        except Exception as e:
            import logging
            logger = logging.getLogger("ShopifyToolLogger")
            logger.error(f"Failed to calculate tags breakdown: {e}", exc_info=True)
            tags_breakdown = None

    # === NEW: SKU Summary ===
    sku_summary = None
    try:
        # Create a helper column for fulfillable quantity
        df_temp = df.copy()
        df_temp["Fulfillable_Qty"] = df_temp.apply(
            lambda row: row["Quantity"] if row["Order_Fulfillment_Status"] == "Fulfillable" else 0,
            axis=1
        )

        # Group by SKU and aggregate
        sku_groups = df_temp.groupby("SKU").agg({
            "Quantity": "sum",  # Total quantity across all orders
            "Product_Name": "first",  # Product name (should be same for all rows)
            "Warehouse_Name": "first",  # Warehouse name from stock
            "Fulfillable_Qty": "sum"  # Sum of fulfillable quantities
        }).reset_index()

        # Rename columns for clarity
        sku_groups.columns = ["SKU", "Total_Quantity", "Product_Name", "Warehouse_Name", "Fulfillable_Items"]

        # Calculate not fulfillable items
        sku_groups["Not_Fulfillable_Items"] = sku_groups["Total_Quantity"] - sku_groups["Fulfillable_Items"]

        # Sort by total quantity (descending)
        sku_groups = sku_groups.sort_values("Total_Quantity", ascending=False)

        # Convert to list of dicts
        sku_summary = sku_groups.to_dict("records")

        import logging
        logger = logging.getLogger("ShopifyToolLogger")
        logger.info(f"SKU summary calculated: {len(sku_summary)} unique SKUs")

    except Exception as e:
        import logging
        logger = logging.getLogger("ShopifyToolLogger")
        logger.error(f"Failed to calculate SKU summary: {e}", exc_info=True)
        sku_summary = None

    stats["tags_breakdown"] = tags_breakdown
    stats["sku_summary"] = sku_summary

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
    if df is None:
        return False, "DataFrame is None.", df

    # Convert order_number to string for comparison (handles int/float order numbers)
    order_number_str = str(order_number).strip()
    order_numbers_str = df["Order_Number"].astype(str).str.strip()

    if order_number_str not in order_numbers_str.values:
        return False, "Order number not found.", df

    # Find current status (assuming all rows for an order have the same status)
    # Use string comparison for finding the order
    order_mask = order_numbers_str == order_number_str
    current_status = df.loc[order_mask, "Order_Fulfillment_Status"].iloc[0]

    if current_status == "Fulfillable":
        # --- Logic to UN-FULFILL an order ---
        new_status = "Not Fulfillable"
        order_items = df.loc[order_mask]

        # Aggregate quantities for each SKU in the order
        stock_to_return = order_items.groupby("SKU")["Quantity"].sum()

        for sku, quantity in stock_to_return.items():
            # Add the quantity back to the 'Final_Stock' for all rows with this SKU
            df.loc[df["SKU"] == sku, "Final_Stock"] += quantity
    else:
        # --- Logic to FORCE-FULFILL an order ---
        new_status = "Fulfillable"
        order_items = df.loc[order_mask]
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
    df.loc[order_mask, "Order_Fulfillment_Status"] = new_status

    return True, None, df
