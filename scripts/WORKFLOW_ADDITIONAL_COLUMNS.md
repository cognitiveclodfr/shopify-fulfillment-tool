# Workflow: Як використовувати додаткові колонки

## Покрокова інструкція

### Крок 1: Завантажити CSV файли

1. Відкрийте додаток
2. Виберіть клієнта (наприклад, ALMA)
3. Завантажте файли Orders CSV та Stock CSV
4. **НЕ запускайте аналіз ще!**

### Крок 2: Налаштувати додаткові колонки

1. Відкрийте меню **Configure → Column Configuration**
2. В діалозі прокрутіть вниз до секції **"Additional CSV Columns"**
3. Натисніть кнопку **"Scan Current CSV for Available Columns"**
4. Ви побачите список з ~69 колонок (всі невиділені за замовчуванням)
5. **Виділіть колонки** які потрібні (наприклад: Email, Phone, Financial Status)
6. Натисніть **"Apply"**
7. Закрийте діалог

**ВАЖЛИВО**: Конфігурація тепер збережена в файлі:
```
D:\Dev\fulfillment-server-mock\Clients\CLIENT_ALMA\client_config.json
```

### Крок 3: Запустити аналіз

1. Натисніть **"Run Analysis"**
2. **Подивіться на логи** - тепер ви маєте побачити:

```
INFO: Loaded client config: 69 additional columns configured, 3 enabled
INFO: Enabled additional columns: ['Email', 'Phone', 'Financial Status']
INFO: Additional columns: 69 total, 3 enabled
INFO: Enabled columns: ['Email', 'Phone', 'Financial Status']
INFO: Processing 69 additional columns config
INFO: Renamed 3 additional columns: ['Email', 'Phone', 'Financial_Status']
INFO: Additional columns to keep: 3 columns
INFO:   Columns: ['Email', 'Phone', 'Financial_Status']
INFO: Total columns to keep: 13 (10 base + 3 additional)
```

3. Після завершення аналізу ви побачите:

```
INFO: Final DataFrame: 380 rows, 13 columns
INFO: Columns: ['Order_Number', 'SKU', 'Quantity', ..., 'Email', 'Phone', 'Financial_Status']
```

### Крок 4: Перевірити результати в таблиці

1. Відкрийте вкладку **"Analysis Results"**
2. Таблиця тепер має додаткові колонки: Email, Phone, Financial_Status
3. Ви можете приховати/показати їх через **Configure → Column Configuration**

---

## Діагностика проблем

### Проблема 1: В логах немає "Loaded client config"

**Причина**: client_config не завантажується

**Рішення**:
1. Перевірте чи існує файл: `D:\Dev\fulfillment-server-mock\Clients\CLIENT_ALMA\client_config.json`
2. Відкрийте його і перевірте структуру:

```json
{
  "ui_settings": {
    "table_view": {
      "additional_columns": [
        {
          "csv_name": "Email",
          "internal_name": "Email",
          "enabled": true,
          "is_order_level": true
        }
      ]
    }
  }
}
```

### Проблема 2: "Additional columns: 69 total, 0 enabled"

**Причина**: Ви налаштували колонки, але НЕ виділили жодну (всі `enabled: false`)

**Рішення**:
1. Відкрийте Column Configuration
2. Натисніть "Scan Current CSV"
3. **ВИДІЛІТЬ чекбокси** біля потрібних колонок
4. Натисніть Apply

### Проблема 3: "Configured additional columns not found in CSV"

**Причина**: Ви налаштували колонки для одного CSV, але потім завантажили інший CSV без цих колонок

**Рішення**:
1. Це нормальна ситуація - просто warning
2. Колонки які відсутні будуть пропущені
3. Решта колонок з'являться в результатах

### Проблема 4: Колонки є в результатах, але не видно в таблиці

**Причина**: Table customization приховує колонки

**Рішення**:
1. Відкрийте Column Configuration
2. В списку колонок знайдіть додаткові колонки (Email, Phone, etc.)
3. **Виділіть чекбокси** щоб показати їх
4. Натисніть Apply

---

## Тестування

Щоб перевірити що все працює:

```powershell
# 1. Запустіть додаток в dev mode
START_DEV.bat

# 2. Завантажте CSV файли (не запускайте аналіз)

# 3. Відкрийте Column Configuration

# 4. Scan CSV -> виділіть Email, Phone, Financial Status -> Apply

# 5. Запустіть аналіз

# 6. Перевірте логи - має бути "Renamed 3 additional columns"

# 7. Перевірте таблицю - має бути 13 колонок замість 10
```

---

## Очікувані логи (SUCCESS)

```
INFO: Loaded client config: 69 additional columns configured, 3 enabled
INFO: Enabled additional columns: ['Email', 'Phone', 'Financial Status']
...
INFO: Additional columns: 69 total, 3 enabled
INFO: Enabled columns: ['Email', 'Phone', 'Financial Status']
INFO: Processing 69 additional columns config
INFO: Renamed 3 additional columns: ['Email', 'Phone', 'Financial_Status']
...
INFO: Additional columns to keep: 3 columns
INFO:   Columns: ['Email', 'Phone', 'Financial_Status']
INFO: Total columns to keep: 13 (10 base + 3 additional)
INFO: Columns existing in DataFrame: 13
...
INFO: Found 3 new columns in DataFrame, adding to config: ['Email', 'Phone', 'Financial_Status']
...
INFO: Final DataFrame: 380 rows, 13 columns
INFO: Columns: ['Order_Number', 'SKU', 'Quantity', 'Shipping_Method', 'Shipping_Country', 'Product_Name', 'Tags', 'Notes', 'Total_Price', 'Subtotal', 'Email', 'Phone', 'Financial_Status']
```

---

## Якщо нічого не працює

Створіть конфіг вручну:

```powershell
# Відкрийте файл
notepad D:\Dev\fulfillment-server-mock\Clients\CLIENT_ALMA\client_config.json
```

Додайте:

```json
{
  "ui_settings": {
    "table_view": {
      "Default": {...},
      "additional_columns": [
        {
          "csv_name": "Email",
          "internal_name": "Email",
          "enabled": true,
          "is_order_level": true,
          "exists_in_df": true
        },
        {
          "csv_name": "Phone",
          "internal_name": "Phone",
          "enabled": true,
          "is_order_level": true,
          "exists_in_df": true
        },
        {
          "csv_name": "Financial Status",
          "internal_name": "Financial_Status",
          "enabled": true,
          "is_order_level": true,
          "exists_in_df": true
        }
      ]
    }
  }
}
```

Збережіть і запустіть аналіз знову.
