import pytest
import pandas as pd
import io
from unittest.mock import patch

# Додаємо шлях до основного проєкту для коректного імпорту
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from shopify_tool import analysis

# --- Тести для ізольованих (unit) функцій ---

@pytest.mark.parametrize("input_method, expected_output", [
    ("dhl express", "DHL"),
    ("DPD Standard", "DPD"),
    ("international shipping (free)", "PostOne"),
    ("Some Other Method", "Some Other Method"),
    (None, "Unknown"),
    (123, "123")
])
def test_generalize_shipping_method(input_method, expected_output):
    """
    Перевіряє, чи функція _generalize_shipping_method коректно
    стандартизує назви методів доставки.
    """
    result = analysis._generalize_shipping_method(input_method)
    assert result == expected_output

# --- Тести для основної логіки (інтеграційні) ---

@pytest.fixture
def mock_stock_df():
    """Фікстура, що створює тестовий DataFrame залишків."""
    data = {
        'Артикул': ['SKU-A', 'SKU-B', 'SKU-C'],
        'Име': ['Product A', 'Product B', 'Product C'],
        'Наличност': [10, 5, 0]
    }
    return pd.DataFrame(data)

# ⭐ ВИРІШЕННЯ: Тести переписано для перевірки реального результату
# через буфер у пам'яті, що робить їх надійнішими.

@patch('os.path.exists', return_value=True)
@patch('pandas.read_csv')
def test_run_analysis_happy_path(mock_read_csv, mock_os_exists, mock_stock_df):
    """
    Тестує "щасливий шлях", перевіряючи фактичний вміст
    згенерованого Excel-файлу.
    """
    # GIVEN: одне замовлення, для якого достатньо товару
    orders_data = {
        'Name': ['#1001'], 'Lineitem sku': ['SKU-A'], 'Lineitem quantity': [8],
        'Shipping Method': ['dhl'], 'Shipping Country': ['DE']
    }
    mock_orders_df_single = pd.DataFrame(orders_data)
    mock_read_csv.side_effect = [mock_stock_df, mock_orders_df_single]
    
    # Створюємо віртуальний бінарний файл у пам'яті
    output_buffer = io.BytesIO()

    # WHEN: запускаємо аналіз, передаючи буфер замість шляху до файлу
    analysis.run_analysis('fake_stock.csv', 'fake_orders.csv', output_buffer)

    # THEN: читаємо результат з буфера і перевіряємо його вміст
    output_buffer.seek(0) # Переміщуємо курсор на початок файлу
    result_df = pd.read_excel(output_buffer)
    
    assert not result_df.empty
    assert result_df['Order_Fulfillment_Status'].iloc[0] == 'Fulfillable'
    assert result_df['Stock'].iloc[0] == 10

@patch('os.path.exists', return_value=True)
@patch('pandas.read_csv')
def test_run_analysis_insufficient_stock(mock_read_csv, mock_os_exists, mock_stock_df):
    """
    Тестує випадок з недостатнім залишком, перевіряючи фактичний
    вміст згенерованого Excel-файлу.
    """
    # GIVEN: замовлення на 12 одиниць, коли на складі є лише 10
    orders_data = {
        'Name': ['#1002'], 'Lineitem sku': ['SKU-A'], 'Lineitem quantity': [12],
        'Shipping Method': ['dhl'], 'Shipping Country': ['DE']
    }
    mock_orders_df_fail = pd.DataFrame(orders_data)
    mock_read_csv.side_effect = [mock_stock_df, mock_orders_df_fail]
    
    output_buffer = io.BytesIO()

    # WHEN: запускаємо аналіз
    analysis.run_analysis('fake_stock.csv', 'fake_orders.csv', output_buffer)

    # THEN: читаємо результат і перевіряємо статус
    output_buffer.seek(0)
    result_df = pd.read_excel(output_buffer)

    assert not result_df.empty
    assert result_df['Order_Fulfillment_Status'].iloc[0] == 'Not Fulfillable'
