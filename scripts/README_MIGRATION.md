# Client Configuration Migration

## Overview

This migration script adds source platform column mappings to existing client configurations.

## What it does

The script adds the following fields to `column_mappings` in `shopify_config.json`:

- `source_platform`: "shopify" or "woocommerce" (default: "woocommerce" for existing clients)
- `orders_source_mappings`: Platform-specific column name mappings
- `stock_source_mappings`: Stock file column mappings

## Usage

### Dry run (recommended first)

```bash
python scripts/migrate_client_configs.py --dry-run
```

This will show what would be changed without making any changes.

### Migrate all clients

```bash
python scripts/migrate_client_configs.py
```

### Migrate specific client

```bash
python scripts/migrate_client_configs.py --client LIDA
```

## What gets added

For each client missing the new structure, the script adds:

```json
{
  "column_mappings": {
    "source_platform": "woocommerce",
    "orders_source_mappings": {
      "shopify": {
        "Name": "Name",
        "Lineitem sku": "Lineitem sku",
        ...
      },
      "woocommerce": {
        "Order ID": "Name",
        "Lineitem sku": "Lineitem sku",
        ...
      }
    },
    "stock_source_mappings": {
      "default": {
        "Артикул": "Артикул",
        "Име": "Име",
        "Наличност": "Наличност"
      }
    }
  }
}
```

## Why this is needed

WooCommerce and Shopify CSV exports use different column names:

- WooCommerce uses `Order ID` for order number
- Shopify uses `Name` for order number

The analysis engine expects Shopify format (`Name`), so WooCommerce files need column mapping.

## After migration

1. The client config will have the new structure
2. Users can change `source_platform` in Settings UI
3. Batch loading will automatically apply the correct column mapping
4. Both WooCommerce and Shopify files will work correctly

## Backup

The script automatically creates backups before modifying configs (in `Clients/CLIENT_XXX/backups/`).
