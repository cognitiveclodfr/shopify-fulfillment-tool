import json
import os
import pandas as pd
from datetime import datetime
from shopify_tool import analysis, packing_lists, stock_export

# ... (функції load_config, run_main_analysis, run_packing_list_creation без змін) ...

def load_config(config_path='config.json'):
    """Завантажує конфігураційний файл."""
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"ПОМИЛКА: Файл конфігурації '{config_path}' не знайдено.")
        return None
    except json.JSONDecodeError:
        print(f"ПОМИЛКА: Некоректний формат JSON у файлі '{config_path}'.")
        return None

def run_main_analysis(config):
    """Запускає повний аналіз замовлень."""
    paths = config.get('paths', {})
    input_paths = paths.get('input', {})
    output_paths = paths.get('output', {})
    settings = config.get('settings', {})

    stock_file = input_paths.get('stock_file')
    orders_file = input_paths.get('orders_file')
    analysis_file = output_paths.get('analysis_file')
    stock_delimiter = settings.get('stock_csv_delimiter', ';')

    if not all([stock_file, orders_file, analysis_file]):
        print("ПОМИЛКА: Не всі необхідні шляхи для аналізу вказані у config.json.")
        return
    
    analysis.run_analysis(
        stock_file_path=stock_file,
        orders_file_path=orders_file,
        output_file_path=analysis_file,
        stock_delimiter=stock_delimiter
    )

def run_packing_list_creation(config):
    """Показує меню для вибору та створення пакувального листа."""
    analysis_file_path = config.get('paths', {}).get('output', {}).get('analysis_file')
    if not analysis_file_path or not os.path.exists(analysis_file_path):
        print(f"ПОМИЛКА: Файл аналізу '{analysis_file_path}' не знайдено.")
        print("Будь ласка, спочатку запустіть повний аналіз (опція 1).")
        return

    analysis_df = pd.read_excel(analysis_file_path, sheet_name='Fulfillment Analysis')
    reports = config.get('packing_lists', [])
    if not reports:
        print("ПОМИЛКА: У файлі config.json не налаштовано жодного пакувального листа.")
        return

    print("\nОберіть, який пакувальний лист створити:")
    for i, report in enumerate(reports):
        print(f"  {i + 1}. {report.get('name', 'Невідомий звіт')}")
    print("  0. Повернутися в головне меню")

    try:
        choice = int(input("Ваш вибір: "))
        if choice == 0:
            return
        if 1 <= choice <= len(reports):
            selected_report = reports[choice - 1]
            packing_lists.create_packing_list(
                analysis_df=analysis_df,
                output_file=selected_report['output_filename'],
                report_name=selected_report['name'],
                filters=selected_report.get('filters')
            )
        else:
            print("Некоректний вибір. Спробуйте ще раз.")
    except ValueError:
        print("Будь ласка, введіть число.")

def run_stock_export_creation(config):
    """Показує меню для вибору та створення експорту залишків."""
    analysis_file_path = config.get('paths', {}).get('output', {}).get('analysis_file')
    templates_path = config.get('paths', {}).get('templates', 'data/templates/')
    output_path = config.get('paths', {}).get('output_dir_stock', 'data/output/')


    if not os.path.exists(analysis_file_path):
        print(f"ПОМИЛКА: Файл аналізу '{analysis_file_path}' не знайдено.")
        return

    analysis_df = pd.read_excel(analysis_file_path, sheet_name='Fulfillment Analysis')
    reports = config.get('stock_exports', [])
    if not reports:
        print("ПОМИЛКА: У файлі config.json не налаштовано жодного експорту залишків.")
        return

    print("\nОберіть, який експорт залишків створити:")
    for i, report in enumerate(reports):
        print(f"  {i + 1}. {report.get('name', 'Невідомий звіт')}")
    print("  0. Повернутися в головне меню")

    try:
        choice = int(input("Ваш вибір: "))
        if choice == 0: return
        if 1 <= choice <= len(reports):
            selected_report = reports[choice - 1]
            template_name = selected_report['template']
            template_full_path = os.path.join(templates_path, template_name)
            
            # ⭐ ОНОВЛЕННЯ: Генерація нової назви файлу з датою
            datestamp = datetime.now().strftime("%Y-%m-%d")
            name, ext = os.path.splitext(template_name)
            output_filename = f"{name}_{datestamp}{ext}"
            output_full_path = os.path.join(output_path, output_filename)
            
            stock_export.create_stock_export(
                analysis_df=analysis_df,
                template_file=template_full_path,
                output_file=output_full_path,
                report_name=selected_report['name'],
                filters=selected_report.get('filters')
            )
        else:
            print("Некоректний вибір.")
    except ValueError:
        print("Будь ласка, введіть число.")

def main():
    """Головна функція для запуску інструменту."""
    config = load_config()
    if not config: return

    while True:
        print("\n--- ГОЛОВНЕ МЕНЮ ---")
        print("1. Запустити повний аналіз")
        print("2. Створити пакувальний лист")
        print("3. Створити експорт залишків")
        print("4. Вийти")
        
        choice = input("Оберіть дію: ")

        if choice == '1': run_main_analysis(config)
        elif choice == '2': run_packing_list_creation(config)
        elif choice == '3': run_stock_export_creation(config)
        elif choice == '4':
            print("--- Роботу завершено ---")
            break
        else:
            print("Некоректний вибір.")

if __name__ == "__main__":
    main()
