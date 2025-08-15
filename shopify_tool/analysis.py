import pandas as pd
import numpy as np

def _generalize_shipping_method(method):
    """
    Standardizes shipping method names to a consistent format.
    """
    if pd.isna(method):
        return 'Unknown'
    method = str(method).lower()
    if 'dhl' in method:
        return 'DHL'
    if 'dpd' in method:
        return 'DPD'
    if 'international shipping' in method:
        return 'PostOne'
    return method.title()

def run_analysis(stock_df, orders_df, history_df):
    """
    Performs a full fulfillment analysis and returns the results and statistics.
    This function does not perform any file I/O.
    """
    # --- Data Cleaning ---
    orders_df['Name'] = orders_df['Name'].ffill()
    orders_df['Shipping Method'] = orders_df['Shipping Method'].ffill()
    orders_df['Shipping Country'] = orders_df['Shipping Country'].ffill()
    
    columns_to_keep = ['Name', 'Lineitem sku', 'Lineitem quantity', 'Shipping Method', 'Shipping Country', 'Tags', 'Notes']
    orders_clean_df = orders_df[columns_to_keep].copy()
    orders_clean_df.rename(columns={'Name': 'Order_Number', 'Lineitem sku': 'SKU', 'Lineitem quantity': 'Quantity'}, inplace=True)
    orders_clean_df.dropna(subset=['SKU'], inplace=True)

    stock_clean_df = stock_df[['Артикул', 'Име', 'Наличност']].copy()
    stock_clean_df.rename(columns={'Артикул': 'SKU', 'Име': 'Product_Name', 'Наличност': 'Stock'}, inplace=True)
    stock_clean_df.dropna(subset=['SKU'], inplace=True)
    stock_clean_df.drop_duplicates(subset=['SKU'], keep='first', inplace=True)
    
    # --- Fulfillment Simulation ---
    order_item_counts = orders_clean_df.groupby('Order_Number').size().rename('item_count')
    orders_with_counts = pd.merge(orders_clean_df, order_item_counts, on='Order_Number')
    prioritized_orders = orders_with_counts[['Order_Number', 'item_count']].drop_duplicates().sort_values(by=['item_count', 'Order_Number'], ascending=[False, True])
    
    live_stock = pd.Series(stock_clean_df.Stock.values, index=stock_clean_df.SKU).to_dict()
    fulfillment_results = {}

    for order_number in prioritized_orders['Order_Number']:
        order_items = orders_with_counts[orders_with_counts['Order_Number'] == order_number]
        can_fulfill_order = True
        # Перевіряємо, чи можна виконати замовлення
        for _, item in order_items.iterrows():
            sku, required_qty = item['SKU'], item['Quantity']
            if required_qty > live_stock.get(sku, 0):
                can_fulfill_order = False
                break
        # Якщо так, списуємо товари
        if can_fulfill_order:
            fulfillment_results[order_number] = 'Fulfillable'
            for _, item in order_items.iterrows():
                live_stock[item['SKU']] -= item['Quantity']
        else:
            fulfillment_results[order_number] = 'Not Fulfillable'

    # Calculate final stock levels after fulfillment
    final_stock_levels = pd.Series(live_stock, name="Final_Stock").reset_index().rename(columns={'index': 'SKU'})

    # --- Final Report Generation ---
    final_df = pd.merge(orders_clean_df, stock_clean_df, on='SKU', how='left')
    final_df = pd.merge(final_df, order_item_counts, on='Order_Number')
    final_df['Order_Type'] = np.where(final_df['item_count'] > 1, 'Multi', 'Single')
    final_df['Stock'].fillna(0, inplace=True)
    final_df['Shipping_Provider'] = final_df['Shipping Method'].apply(_generalize_shipping_method)
    final_df['Order_Fulfillment_Status'] = final_df['Order_Number'].map(fulfillment_results)
    final_df['Destination_Country'] = np.where(final_df['Shipping_Provider'] == 'DHL', final_df['Shipping Country'], '')
    final_df['Status_Note'] = np.where(final_df['Order_Number'].isin(history_df['Order_Number']), 'Repeat', '')
    output_columns = ['Order_Number', 'Order_Type', 'SKU', 'Product_Name', 'Quantity', 'Stock', 'Order_Fulfillment_Status', 'Shipping_Provider', 'Destination_Country', 'Shipping Method', 'Tags', 'Notes', 'Status_Note']
    final_df = final_df[output_columns]

    # --- Summary Reports Generation ---
    present_df = final_df[final_df['Order_Fulfillment_Status'] == 'Fulfillable'].copy()
    summary_present_df = present_df.groupby(['SKU', 'Product_Name'], as_index=False)['Quantity'].sum()
    summary_present_df.rename(columns={'Product_Name': 'Name', 'Quantity': 'Total Quantity'}, inplace=True)
    summary_present_df = summary_present_df[['Name', 'SKU', 'Total Quantity']]

    # --- New logic for Summary_Missing ---
    # 1. Get all items from orders that could not be fulfilled.
    not_fulfilled_df = final_df[final_df['Order_Fulfillment_Status'] == 'Not Fulfillable'].copy()

    # 2. Identify items that are "truly missing" by comparing required quantity vs initial stock.
    truly_missing_df = not_fulfilled_df[not_fulfilled_df['Quantity'] > not_fulfilled_df['Stock']]

    # 3. Create the summary report from this filtered data.
    if not truly_missing_df.empty:
        summary_missing_df = truly_missing_df.groupby(['SKU', 'Product_Name'], as_index=False)['Quantity'].sum()
        summary_missing_df.rename(columns={'Product_Name': 'Name', 'Quantity': 'Total Quantity'}, inplace=True)
        summary_missing_df = summary_missing_df[['Name', 'SKU', 'Total Quantity']]
    else:
        summary_missing_df = pd.DataFrame(columns=['Name', 'SKU', 'Total Quantity'])

    # --- Statistics Calculation ---
    stats = {}
    completed_orders_df = final_df[final_df['Order_Fulfillment_Status'] == 'Fulfillable']
    not_completed_orders_df = final_df[final_df['Order_Fulfillment_Status'] == 'Not Fulfillable']
    
    stats['total_orders_completed'] = int(completed_orders_df['Order_Number'].nunique())
    stats['total_orders_not_completed'] = int(not_completed_orders_df['Order_Number'].nunique())
    stats['total_items_to_write_off'] = int(completed_orders_df['Quantity'].sum())
    stats['total_items_not_to_write_off'] = int(not_completed_orders_df['Quantity'].sum())
    
    courier_stats = []
    if not completed_orders_df.empty:
        # Fill NA to include 'Unknown' providers in the stats
        completed_orders_df['Shipping_Provider'].fillna('Unknown', inplace=True)
        grouped_by_courier = completed_orders_df.groupby('Shipping_Provider')
        for provider, group in grouped_by_courier:
            courier_data = {
                'courier_id': provider,
                'orders_assigned': int(group['Order_Number'].nunique()),
                'repeated_orders_found': int(group[group['Status_Note'] == 'Repeat']['Order_Number'].nunique())
            }
            courier_stats.append(courier_data)
    # Per instructions, use null (None) if no stats are available
    stats['couriers_stats'] = courier_stats if courier_stats else None
    
    return final_df, summary_present_df, summary_missing_df, stats
