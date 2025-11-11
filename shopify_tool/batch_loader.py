"""
Batch CSV loader for loading and merging multiple CSV files from a folder.
"""

import logging
from pathlib import Path
from typing import List, Dict, Tuple, Optional
import pandas as pd

logger = logging.getLogger(__name__)


def apply_column_mapping(df: pd.DataFrame, column_mapping: Optional[Dict[str, str]]) -> pd.DataFrame:
    """
    Apply column name mapping to a DataFrame.

    This converts source column names (e.g., WooCommerce "Order ID") to
    target column names (e.g., Shopify "Name") that the analysis code expects.

    Args:
        df: DataFrame to apply mapping to
        column_mapping: Dictionary mapping source column names to target names
                       Example: {"Order ID": "Name", "Lineitem sku": "Lineitem sku"}

    Returns:
        DataFrame with renamed columns
    """
    if not column_mapping:
        logger.debug("No column mapping provided, returning DataFrame as-is")
        return df

    # Only rename columns that exist in the DataFrame
    rename_dict = {
        source: target
        for source, target in column_mapping.items()
        if source in df.columns and source != target
    }

    if rename_dict:
        logger.info(f"Applying column mapping: {rename_dict}")
        df = df.rename(columns=rename_dict)
    else:
        logger.debug("No columns to rename (all source columns already match target)")

    return df


class BatchLoaderResult:
    """Result object for batch loading operations."""

    def __init__(
        self,
        df: pd.DataFrame,
        files_count: int,
        total_orders: int,
        duplicates_removed: int,
        files_loaded: List[str]
    ):
        self.df = df
        self.files_count = files_count
        self.total_orders = total_orders
        self.duplicates_removed = duplicates_removed
        self.files_loaded = files_loaded

    def get_summary(self) -> str:
        """Get a summary string of the batch loading operation."""
        summary = [
            f"Files loaded: {self.files_count}",
            f"Total orders: {self.total_orders}",
            f"Duplicates removed: {self.duplicates_removed}"
        ]
        return "\n".join(summary)


def discover_csv_files(folder_path: Path) -> List[Path]:
    """
    Discover all CSV files in the given folder.

    Args:
        folder_path: Path to the folder to search

    Returns:
        List of Path objects for CSV files found

    Raises:
        ValueError: If folder_path is not a directory
    """
    if not folder_path.is_dir():
        raise ValueError(f"Path is not a directory: {folder_path}")

    csv_files = sorted(folder_path.glob("*.csv"))
    logger.info(f"Found {len(csv_files)} CSV files in {folder_path}")

    return csv_files


def validate_csv_structure(
    csv_files: List[Path],
    required_columns: List[str],
    delimiter: str = ",",
    encoding: str = "utf-8"
) -> Tuple[bool, Optional[str]]:
    """
    Validate that all CSV files have the same structure and required columns.

    Args:
        csv_files: List of CSV file paths to validate
        required_columns: List of required column names
        delimiter: CSV delimiter (default: comma)
        encoding: File encoding (default: utf-8)

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not csv_files:
        return False, "No CSV files found"

    # Read headers from first file
    try:
        first_headers = pd.read_csv(csv_files[0], nrows=0, delimiter=delimiter, encoding=encoding).columns.tolist()
    except Exception as e:
        return False, f"Error reading first file {csv_files[0].name}: {str(e)}"

    # Check if first file has all required columns
    missing_cols = [col for col in required_columns if col not in first_headers]
    if missing_cols:
        return False, f"File {csv_files[0].name} missing required columns: {', '.join(missing_cols)}"

    # Check that all other files have the same columns
    for csv_file in csv_files[1:]:
        try:
            headers = pd.read_csv(csv_file, nrows=0, delimiter=delimiter, encoding=encoding).columns.tolist()
        except Exception as e:
            return False, f"Error reading file {csv_file.name}: {str(e)}"

        if headers != first_headers:
            return False, f"File {csv_file.name} has different structure than {csv_files[0].name}"

    logger.info(f"All {len(csv_files)} files have matching structure")
    return True, None


def load_and_merge_csvs(
    csv_files: List[Path],
    order_number_column: str = "Order_Number",
    delimiter: str = ",",
    encoding: str = "utf-8",
    column_mapping: Optional[Dict[str, str]] = None
) -> BatchLoaderResult:
    """
    Load multiple CSV files and merge them into a single DataFrame.

    Args:
        csv_files: List of CSV file paths to load
        order_number_column: Column name for order number (for deduplication)
        delimiter: CSV delimiter (default: comma)
        encoding: File encoding (default: utf-8)
        column_mapping: Optional dictionary to map source column names to target names
                       Example: {"Order ID": "Name"} converts WooCommerce to Shopify format

    Returns:
        BatchLoaderResult object with merged DataFrame and statistics

    Raises:
        ValueError: If no CSV files provided or loading fails
    """
    if not csv_files:
        raise ValueError("No CSV files provided")

    logger.info(f"Loading {len(csv_files)} CSV files...")

    dataframes = []
    files_loaded = []

    for csv_file in csv_files:
        try:
            df = pd.read_csv(csv_file, delimiter=delimiter, encoding=encoding)
            dataframes.append(df)
            files_loaded.append(csv_file.name)
            logger.info(f"Loaded {len(df)} rows from {csv_file.name}")
        except Exception as e:
            logger.error(f"Error loading file {csv_file.name}: {str(e)}")
            raise ValueError(f"Failed to load file {csv_file.name}: {str(e)}")

    # Merge all dataframes
    merged_df = pd.concat(dataframes, ignore_index=True)
    total_rows_before = len(merged_df)

    logger.info(f"Merged {len(dataframes)} files into {total_rows_before} total rows")

    # Apply column mapping if provided (e.g., WooCommerce -> Shopify format)
    if column_mapping:
        merged_df = apply_column_mapping(merged_df, column_mapping)

    # Remove duplicates by Order_Number
    duplicates_removed = 0
    if order_number_column in merged_df.columns:
        merged_df_deduplicated = merged_df.drop_duplicates(subset=[order_number_column], keep='first')
        duplicates_removed = total_rows_before - len(merged_df_deduplicated)

        if duplicates_removed > 0:
            logger.warning(f"Removed {duplicates_removed} duplicate orders based on {order_number_column}")

        merged_df = merged_df_deduplicated
    else:
        logger.warning(f"Column {order_number_column} not found, skipping deduplication")

    total_orders = len(merged_df)

    result = BatchLoaderResult(
        df=merged_df,
        files_count=len(csv_files),
        total_orders=total_orders,
        duplicates_removed=duplicates_removed,
        files_loaded=files_loaded
    )

    logger.info(f"Batch loading complete: {result.get_summary()}")

    return result


def load_orders_from_folder(
    folder_path: Path,
    required_columns: List[str],
    order_number_column: str = "Order_Number",
    delimiter: str = ",",
    encoding: str = "utf-8",
    column_mapping: Optional[Dict[str, str]] = None
) -> BatchLoaderResult:
    """
    Complete workflow for loading orders from a folder of CSV files.

    This is the main entry point for batch loading:
    1. Discover all CSV files in the folder
    2. Validate that all files have the same structure
    3. Load and merge all files
    4. Apply column mapping (e.g., WooCommerce -> Shopify format)
    5. Deduplicate by Order_Number
    6. Return summary statistics

    Args:
        folder_path: Path to folder containing CSV files
        required_columns: List of required column names (in SOURCE format, before mapping)
        order_number_column: Column name for order number (for deduplication, in TARGET format after mapping)
        delimiter: CSV delimiter (default: comma)
        encoding: File encoding (default: utf-8)
        column_mapping: Optional dictionary to map source column names to target names
                       Example: {"Order ID": "Name"} converts WooCommerce to Shopify format

    Returns:
        BatchLoaderResult object with merged DataFrame and statistics

    Raises:
        ValueError: If validation fails or loading fails
    """
    logger.info(f"Starting batch load from folder: {folder_path}")

    # Step 1: Discover CSV files
    csv_files = discover_csv_files(folder_path)

    if not csv_files:
        raise ValueError(f"No CSV files found in folder: {folder_path}")

    # Step 2: Validate structure
    is_valid, error_message = validate_csv_structure(csv_files, required_columns, delimiter, encoding)

    if not is_valid:
        raise ValueError(f"CSV validation failed: {error_message}")

    # Step 3: Load and merge
    result = load_and_merge_csvs(csv_files, order_number_column, delimiter, encoding, column_mapping)

    return result
