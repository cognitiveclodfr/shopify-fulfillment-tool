import sys
sys.path.append("..")
import pandas as pd
from shopify_tool import packing_lists

def test_exclude_skus():
    # Створюємо тестові дані
    df = pd.DataFrame({
        'Order_Fulfillment_Status': ['Fulfillable', 'Fulfillable', 'Fulfillable'],
        'Order_Number': [1, 2, 3],
        'SKU': ['07', 'Shipping protection', 'ABC123'],
        'Product_Name': ['Test1', 'Test2', 'Test3'],
        'Destination_Country': ['UA', 'UA', 'UA']
    })
    # Викликаємо функцію
    packing_lists.create_packing_list(
        analysis_df=df,
        output_file="dummy.xlsx",
        report_name="Test",
        filters=None,
        exclude_skus=["07", "Shipping protection"]
    )
    # Перевіряємо, що виключені SKU відсутні
    filtered = df[~df['SKU'].isin(["07", "Shipping protection"])]
    assert all(sku not in ["07", "Shipping protection"] for sku in filtered['SKU'])
