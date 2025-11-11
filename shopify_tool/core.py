import os
import logging
import pandas as pd
import json
import shutil
import csv
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple, Dict, Any
from . import analysis, packing_lists, stock_export, batch_loader
from .rules import RuleEngine
from .utils import get_persistent_data_path
import numpy as np

SYSTEM_TAGS = ["Repeat", "Priority", "Error"]

logger = logging.getLogger("ShopifyToolLogger")


def _normalize_unc_path(path):
    """Normalizes a path, which is especially useful for UNC paths on Windows."""
    if not path:
        return path
    # os.path.normpath will convert / to \ on Windows and handle other inconsistencies
    return os.path.normpath(path)


def _create_analysis_data_for_packing(final_df: pd.DataFrame) -> Dict[str, Any]:
    """Create analysis_data.json structure for Packing Tool integration.

    This function extracts relevant data from the analysis DataFrame and
    formats it in a structure that the Packing Tool can consume.

    Args:
        final_df (pd.DataFrame): The final analysis DataFrame

    Returns:
        Dict[str, Any]: Dictionary containing analysis data in Packing Tool format
    """
    try:
        # Group by Order_Number to get order-level data
        orders_data = []
        grouped = final_df.groupby("Order_Number")

        for order_number, group in grouped:
            # Get first row for order-level fields (they should be same for all items in order)
            first_row = group.iloc[0]

            order_data = {
                "order_number": str(order_number),
                "courier": first_row.get("Courier", ""),
                "status": first_row.get("Order_Fulfillment_Status", "Unknown"),
                "shipping_country": first_row.get("Shipping_Country", ""),
                "tags": first_row.get("Tags", ""),
                "items": []
            }

            # Add all items in the order
            for _, row in group.iterrows():
                item_data = {
                    "sku": str(row.get("SKU", "")),
                    "product_name": str(row.get("Product_Name", "")),
                    "quantity": int(row.get("Quantity", 0))
                }
                order_data["items"].append(item_data)

            orders_data.append(order_data)

        # Calculate statistics
        total_orders = len(orders_data)
        fulfillable_orders = len([o for o in orders_data if o["status"] == "Fulfillable"])
        not_fulfillable_orders = total_orders - fulfillable_orders

        analysis_data = {
            "analyzed_at": datetime.now().isoformat(),
            "total_orders": total_orders,
            "fulfillable_orders": fulfillable_orders,
            "not_fulfillable_orders": not_fulfillable_orders,
            "orders": orders_data
        }

        return analysis_data

    except Exception as e:
        logger.error(f"Failed to create analysis data for packing: {e}", exc_info=True)
        return {
            "analyzed_at": datetime.now().isoformat(),
            "total_orders": 0,
            "fulfillable_orders": 0,
            "not_fulfillable_orders": 0,
            "orders": [],
            "error": str(e)
        }


def _validate_dataframes(orders_df, stock_df, config):
    """Validates that the required columns are present in the dataframes.

    Checks the orders and stock DataFrames against the required columns
    specified in the application configuration.

    Args:
        orders_df (pd.DataFrame): The DataFrame containing order data.
        stock_df (pd.DataFrame): The DataFrame containing stock data.
        config (dict): The application configuration dictionary, which contains
            the 'column_mappings' with 'orders_required' and
            'stock_required' lists.

    Returns:
        list[str]: A list of error messages. If the list is empty,
                   validation passed.
    """
    errors = []
    column_mappings = config.get("column_mappings", {})
    required_orders_cols = column_mappings.get("orders_required", [])
    required_stock_cols = column_mappings.get("stock_required", [])

    for col in required_orders_cols:
        if col not in orders_df.columns:
            errors.append(f"Missing required column in Orders file: '{col}'")

    for col in required_stock_cols:
        if col not in stock_df.columns:
            errors.append(f"Missing required column in Stock file: '{col}'")

    return errors


def detect_csv_encoding(file_path):
    """Automatically detect the encoding of a CSV file.

    Tries multiple common encodings and returns the first one that works.
    Prioritizes encodings commonly used for CSV files.

    Args:
        file_path (str): The path to the CSV file.

    Returns:
        str: The detected encoding (e.g., 'utf-8', 'windows-1251', 'cp1252')
    """
    # Common encodings to try, in order of preference
    encodings_to_try = [
        'utf-8-sig',      # UTF-8 with BOM (common in Excel exports)
        'utf-8',          # Standard UTF-8
        'windows-1251',   # Cyrillic (Ukrainian, Russian, Bulgarian)
        'cp1252',         # Western European (common in Windows)
        'latin-1',        # ISO-8859-1 (never fails, but may produce garbage)
    ]

    for encoding in encodings_to_try:
        try:
            with open(file_path, 'r', encoding=encoding) as file:
                # Try to read first few lines
                sample = file.read(8192)  # Read first 8KB

                # If we can decode it without errors, it's likely correct
                if sample:
                    logger.info(f"Detected encoding '{encoding}' for file {file_path}")
                    return encoding

        except (UnicodeDecodeError, UnicodeError):
            # This encoding doesn't work, try next one
            continue
        except Exception as e:
            # Other error, skip this encoding
            logger.debug(f"Error trying encoding '{encoding}' for {file_path}: {e}")
            continue

    # If nothing worked, fall back to latin-1 (it never fails)
    logger.warning(f"Could not detect encoding for {file_path}, using 'latin-1' as fallback")
    return 'latin-1'


def detect_csv_delimiter(file_path, sample_size=5):
    """Automatically detect the delimiter used in a CSV file.

    Uses Python's csv.Sniffer to detect the delimiter by analyzing
    a sample of the file. Falls back to common delimiters if detection fails.

    Args:
        file_path (str): The path to the CSV file.
        sample_size (int, optional): Number of lines to sample. Defaults to 5.

    Returns:
        str: The detected delimiter (most commonly ',' or ';')
    """
    common_delimiters = [',', ';', '\t', '|']

    # First, detect encoding
    encoding = detect_csv_encoding(file_path)

    try:
        with open(file_path, 'r', encoding=encoding) as file:
            # Read sample lines
            sample_lines = []
            for _ in range(sample_size):
                line = file.readline()
                if not line:
                    break
                sample_lines.append(line)

            if not sample_lines:
                logger.warning(f"File {file_path} is empty, using default delimiter ','")
                return ','

            sample = ''.join(sample_lines)

            # Try to detect delimiter using csv.Sniffer
            try:
                sniffer = csv.Sniffer()
                delimiter = sniffer.sniff(sample, delimiters=''.join(common_delimiters)).delimiter
                logger.info(f"Detected delimiter '{delimiter}' for file {file_path}")
                return delimiter
            except csv.Error:
                # If sniffer fails, try to count occurrences of common delimiters
                delimiter_counts = {}
                for delim in common_delimiters:
                    # Count occurrences in first line (header)
                    count = sample_lines[0].count(delim)
                    if count > 0:
                        delimiter_counts[delim] = count

                if delimiter_counts:
                    # Return delimiter with highest count
                    detected = max(delimiter_counts, key=delimiter_counts.get)
                    logger.info(f"Detected delimiter '{detected}' by counting (file: {file_path})")
                    return detected
                else:
                    logger.warning(f"Could not detect delimiter for {file_path}, using default ','")
                    return ','

    except Exception as e:
        logger.error(f"Error detecting delimiter for {file_path}: {e}")
        return ','


def validate_csv_headers(file_path, required_columns, delimiter=",", encoding=None):
    """Quickly validates if a CSV file contains the required column headers.

    This function reads only the header row of a CSV file to check for the
    presence of required columns without loading the entire file into memory.

    Args:
        file_path (str): The path to the CSV file.
        required_columns (list[str]): A list of column names that must be present.
        delimiter (str, optional): The delimiter used in the CSV file.
            Defaults to ",".
        encoding (str, optional): The file encoding. If None, will auto-detect.

    Returns:
        tuple[bool, list[str]]: A tuple containing:
            - bool: True if all required columns are present, False otherwise.
            - list[str]: A list of missing columns. An empty list if all are
              present. Returns a list with an error message on file read
              errors.
    """
    if not required_columns:
        return True, []

    # Auto-detect encoding if not provided
    if encoding is None:
        encoding = detect_csv_encoding(file_path)

    try:
        headers = pd.read_csv(file_path, nrows=0, delimiter=delimiter, encoding=encoding).columns.tolist()
        missing_columns = [col for col in required_columns if col not in headers]

        if not missing_columns:
            return True, []
        else:
            return False, missing_columns

    except FileNotFoundError:
        return False, [f"File not found at path: {file_path}"]
    except pd.errors.ParserError as e:
        logger.error(f"Parser error validating CSV '{file_path}': {e}", exc_info=True)
        return False, [f"Could not parse file. It might be corrupt or not a valid CSV. Error: {e}"]
    except Exception as e:
        logger.error(f"Unexpected error validating CSV headers for {file_path}: {e}", exc_info=True)
        return False, [f"An unexpected error occurred: {e}"]


def run_full_analysis(
    stock_file_path,
    orders_file_path,
    output_dir_path,
    stock_delimiter,
    config,
    client_id: Optional[str] = None,
    session_manager: Optional[Any] = None,
    profile_manager: Optional[Any] = None,
    session_path: Optional[str] = None
):
    """Orchestrates the entire fulfillment analysis process.

    This function serves as the main entry point for the core analysis logic.
    It performs the following steps:
    1. Loads stock and order data from CSV files.
    2. Validates that the data contains the required columns.
    3. Loads historical fulfillment data.
    4. Runs the fulfillment simulation to determine order statuses.
    5. Applies stock alerts and custom tagging rules.
    6. Saves a detailed analysis report to an Excel file, including summaries.
    7. Updates the fulfillment history with newly fulfilled orders.

    New Session-Based Workflow (when session_manager and client_id are provided):
    1. Creates new session OR uses provided session_path
       - If session_path is None: automatically creates new session
       - If session_path provided: uses existing session (GUI workflow)
    2. Copies input files to session/input/
    3. Saves analysis results to session/analysis/
    4. Exports analysis_data.json for Packing Tool integration
    5. Updates session_info.json with results

    Args:
        stock_file_path (str | None): Path to the stock data CSV file. Can be
            None for testing purposes if a DataFrame is provided in `config`.
        orders_file_path (str | None): Path to the Shopify orders export CSV
            file. Can be None for testing.
        output_dir_path (str): Path to the directory where the output report
            will be saved (legacy mode). Ignored in session mode.
        stock_delimiter (str): The delimiter used in the stock CSV file.
        config (dict): The application configuration dictionary. It can also
            contain test DataFrames under 'test_stock_df' and
            'test_orders_df' keys.
        client_id (str, optional): Client ID for session-based workflow.
        session_manager (SessionManager, optional): Session manager instance.
        profile_manager (ProfileManager, optional): Profile manager instance.
        session_path (str, optional): Path to existing session directory (new workflow).
            If not provided in session mode, a new session will be created automatically.

    Returns:
        tuple[bool, str | None, pd.DataFrame | None, dict | None]:
            A tuple containing:
            - bool: True for success, False for failure.
            - str | None: A message indicating the result. On success, this
              is the path to the output file (or session path). On failure,
              it's an error message.
            - pd.DataFrame | None: The final analysis DataFrame if successful,
              otherwise None.
            - dict | None: A dictionary of calculated statistics if
              successful, otherwise None.
    """
    logger.info("--- Starting Full Analysis Process ---")

    # Determine if using session-based workflow
    use_session_mode = session_manager is not None and client_id is not None

    # Handle session path based on workflow mode
    if use_session_mode:
        # If session_path not provided, create a new session
        if session_path is None:
            try:
                logger.info(f"Creating new session for client: {client_id}")
                session_path = session_manager.create_session(client_id)
                logger.info(f"Session created at: {session_path}")
            except Exception as e:
                error_msg = f"Failed to create session: {e}"
                logger.error(error_msg, exc_info=True)
                return False, error_msg, None, None

        working_path = session_path
        logger.info(f"Using session-based workflow for client: {client_id}")
        logger.info(f"Session path: {working_path}")
    else:
        # Legacy mode: use output_dir_path
        working_path = output_dir_path

    if use_session_mode:
        try:

            # Copy input files to session/input/
            if stock_file_path and orders_file_path:
                input_dir = session_manager.get_input_dir(working_path)

                # Copy with standardized names
                orders_dest = Path(input_dir) / "orders_export.csv"
                stock_dest = Path(input_dir) / "inventory.csv"

                logger.info(f"Copying orders file to: {orders_dest}")
                shutil.copy2(orders_file_path, orders_dest)

                logger.info(f"Copying stock file to: {stock_dest}")
                shutil.copy2(stock_file_path, stock_dest)

                # Update session info with input file names
                session_manager.update_session_info(working_path, {
                    "orders_file": "orders_export.csv",
                    "stock_file": "inventory.csv"
                })

                logger.info("Input files copied to session directory")
        except Exception as e:
            error_msg = f"Failed to setup session: {e}"
            logger.error(error_msg, exc_info=True)
            return False, error_msg, None, None

    # 1. Load data
    logger.info("Step 1: Loading data files...")
    if stock_file_path is not None and orders_file_path is not None:
        # Normalize paths to handle UNC paths from network shares correctly
        stock_file_path = _normalize_unc_path(stock_file_path)
        orders_file_path = _normalize_unc_path(orders_file_path)

        if not os.path.exists(stock_file_path) or not os.path.exists(orders_file_path):
            return False, "One or both input files were not found.", None, None

        # Detect encodings for both files
        stock_encoding = detect_csv_encoding(stock_file_path)
        orders_encoding = detect_csv_encoding(orders_file_path)

        logger.info(f"Reading stock file from normalized path: {stock_file_path}")
        logger.info(f"Using encoding: {stock_encoding}, delimiter: '{stock_delimiter}'")
        stock_df = pd.read_csv(stock_file_path, delimiter=stock_delimiter, encoding=stock_encoding)

        logger.info(f"Reading orders file from normalized path: {orders_file_path}")
        logger.info(f"Using encoding: {orders_encoding}")
        orders_df = pd.read_csv(orders_file_path, encoding=orders_encoding)

        # Apply column mapping if configured (e.g., WooCommerce -> Shopify format)
        if config:
            column_mappings = config.get("column_mappings", {})
            source_platform = column_mappings.get("source_platform", "shopify")
            orders_source_mappings = column_mappings.get("orders_source_mappings", {})
            orders_column_mapping = orders_source_mappings.get(source_platform, {})

            if orders_column_mapping:
                logger.info(f"Applying orders column mapping for platform: {source_platform}")
                orders_df = batch_loader.apply_column_mapping(orders_df, orders_column_mapping)

            # Apply stock column mapping (usually identity mapping for Cyrillic names)
            stock_source_mappings = column_mappings.get("stock_source_mappings", {})
            stock_column_mapping = stock_source_mappings.get("default", {})

            if stock_column_mapping:
                logger.info(f"Applying stock column mapping")
                stock_df = batch_loader.apply_column_mapping(stock_df, stock_column_mapping)
    else:
        # For testing: allow passing DataFrames directly
        stock_df = config.get("test_stock_df")
        orders_df = config.get("test_orders_df")
        history_df = config.get("test_history_df", pd.DataFrame({"Order_Number": []}))
    logger.info("Data loaded successfully.")

    # Validate dataframes
    validation_errors = _validate_dataframes(orders_df, stock_df, config)
    if validation_errors:
        error_message = "\n".join(validation_errors)
        logger.error(f"Validation Error: {error_message}")
        return False, error_message, None, None

    # NEW: Use server-based history storage
    # Determine history file location
    if profile_manager and client_id:
        # Server-based storage in client directory
        client_dir = profile_manager.get_client_directory(client_id)
        history_path = client_dir / "fulfillment_history.csv"
        logger.info(f"Using server-based history: {history_path}")
    else:
        # Fallback to local storage for tests/compatibility
        history_path = get_persistent_data_path("fulfillment_history.csv")
        logger.warning("Using local history fallback (no profile manager)")

    # Load history
    if stock_file_path is not None and orders_file_path is not None:
        try:
            if isinstance(history_path, Path):
                history_path_str = str(history_path)
            else:
                history_path_str = history_path

            history_df = pd.read_csv(history_path_str)
            logger.info(f"Loaded {len(history_df)} records from fulfillment history: {history_path}")
        except FileNotFoundError:
            history_df = pd.DataFrame(columns=["Order_Number", "Execution_Date"])
            logger.info("No history file found. Starting with empty history.")
        except Exception as e:
            logger.error(f"Error loading history: {e}")
            history_df = pd.DataFrame(columns=["Order_Number", "Execution_Date"])

    # 2. Run analysis (computation only)
    logger.info("Step 2: Running fulfillment simulation...")
    final_df, summary_present_df, summary_missing_df, stats = analysis.run_analysis(stock_df, orders_df, history_df)
    logger.info("Analysis computation complete.")

    # Debug logging: Verify DataFrame structure
    logger.debug(f"Analysis result columns: {list(final_df.columns)}")
    logger.debug(f"DataFrame shape: {final_df.shape}")
    if not final_df.empty:
        logger.debug(f"Sample row (first): {final_df.iloc[0].to_dict()}")
    if "Order_Fulfillment_Status" in final_df.columns:
        status_counts = final_df["Order_Fulfillment_Status"].value_counts().to_dict()
        logger.debug(f"Order_Fulfillment_Status distribution: {status_counts}")
    else:
        logger.error("CRITICAL: Order_Fulfillment_Status column is missing from analysis result!")

    # 2.5. Add stock alerts based on config
    low_stock_threshold = config.get("settings", {}).get("low_stock_threshold")
    if low_stock_threshold is not None and "Final_Stock" in final_df.columns:
        logger.info(f"Applying low stock threshold: < {low_stock_threshold}")
        final_df["Stock_Alert"] = np.where(final_df["Final_Stock"] < low_stock_threshold, "Low Stock", "")

    # 2.6. Apply the new rule engine
    rules = config.get("rules", [])
    if rules:
        logger.info("Applying new rule engine...")
        engine = RuleEngine(rules)
        final_df = engine.apply(final_df)
        logger.info("Rule engine application complete.")

    # 3. Save Excel report (skip in test mode)
    if stock_file_path is not None and orders_file_path is not None:
        logger.info("Step 3: Saving analysis report to Excel...")

        # Determine output directory based on mode
        if use_session_mode:
            # Session mode: save to session/analysis/
            analysis_dir = session_manager.get_analysis_dir(working_path)
            output_file_path = str(Path(analysis_dir) / "fulfillment_analysis.xlsx")
            logger.info(f"Session mode: saving to {output_file_path}")
        else:
            # Legacy mode: save to specified output_dir_path
            if not os.path.exists(output_dir_path):
                os.makedirs(output_dir_path)
            output_file_path = os.path.join(output_dir_path, "fulfillment_analysis.xlsx")

        with pd.ExcelWriter(output_file_path, engine="xlsxwriter") as writer:
            final_df.to_excel(writer, sheet_name="fulfillment_analysis", index=False)
            summary_present_df.to_excel(writer, sheet_name="Summary_Present", index=False)
            summary_missing_df.to_excel(writer, sheet_name="Summary_Missing", index=False)

            workbook = writer.book
            report_info_sheet = workbook.add_worksheet("Report Info")
            generation_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            report_info_sheet.write("A1", "Report Generated On:")
            report_info_sheet.write("B1", generation_time)
            report_info_sheet.set_column("A:B", 25)

            worksheet = writer.sheets["fulfillment_analysis"]
            highlight_format = workbook.add_format({"bg_color": "#FFC7CE", "font_color": "#9C0006"})
            for idx, col in enumerate(final_df):
                max_len = max((final_df[col].astype(str).map(len).max(), len(str(col)))) + 2
                worksheet.set_column(idx, idx, max_len)
            for row_num, status in enumerate(final_df["Order_Fulfillment_Status"]):
                if status == "Not Fulfillable":
                    worksheet.set_row(row_num + 1, None, highlight_format)
        logger.info(f"Excel report saved to '{output_file_path}'")

        # 3.5. Session mode: Export analysis_data.json and update session_info
        if use_session_mode:
            try:
                logger.info("Exporting analysis_data.json for Packing Tool integration...")
                analysis_data = _create_analysis_data_for_packing(final_df)

                # Save analysis_data.json
                analysis_data_path = Path(analysis_dir) / "analysis_data.json"
                with open(analysis_data_path, 'w', encoding='utf-8') as f:
                    json.dump(analysis_data, f, indent=2, ensure_ascii=False)

                logger.info(f"analysis_data.json saved to: {analysis_data_path}")

                # Update session_info.json with analysis results
                session_manager.update_session_info(working_path, {
                    "analysis_completed": True,
                    "analysis_completed_at": datetime.now().isoformat(),
                    "total_orders": analysis_data["total_orders"],
                    "fulfillable_orders": analysis_data["fulfillable_orders"],
                    "not_fulfillable_orders": analysis_data["not_fulfillable_orders"],
                    "analysis_report_path": "analysis/analysis_report.xlsx"
                })

                logger.info("Session info updated with analysis results")

            except Exception as e:
                logger.error(f"Failed to export analysis data: {e}", exc_info=True)
                # Continue with the workflow even if export fails

        # 4. Update history
        logger.info("Step 4: Updating fulfillment history...")
        newly_fulfilled = final_df[final_df["Order_Fulfillment_Status"] == "Fulfillable"][
            ["Order_Number"]
        ].drop_duplicates()
        if not newly_fulfilled.empty:
            newly_fulfilled["Execution_Date"] = datetime.now().strftime("%Y-%m-%d")
            updated_history = pd.concat([history_df, newly_fulfilled]).drop_duplicates(
                subset=["Order_Number"], keep="last"
            )

            # Save updated history (path already determined above)
            try:
                # Ensure parent directory exists
                if isinstance(history_path, Path):
                    history_path.parent.mkdir(parents=True, exist_ok=True)
                    history_path_str = str(history_path)
                else:
                    history_path_str = history_path
                    # Create parent directory if needed
                    parent_dir = os.path.dirname(history_path_str)
                    if parent_dir:
                        os.makedirs(parent_dir, exist_ok=True)

                updated_history.to_csv(history_path_str, index=False)
                logger.info(f"History updated and saved to: {history_path} ({len(newly_fulfilled)} new records)")
            except Exception as e:
                logger.error(f"Failed to save history: {e}")
                # Don't fail the entire analysis if history save fails

        # Return appropriate path based on mode
        if use_session_mode:
            return True, working_path, final_df, stats
        else:
            return True, output_file_path, final_df, stats
    else:
        # For tests, just return the DataFrames
        return True, None, final_df, stats


def create_packing_list_report(
    analysis_df,
    report_config,
    session_manager: Optional[Any] = None,
    session_path: Optional[str] = None
):
    """Generates a single packing list report based on a report configuration.

    Uses the provided analysis DataFrame and a specific report configuration
    to filter and format a packing list. The resulting report is saved to the
    location specified in the configuration.

    Session Mode: When session_manager and session_path are provided, the report
    is saved to the session's packing_lists/ directory and session_info is updated.

    Args:
        analysis_df (pd.DataFrame): The main analysis DataFrame containing
            fulfillment data.
        report_config (dict): A dictionary from the main config file that
            defines the filters, output filename, excluded SKUs, and other
            settings for this specific report.
        session_manager (SessionManager, optional): Session manager for session-based workflow.
        session_path (str, optional): Path to current session directory.

    Returns:
        tuple[bool, str]: A tuple containing:
            - bool: True for success, False for failure.
            - str: A message indicating the result (e.g., success message with
              file path or an error description).
    """
    report_name = report_config.get("name", "Unknown Report")
    try:
        # Determine output path based on mode
        if session_manager and session_path:
            # Session mode: save to session/packing_lists/
            packing_lists_dir = session_manager.get_packing_lists_dir(session_path)
            # Extract just the filename from the configured path
            original_filename = os.path.basename(report_config["output_filename"])
            output_file = str(Path(packing_lists_dir) / original_filename)
            logger.info(f"Session mode: saving packing list to {output_file}")
        else:
            # Legacy mode: use configured path
            output_file = report_config["output_filename"]
            os.makedirs(os.path.dirname(output_file), exist_ok=True)

        packing_lists.create_packing_list(
            analysis_df=analysis_df,
            output_file=output_file,
            report_name=report_name,
            filters=report_config.get("filters"),
            exclude_skus=report_config.get("exclude_skus"),  # Pass the new parameter
        )

        # Verify file was actually created before updating session info
        if not os.path.exists(output_file):
            error_message = f"Packing list file was not created: {output_file}"
            logger.error(error_message)
            return False, error_message

        # Update session info if in session mode
        if session_manager and session_path:
            try:
                session_info = session_manager.get_session_info(session_path)
                generated_lists = session_info.get("packing_lists_generated", [])
                if original_filename not in generated_lists:
                    generated_lists.append(original_filename)
                    session_manager.update_session_info(session_path, {
                        "packing_lists_generated": generated_lists
                    })
                    logger.info(f"Session info updated: added packing list {original_filename}")
            except Exception as e:
                logger.warning(f"Failed to update session info: {e}")

        success_message = f"Report '{report_name}' created successfully at '{output_file}'."
        return True, success_message
    except KeyError as e:
        error_message = f"Configuration error for report '{report_name}': Missing key {e}."
        logger.error(f"Config error for packing list '{report_name}': {e}", exc_info=True)
        return False, error_message
    except PermissionError:
        output_filename = report_config.get('output_filename', 'N/A')
        error_message = f"Permission denied. Could not write report to '{output_filename}'."
        logger.error(
            f"Permission error creating packing list '{report_name}' at '{output_filename}'", exc_info=True
        )
        return False, error_message
    except Exception as e:
        error_message = f"Failed to create report '{report_name}'. See logs/app_errors.log for details."
        logger.error(f"Error creating packing list '{report_name}': {e}", exc_info=True)
        return False, error_message


def get_unique_column_values(df, column_name):
    """Extracts unique, sorted, non-null values from a DataFrame column.

    Args:
        df (pd.DataFrame): The DataFrame to extract values from.
        column_name (str): The name of the column to get unique values from.

    Returns:
        list[str]: A sorted list of unique string-converted values, or an
                   empty list if the column doesn't exist or an error occurs.
    """
    if df.empty or column_name not in df.columns:
        return []
    try:
        unique_values = df[column_name].dropna().unique().tolist()
        return sorted([str(v) for v in unique_values])
    except Exception:
        return []


def create_stock_export_report(
    analysis_df,
    report_config,
    session_manager: Optional[Any] = None,
    session_path: Optional[str] = None
):
    """Generates a single stock export report based on a configuration.

    Session Mode: When session_manager and session_path are provided, the report
    is saved to the session's stock_exports/ directory and session_info is updated.

    Args:
        analysis_df (pd.DataFrame): The main analysis DataFrame.
        report_config (dict): The configuration for the specific stock export.
        session_manager (SessionManager, optional): Session manager for session-based workflow.
        session_path (str, optional): Path to current session directory.

    Returns:
        tuple[bool, str]: A tuple containing a success flag and a status message.
    """
    report_name = report_config.get("name", "Untitled Stock Export")
    try:
        # Determine output path based on mode
        if session_manager and session_path:
            # Session mode: save to session/stock_exports/
            stock_exports_dir = session_manager.get_stock_exports_dir(session_path)
            # Extract just the filename from the configured path
            original_filename = os.path.basename(report_config["output_filename"])
            output_filename = str(Path(stock_exports_dir) / original_filename)
            logger.info(f"Session mode: saving stock export to {output_filename}")
        else:
            # Legacy mode: use configured path
            output_filename = report_config["output_filename"]
            # Ensure the output directory exists
            output_dir = os.path.dirname(output_filename)
            if not os.path.exists(output_dir):
                os.makedirs(output_dir)

        filters = report_config.get("filters")

        stock_export.create_stock_export(
            analysis_df,
            output_filename,
            report_name=report_name,
            filters=filters,
        )

        # Verify file was actually created before updating session info
        if not os.path.exists(output_filename):
            error_message = f"Stock export file was not created: {output_filename}"
            logger.error(error_message)
            return False, error_message

        # Update session info if in session mode
        if session_manager and session_path:
            try:
                session_info = session_manager.get_session_info(session_path)
                generated_exports = session_info.get("stock_exports_generated", [])
                if original_filename not in generated_exports:
                    generated_exports.append(original_filename)
                    session_manager.update_session_info(session_path, {
                        "stock_exports_generated": generated_exports
                    })
                    logger.info(f"Session info updated: added stock export {original_filename}")
            except Exception as e:
                logger.warning(f"Failed to update session info: {e}")

        success_message = f"Stock export '{report_name}' created successfully at '{output_filename}'."
        return True, success_message
    except KeyError as e:
        error_message = f"Configuration error for stock export '{report_name}': Missing key {e}."
        logger.error(f"Config error for stock export '{report_name}': {e}", exc_info=True)
        return False, error_message
    except PermissionError:
        error_message = "Permission denied. Could not write stock export."
        logger.error(f"Permission error creating stock export '{report_name}'", exc_info=True)
        return False, error_message
    except Exception as e:
        error_message = f"Failed to create stock export '{report_name}'. See logs for details."
        logger.error(f"Error creating stock export '{report_name}': {e}", exc_info=True)
        return False, error_message
