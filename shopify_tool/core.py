import os
import logging
import pandas as pd
from datetime import datetime
from . import analysis, packing_lists, stock_export
from .rules import RuleEngine
import numpy as np

logger = logging.getLogger('ShopifyToolLogger')

def _validate_dataframes(orders_df, stock_df, config):
    """
    Validates that the required columns are present in the dataframes.
    Returns a list of error messages. If the list is empty, validation passed.
    """
    errors = []
    column_mappings = config.get('column_mappings', {})
    required_orders_cols = column_mappings.get('orders_required', [])
    required_stock_cols = column_mappings.get('stock_required', [])

    for col in required_orders_cols:
        if col not in orders_df.columns:
            errors.append(f"Missing required column in Orders file: '{col}'")

    for col in required_stock_cols:
        if col not in stock_df.columns:
            errors.append(f"Missing required column in Stock file: '{col}'")

    return errors

def validate_csv_headers(file_path, required_columns, delimiter=','):
    """
    Quickly validates if a CSV file contains the required column headers.

    Args:
        file_path (str): The path to the CSV file.
        required_columns (list): A list of column names that must be present.
        delimiter (str): The delimiter used in the CSV file.

    Returns:
        tuple: A tuple containing:
            - bool: True if all required columns are present, False otherwise.
            - list: A list of missing columns. An empty list if all are present.
    """
    if not required_columns:
        return True, []

    try:
        headers = pd.read_csv(file_path, nrows=0, delimiter=delimiter).columns.tolist()
        missing_columns = [col for col in required_columns if col not in headers]

        if not missing_columns:
            return True, []
        else:
            return False, missing_columns

    except FileNotFoundError:
        return False, ["File not found."]
    except Exception as e:
        logger.error(f"Error validating CSV headers for {file_path}: {e}")
        return False, [f"An unexpected error occurred: {e}"]

def run_full_analysis(stock_file_path, orders_file_path, output_dir_path, stock_delimiter, config):
    """
    Orchestrates the entire fulfillment analysis process.
    """
    logger.info("--- Starting Full Analysis Process ---")
    # 1. Load data
    logger.info("Step 1: Loading data files...")
    if stock_file_path is not None and orders_file_path is not None:
        if not os.path.exists(stock_file_path) or not os.path.exists(orders_file_path):
            return False, "One or both input files were not found.", None, None
        stock_df = pd.read_csv(stock_file_path, delimiter=stock_delimiter)
        orders_df = pd.read_csv(orders_file_path)
    else:
        # For testing: allow passing DataFrames directly
        stock_df = config.get('test_stock_df')
        orders_df = config.get('test_orders_df')
        history_df = config.get('test_history_df', pd.DataFrame({'Order_Number': []}))
    logger.info("Data loaded successfully.")

    # Validate dataframes
    validation_errors = _validate_dataframes(orders_df, stock_df, config)
    if validation_errors:
        error_message = "\n".join(validation_errors)
        logger.error(f"Validation Error: {error_message}")
        return False, error_message, None, None

    history_path = 'fulfillment_history.csv'
    if stock_file_path is not None and orders_file_path is not None:
        try:
            history_df = pd.read_csv(history_path)
            logger.info(f"Loaded {len(history_df)} records from fulfillment history.")
        except FileNotFoundError:
            history_df = pd.DataFrame(columns=['Order_Number', 'Execution_Date'])
            logger.warning("Fulfillment history not found. A new one will be created.")

    # 2. Run analysis (computation only)
    logger.info("Step 2: Running fulfillment simulation...")
    final_df, summary_present_df, summary_missing_df, stats = analysis.run_analysis(
        stock_df, orders_df, history_df
    )
    logger.info("Analysis computation complete.")

    # 2.5. Add stock alerts based on config
    low_stock_threshold = config.get('settings', {}).get('low_stock_threshold')
    if low_stock_threshold is not None and 'Final_Stock' in final_df.columns:
        logger.info(f"Applying low stock threshold: < {low_stock_threshold}")
        final_df['Stock_Alert'] = np.where(
            final_df['Final_Stock'] < low_stock_threshold,
            'Low Stock',
            ''
        )

    # 2.6. Apply the new rule engine
    rules = config.get('rules', [])
    if rules:
        logger.info("Applying new rule engine...")
        engine = RuleEngine(rules)
        final_df = engine.apply(final_df)
        logger.info("Rule engine application complete.")

    # 3. Save Excel report (skip in test mode)
    if stock_file_path is not None and orders_file_path is not None:
        logger.info("Step 3: Saving analysis report to Excel...")
        if not os.path.exists(output_dir_path):
            os.makedirs(output_dir_path)
        output_file_path = os.path.join(output_dir_path, "fulfillment_analysis.xlsx")

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
        logger.info(f"Excel report saved to '{output_file_path}'")

        # 4. Update history
        logger.info("Step 4: Updating fulfillment history...")
        newly_fulfilled = final_df[final_df['Order_Fulfillment_Status'] == 'Fulfillable'][['Order_Number']].drop_duplicates()
        if not newly_fulfilled.empty:
            newly_fulfilled['Execution_Date'] = datetime.now().strftime("%Y-%m-%d")
            updated_history = pd.concat([history_df, newly_fulfilled]).drop_duplicates(subset=['Order_Number'], keep='last')
            updated_history.to_csv(history_path, index=False)
            logger.info(f"Updated fulfillment history with {len(newly_fulfilled)} new records.")
        return True, output_file_path, final_df, stats
    else:
        # For tests, just return the DataFrames
        return True, None, final_df, stats

def create_packing_list_report(analysis_df, report_config):
    """
    Generates a single packing list report based on a report configuration.
    """
    report_name = report_config.get('name', 'Unknown Report')
    try:
        output_file = report_config['output_filename']
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        
        packing_lists.create_packing_list(
            analysis_df=analysis_df,
            output_file=output_file,
            report_name=report_name,
            filters=report_config.get('filters'),
            exclude_skus=report_config.get('exclude_skus')
        )
        success_message = f"Report '{report_name}' created successfully at '{output_file}'."
        return True, success_message
    except Exception as e:
        error_message = f"Failed to create report '{report_name}'. See logs/app_errors.log for details."
        logger.error(f"Error creating packing list '{report_name}': {e}", exc_info=True)
        return False, error_message

def create_stock_export_report(analysis_df, report_config, templates_path, output_path):
    """
    Generates a single stock export report based on a template and report configuration.
    """
    report_name = report_config.get('name', 'Unknown Report')
    try:
        template_name = report_config['template']
        template_full_path = os.path.join(templates_path, template_name)
        
        datestamp = datetime.now().strftime("%Y-%m-%d")
        name, ext = os.path.splitext(template_name)
        output_filename = f"{name}_{datestamp}{ext}"
        
        os.makedirs(output_path, exist_ok=True)
        output_full_path = os.path.join(output_path, output_filename)

        stock_export.create_stock_export(
            analysis_df=analysis_df,
            template_file=template_full_path,
            output_file=output_full_path,
            report_name=report_name,
            filters=report_config.get('filters')
        )
        success_message = f"Stock export '{report_name}' created successfully at '{output_full_path}'."
        return True, success_message
    except Exception as e:
        error_message = f"Failed to create stock export '{report_name}'. See logs/app_errors.log for details."
        logger.error(f"Error creating stock export '{report_name}': {e}", exc_info=True)
        return False, error_message
