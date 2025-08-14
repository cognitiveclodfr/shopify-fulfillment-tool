# shopify_tool/core.py

import os
import pandas as pd
from datetime import datetime

from . import analysis, packing_lists, stock_export

def run_full_analysis(stock_file_path, orders_file_path, output_dir):
    """
    Runs the full fulfillment analysis.

    Args:
        stock_file_path (str): Path to the stock CSV file.
        orders_file_path (str): Path to the orders CSV file.
        output_dir (str): Directory to save the analysis report.

    Returns:
        tuple: A tuple containing (bool: success, str: result_path or error_message).
    """
    print("--- Starting Analysis ---")
    try:
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        # Define the standard output path for the analysis file
        output_file_path = os.path.join(output_dir, "fulfillment_analysis.xlsx")

        analysis.run_analysis(
            stock_file_path=stock_file_path,
            orders_file_path=orders_file_path,
            output_file_path=output_file_path
        )
        print(f"--- Analysis Completed Successfully! ---")
        return True, output_file_path
    except Exception as e:
        error_message = f"An unexpected error occurred during analysis: {e}"
        print(f"ERROR: {error_message}")
        return False, error_message

def create_packing_list_report(analysis_df, report_config):
    """
    Generates a single packing list report based on the provided configuration.

    Args:
        analysis_df (pd.DataFrame): The DataFrame with analysis results.
        report_config (dict): A dictionary containing the configuration for the report.

    Returns:
        tuple: A tuple containing (bool: success, str: message).
    """
    report_name = report_config.get('name', 'Unknown Report')
    print(f"--- Generating Packing List: {report_name} ---")
    try:
        output_file = report_config['output_filename']
        # Ensure the output directory exists
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        
        packing_lists.create_packing_list(
            analysis_df=analysis_df,
            output_file=output_file,
            report_name=report_name,
            filters=report_config.get('filters')
        )
        success_message = f"Report '{report_name}' created successfully at '{output_file}'."
        print(success_message)
        return True, success_message
    except Exception as e:
        error_message = f"Failed to create report '{report_name}': {e}"
        print(f"ERROR: {error_message}")
        return False, error_message

def create_stock_export_report(analysis_df, report_config, templates_path, output_path):
    """
    Generates a single stock export report based on the provided configuration.

    Args:
        analysis_df (pd.DataFrame): The DataFrame with analysis results.
        report_config (dict): A dictionary containing the configuration for the report.
        templates_path (str): Path to the directory with template files.
        output_path (str): Path to the directory to save the export file.

    Returns:
        tuple: A tuple containing (bool: success, str: message).
    """
    report_name = report_config.get('name', 'Unknown Report')
    print(f"--- Generating Stock Export: {report_name} ---")
    try:
        template_name = report_config['template']
        template_full_path = os.path.join(templates_path, template_name)
        
        # Generate a new filename with a datestamp
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
        print(success_message)
        return True, success_message
    except Exception as e:
        error_message = f"Failed to create stock export '{report_name}': {e}"
        print(f"ERROR: {error_message}")
        return False, error_message
