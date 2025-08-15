import os
import pandas as pd
from datetime import datetime
from . import analysis, packing_lists, stock_export
import logging
logger = logging.getLogger('ShopifyToolLogger')

def run_full_analysis(stock_file_path, orders_file_path, output_dir_path, stock_delimiter):
    """
    Loads data, runs analysis, saves all report files, and updates history.
    """
    print("--- Starting Full Analysis Process ---")
    try:
        # 1. Load data
        print("Step 1: Loading data files...")
        if not os.path.exists(stock_file_path) or not os.path.exists(orders_file_path):
            return False, "One or both input files were not found.", None, None
        
        stock_df = pd.read_csv(stock_file_path, delimiter=stock_delimiter)
        orders_df = pd.read_csv(orders_file_path)
        print("Data loaded successfully.")

        history_path = 'fulfillment_history.csv'
        try:
            history_df = pd.read_csv(history_path)
            print(f"Loaded {len(history_df)} records from fulfillment history.")
        except FileNotFoundError:
            history_df = pd.DataFrame(columns=['Order_Number', 'Execution_Date'])
            print("Fulfillment history not found. A new one will be created.")

        # 2. Run analysis (computation only)
        print("Step 2: Running fulfillment simulation...")
        final_df, summary_present_df, summary_missing_df, stats = analysis.run_analysis(
            stock_df, orders_df, history_df
        )
        print("Analysis computation complete.")

        # 3. Save Excel report
        print("Step 3: Saving analysis report to Excel...")
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
        print(f"Excel report saved to '{output_file_path}'")

        # 4. Update history
        print("Step 4: Updating fulfillment history...")
        newly_fulfilled = final_df[final_df['Order_Fulfillment_Status'] == 'Fulfillable'][['Order_Number']].drop_duplicates()
        if not newly_fulfilled.empty:
            newly_fulfilled['Execution_Date'] = datetime.now().strftime("%Y-%m-%d")
            updated_history = pd.concat([history_df, newly_fulfilled]).drop_duplicates(subset=['Order_Number'], keep='last')
            updated_history.to_csv(history_path, index=False)
            print(f"Updated fulfillment history with {len(newly_fulfilled)} new records.")

        return True, output_file_path, final_df, stats

    except Exception as e:
        error_message = f"An unexpected error occurred during analysis. See logs/app_errors.log for details."
        logger.error("Error in run_full_analysis", exc_info=True)
        print(f"ERROR: {error_message}")  # keep print for GUI logging
        return False, error_message, None, None

def create_packing_list_report(analysis_df, report_config):
    """
    Generates a single packing list report.
    """
    report_name = report_config.get('name', 'Unknown Report')
    try:
        output_file = report_config['output_filename']
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        
        packing_lists.create_packing_list(
            analysis_df=analysis_df,
            output_file=output_file,
            report_name=report_name,
            filters=report_config.get('filters')
        )
        success_message = f"Report '{report_name}' created successfully at '{output_file}'."
        return True, success_message
    except Exception as e:
        error_message = f"Failed to create report '{report_name}'. See logs/app_errors.log for details."
        logger.error(f"Error creating packing list '{report_name}': {e}", exc_info=True)
        return False, error_message

def create_stock_export_report(analysis_df, report_config, templates_path, output_path):
    """
    Generates a single stock export report.
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
