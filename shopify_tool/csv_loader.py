"""CSV Loader module for handling single and multiple CSV file imports.

This module provides functionality to:
- Load single CSV files
- Load and merge multiple CSV files from a folder
- Auto-detect CSV delimiters
- Detect and map columns for different export types (WooCommerce, Shopify)
- Validate CSV structure
- Remove duplicates with warnings

Author: Shopify Fulfillment Tool Team
"""

import logging
import csv
from pathlib import Path
from typing import List, Tuple, Dict, Optional, Set
import pandas as pd

logger = logging.getLogger("ShopifyToolLogger")


class CSVLoadResult:
    """Result object for CSV loading operations."""

    def __init__(self):
        self.success: bool = False
        self.dataframe: Optional[pd.DataFrame] = None
        self.files_processed: int = 0
        self.total_orders: int = 0
        self.duplicates_removed: int = 0
        self.warnings: List[str] = []
        self.errors: List[str] = []
        self.detected_format: Optional[str] = None  # "shopify" or "woocommerce"
        self.delimiter: str = ","

    def add_warning(self, message: str):
        """Add a warning message."""
        self.warnings.append(message)
        logger.warning(message)

    def add_error(self, message: str):
        """Add an error message."""
        self.errors.append(message)
        logger.error(message)

    def get_summary(self) -> str:
        """Get a formatted summary of the load operation."""
        lines = []
        if self.success:
            lines.append(f"✓ Successfully loaded {self.files_processed} file(s)")
            lines.append(f"  Total orders: {self.total_orders}")
            if self.duplicates_removed > 0:
                lines.append(f"  ⚠ Duplicates removed: {self.duplicates_removed}")
            if self.detected_format:
                lines.append(f"  Detected format: {self.detected_format.upper()}")
        else:
            lines.append("✗ Failed to load CSV file(s)")

        if self.warnings:
            lines.append(f"\nWarnings ({len(self.warnings)}):")
            for w in self.warnings:
                lines.append(f"  • {w}")

        if self.errors:
            lines.append(f"\nErrors ({len(self.errors)}):")
            for e in self.errors:
                lines.append(f"  • {e}")

        return "\n".join(lines)


# Column mapping configurations for different export types
COLUMN_MAPPINGS = {
    "woocommerce": {
        "order_id": "Order ID",
        "sku": "Lineitem sku",
        "product_name": "Lineitem name",
        "quantity": "Lineitem quantity",
        "shipping_method": "Shipping Method"
    },
    "shopify": {
        "order_id": "Name",
        "sku": "Lineitem sku",
        "product_name": "Lineitem name",
        "quantity": "Lineitem quantity",
        "shipping_method": "Shipping Method"
    }
}

# Standard column names used internally
STANDARD_COLUMNS = {
    "order_id": "Order_Number",
    "sku": "SKU",
    "product_name": "Product_Name",
    "quantity": "Quantity",
    "shipping_method": "Shipping_Method"
}


def detect_csv_delimiter(file_path: Path, sample_size: int = 5) -> str:
    """Auto-detect CSV delimiter by analyzing the first few lines.

    Args:
        file_path: Path to CSV file
        sample_size: Number of lines to sample for detection

    Returns:
        Detected delimiter character (default: ',')
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            # Read sample lines
            sample_lines = []
            for i, line in enumerate(f):
                if i >= sample_size:
                    break
                sample_lines.append(line)

            if not sample_lines:
                logger.warning(f"Empty file: {file_path}")
                return ','

            # Use CSV Sniffer to detect delimiter
            sample = '\n'.join(sample_lines)
            sniffer = csv.Sniffer()

            try:
                dialect = sniffer.sniff(sample, delimiters=',;\t|')
                delimiter = dialect.delimiter
                logger.info(f"Detected delimiter '{delimiter}' for {file_path.name}")
                return delimiter
            except csv.Error:
                # If sniffer fails, count common delimiters
                delimiters = {',': 0, ';': 0, '\t': 0, '|': 0}
                for line in sample_lines:
                    for delim in delimiters:
                        delimiters[delim] += line.count(delim)

                # Return delimiter with highest count
                detected = max(delimiters, key=delimiters.get)
                if delimiters[detected] > 0:
                    logger.info(f"Detected delimiter '{detected}' (fallback method) for {file_path.name}")
                    return detected

                # Default to comma
                logger.warning(f"Could not detect delimiter for {file_path.name}, using ','")
                return ','

    except Exception as e:
        logger.error(f"Error detecting delimiter for {file_path}: {e}")
        return ','


def detect_export_format(df: pd.DataFrame) -> Optional[str]:
    """Detect if CSV is from WooCommerce or Shopify based on columns.

    Args:
        df: DataFrame to analyze

    Returns:
        "woocommerce", "shopify", or None if unknown
    """
    columns = set(df.columns)

    # Check for WooCommerce signature column
    if "Order ID" in columns:
        logger.info("Detected WooCommerce export format (has 'Order ID' column)")
        return "woocommerce"

    # Check for Shopify signature column
    if "Name" in columns and "Lineitem sku" in columns:
        logger.info("Detected Shopify export format (has 'Name' column)")
        return "shopify"

    logger.warning("Could not detect export format - unknown column structure")
    return None


def normalize_columns(df: pd.DataFrame, export_format: str) -> pd.DataFrame:
    """Normalize column names to standard internal names.

    Args:
        df: DataFrame with original column names
        export_format: "woocommerce" or "shopify"

    Returns:
        DataFrame with normalized column names
    """
    if export_format not in COLUMN_MAPPINGS:
        logger.warning(f"Unknown export format: {export_format}")
        return df

    mapping = COLUMN_MAPPINGS[export_format]
    rename_dict = {}

    for standard_name, original_name in mapping.items():
        if original_name in df.columns:
            target_name = STANDARD_COLUMNS.get(standard_name, original_name)
            rename_dict[original_name] = target_name

    if rename_dict:
        df = df.rename(columns=rename_dict)
        logger.info(f"Normalized columns: {list(rename_dict.keys())} -> {list(rename_dict.values())}")

    return df


def validate_csv_structure(files_data: List[Tuple[Path, pd.DataFrame]]) -> Tuple[bool, List[str]]:
    """Validate that all CSV files have compatible structure.

    Args:
        files_data: List of tuples (file_path, dataframe)

    Returns:
        Tuple of (is_valid, error_messages)
    """
    if not files_data:
        return False, ["No files to validate"]

    errors = []

    # Get reference columns from first file
    reference_path, reference_df = files_data[0]
    reference_cols = set(reference_df.columns)

    # Check all other files have same columns
    for file_path, df in files_data[1:]:
        current_cols = set(df.columns)

        if current_cols != reference_cols:
            missing = reference_cols - current_cols
            extra = current_cols - reference_cols

            error_msg = f"Column mismatch in {file_path.name}:"
            if missing:
                error_msg += f"\n  Missing: {', '.join(missing)}"
            if extra:
                error_msg += f"\n  Extra: {', '.join(extra)}"
            errors.append(error_msg)

    is_valid = len(errors) == 0
    return is_valid, errors


def remove_duplicates(df: pd.DataFrame, order_column: str = "Order_Number") -> Tuple[pd.DataFrame, int]:
    """Remove duplicate orders and return count.

    Args:
        df: DataFrame with potential duplicates
        order_column: Name of order number column

    Returns:
        Tuple of (deduplicated_dataframe, num_duplicates_removed)
    """
    if order_column not in df.columns:
        logger.warning(f"Order column '{order_column}' not found, skipping deduplication")
        return df, 0

    original_count = len(df)

    # Keep first occurrence of each order
    df_dedup = df.drop_duplicates(subset=[order_column], keep='first')

    duplicates_removed = original_count - len(df_dedup)

    if duplicates_removed > 0:
        logger.warning(f"Removed {duplicates_removed} duplicate orders")

    return df_dedup, duplicates_removed


def load_single_csv(file_path: Path, delimiter: Optional[str] = None) -> CSVLoadResult:
    """Load a single CSV file with auto-detection and normalization.

    Args:
        file_path: Path to CSV file
        delimiter: Optional delimiter (will auto-detect if None)

    Returns:
        CSVLoadResult object with loaded data and metadata
    """
    result = CSVLoadResult()

    try:
        # Auto-detect delimiter if not provided
        if delimiter is None:
            delimiter = detect_csv_delimiter(file_path)
        result.delimiter = delimiter

        # Load CSV
        logger.info(f"Loading CSV: {file_path}")
        df = pd.read_csv(file_path, delimiter=delimiter)

        if df.empty:
            result.add_error(f"File is empty: {file_path.name}")
            return result

        # Detect export format
        export_format = detect_export_format(df)
        result.detected_format = export_format

        if export_format:
            # Normalize columns
            df = normalize_columns(df, export_format)
        else:
            result.add_warning(f"Could not detect export format for {file_path.name}")

        # Remove duplicates
        df, duplicates = remove_duplicates(df)
        result.duplicates_removed = duplicates

        # Set result
        result.success = True
        result.dataframe = df
        result.files_processed = 1
        result.total_orders = len(df)

        logger.info(f"Successfully loaded {file_path.name}: {len(df)} rows")

    except FileNotFoundError:
        result.add_error(f"File not found: {file_path}")
    except pd.errors.EmptyDataError:
        result.add_error(f"File is empty or contains no data: {file_path.name}")
    except pd.errors.ParserError as e:
        result.add_error(f"Failed to parse CSV {file_path.name}: {str(e)}")
    except Exception as e:
        result.add_error(f"Unexpected error loading {file_path.name}: {str(e)}")
        logger.exception(e)

    return result


def load_orders_from_folder(folder_path: Path, delimiter: Optional[str] = None) -> CSVLoadResult:
    """Load and merge all CSV files from a folder.

    This function:
    1. Finds all .csv files in the folder
    2. Loads each file with auto-detection
    3. Validates they have compatible structure
    4. Merges them into a single DataFrame
    5. Removes duplicates by Order_Number
    6. Returns summary with warnings

    Args:
        folder_path: Path to folder containing CSV files
        delimiter: Optional delimiter (will auto-detect if None)

    Returns:
        CSVLoadResult object with merged data and metadata
    """
    result = CSVLoadResult()

    try:
        folder_path = Path(folder_path)

        if not folder_path.exists():
            result.add_error(f"Folder not found: {folder_path}")
            return result

        if not folder_path.is_dir():
            result.add_error(f"Path is not a folder: {folder_path}")
            return result

        # Find all CSV files
        csv_files = sorted(folder_path.glob("*.csv"))

        if not csv_files:
            result.add_error(f"No CSV files found in folder: {folder_path}")
            return result

        logger.info(f"Found {len(csv_files)} CSV file(s) in {folder_path}")

        # Load all files
        files_data = []
        detected_formats = []
        all_duplicates = 0

        for csv_file in csv_files:
            file_result = load_single_csv(csv_file, delimiter)

            if not file_result.success:
                # Propagate errors
                result.errors.extend(file_result.errors)
                result.warnings.extend(file_result.warnings)
                continue

            files_data.append((csv_file, file_result.dataframe))
            if file_result.detected_format:
                detected_formats.append(file_result.detected_format)
            all_duplicates += file_result.duplicates_removed

            # Propagate warnings
            result.warnings.extend(file_result.warnings)

        if not files_data:
            result.add_error("Failed to load any CSV files")
            return result

        # Validate structure compatibility
        is_valid, validation_errors = validate_csv_structure(files_data)

        if not is_valid:
            result.errors.extend(validation_errors)
            return result

        # Determine dominant format
        if detected_formats:
            # Count occurrences
            format_counts = {}
            for fmt in detected_formats:
                format_counts[fmt] = format_counts.get(fmt, 0) + 1
            result.detected_format = max(format_counts, key=format_counts.get)

        # Merge all DataFrames
        logger.info(f"Merging {len(files_data)} file(s)...")
        dfs = [df for _, df in files_data]
        merged_df = pd.concat(dfs, ignore_index=True)

        logger.info(f"Merged result: {len(merged_df)} total rows")

        # Remove duplicates across all files
        merged_df, cross_file_duplicates = remove_duplicates(merged_df)
        total_duplicates = all_duplicates + cross_file_duplicates

        if cross_file_duplicates > 0:
            result.add_warning(
                f"Found {cross_file_duplicates} duplicate orders across different files"
            )

        # Set success result
        result.success = True
        result.dataframe = merged_df
        result.files_processed = len(files_data)
        result.total_orders = len(merged_df)
        result.duplicates_removed = total_duplicates

        logger.info(f"Successfully merged {len(files_data)} file(s): {len(merged_df)} unique orders")

    except Exception as e:
        result.add_error(f"Unexpected error processing folder: {str(e)}")
        logger.exception(e)

    return result


def get_csv_preview(file_path: Path, num_rows: int = 5) -> Optional[pd.DataFrame]:
    """Get a preview of CSV file (first N rows).

    Args:
        file_path: Path to CSV file
        num_rows: Number of rows to preview

    Returns:
        DataFrame with preview data or None on error
    """
    try:
        delimiter = detect_csv_delimiter(file_path)
        df = pd.read_csv(file_path, delimiter=delimiter, nrows=num_rows)
        return df
    except Exception as e:
        logger.error(f"Failed to get preview for {file_path}: {e}")
        return None
