"""Create comprehensive test data for Shopify Fulfillment Tool and Packing Tool.

This script generates realistic test data that covers all possible scenarios:
- Single and Multi-item orders
- Fulfillable and Not fulfillable orders
- Competing orders (same SKU)
- Different couriers (DHL, DPD, PostOne, Speedy)
- Different countries
- Tags and priorities
- Low stock scenarios
- Exclude SKUs (07, Shipping protection)
- Repeat orders

The data is designed to test the complete workflow:
Shopify Tool (Analysis + Reports) → Packing Tool (Scanning + Packing)
"""

import pandas as pd
from pathlib import Path
from datetime import datetime, timedelta
import random


def create_comprehensive_orders(output_path: Path = None):
    """Create comprehensive orders CSV with all test scenarios.

    Args:
        output_path: Optional path for output CSV. Defaults to data/test_input/comprehensive_orders.csv
    """

    print("Creating comprehensive test orders...")

    # Base date for orders
    base_date = datetime(2025, 11, 7)

    orders_data = []

    # ========================================
    # SCENARIO 1: Single-item orders (Fulfillable)
    # ========================================
    # Order 1001: Single DHL - High stock
    orders_data.append({
        "Name": "#1001",
        "Email": "customer1@example.com",
        "Financial Status": "paid",
        "Fulfillment Status": "",
        "Currency": "BGN",
        "Subtotal": "45.00",
        "Shipping": "5.00",
        "Taxes": "0.00",
        "Total": "50.00",
        "Discount Code": "",
        "Discount Amount": "0.00",
        "Shipping Method": "DHL Express Shipping",
        "Created at": (base_date - timedelta(days=2)).strftime("%Y-%m-%d %H:%M:%S"),
        "Lineitem quantity": 1,
        "Lineitem name": "Python Camo Denim - Size Large (34)",
        "Lineitem sku": "01-DM-0379-110-L",
        "Lineitem price": "45.00",
        "Billing Name": "John Doe",
        "Billing Street": "123 Main St",
        "Billing City": "Sofia",
        "Billing Zip": "1000",
        "Billing Province": "Sofia",
        "Billing Country": "Bulgaria",
        "Billing Phone": "+359888123456",
        "Shipping Name": "John Doe",
        "Shipping Street": "123 Main St",
        "Shipping City": "Sofia",
        "Shipping Zip": "1000",
        "Shipping Province": "Sofia",
        "Shipping Country": "Bulgaria",
        "Shipping Phone": "+359888123456",
        "Notes": "",
        "Tags": "",
        "Cancelled at": "",
        "Payment Method": "Credit Card",
        "Payment Reference": "ch_3ABC123",
        "Refunded Amount": "0.00",
        "Vendor": "M Cosmetics",
        "Outstanding Balance": "0.00",
        "Risk Level": "low",
        "Source": "web",
        "Lineitem discount": "0.00"
    })

    # Order 1002: Single DPD - Medium stock
    orders_data.append({
        "Name": "#1002",
        "Email": "customer2@example.com",
        "Financial Status": "paid",
        "Fulfillment Status": "",
        "Currency": "BGN",
        "Subtotal": "38.00",
        "Shipping": "5.00",
        "Taxes": "0.00",
        "Total": "43.00",
        "Discount Code": "SAVE10",
        "Discount Amount": "4.20",
        "Shipping Method": "DPD Standard",
        "Created at": (base_date - timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S"),
        "Lineitem quantity": 1,
        "Lineitem name": "Flare Repaired Denim - Cream Wash, Size Medium",
        "Lineitem sku": "01-DM-0239-003-M",
        "Lineitem price": "38.00",
        "Billing Name": "Jane Smith",
        "Billing Street": "456 Oak Ave",
        "Billing City": "Plovdiv",
        "Billing Zip": "4000",
        "Billing Province": "Plovdiv",
        "Billing Country": "Bulgaria",
        "Billing Phone": "+359888234567",
        "Shipping Name": "Jane Smith",
        "Shipping Street": "456 Oak Ave",
        "Shipping City": "Plovdiv",
        "Shipping Zip": "4000",
        "Shipping Province": "Plovdiv",
        "Shipping Country": "Bulgaria",
        "Shipping Phone": "+359888234567",
        "Notes": "",
        "Tags": "",
        "Cancelled at": "",
        "Payment Method": "PayPal",
        "Payment Reference": "PAYID-ABC123",
        "Refunded Amount": "0.00",
        "Vendor": "M Cosmetics",
        "Outstanding Balance": "0.00",
        "Risk Level": "low",
        "Source": "web",
        "Lineitem discount": "0.00"
    })

    # Order 1003: Single PostOne - Low stock (will compete)
    orders_data.append({
        "Name": "#1003",
        "Email": "customer3@example.com",
        "Financial Status": "paid",
        "Fulfillment Status": "",
        "Currency": "BGN",
        "Subtotal": "32.00",
        "Shipping": "3.50",
        "Taxes": "0.00",
        "Total": "35.50",
        "Discount Code": "",
        "Discount Amount": "0.00",
        "Shipping Method": "PostOne",
        "Created at": (base_date - timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S"),
        "Lineitem quantity": 2,
        "Lineitem name": "Eyelet Flare Denim, Size Medium (32)",
        "Lineitem sku": "01-DM-0339-006-M",
        "Lineitem price": "32.00",
        "Billing Name": "Peter Johnson",
        "Billing Street": "789 Pine Rd",
        "Billing City": "Varna",
        "Billing Zip": "9000",
        "Billing Province": "Varna",
        "Billing Country": "Bulgaria",
        "Billing Phone": "+359888345678",
        "Shipping Name": "Peter Johnson",
        "Shipping Street": "789 Pine Rd",
        "Shipping City": "Varna",
        "Shipping Zip": "9000",
        "Shipping Province": "Varna",
        "Shipping Country": "Bulgaria",
        "Shipping Phone": "+359888345678",
        "Notes": "",
        "Tags": "",
        "Cancelled at": "",
        "Payment Method": "Credit Card",
        "Payment Reference": "ch_3DEF456",
        "Refunded Amount": "0.00",
        "Vendor": "M Cosmetics",
        "Outstanding Balance": "0.00",
        "Risk Level": "low",
        "Source": "mobile",
        "Lineitem discount": "0.00"
    })

    # ========================================
    # SCENARIO 2: Multi-item orders (Priority - process first)
    # ========================================
    # Order 1004: Multi DHL - All items fulfillable (Priority)
    order_1004_items = [
        {
            "Lineitem quantity": 1,
            "Lineitem name": "Python Camo Denim - Size Large (34)",
            "Lineitem sku": "01-DM-0379-110-L",
            "Lineitem price": "45.00",
            "Lineitem discount": "0.00"
        },
        {
            "Lineitem quantity": 1,
            "Lineitem name": "Diamond Mind Tee, Size Large",
            "Lineitem sku": "01-DM-03-Diamond-L",
            "Lineitem price": "28.00",
            "Lineitem discount": "0.00"
        },
        {
            "Lineitem quantity": 1,
            "Lineitem name": "R.S. Socks - Black",
            "Lineitem sku": "03-SK-0230-001-OS",
            "Lineitem price": "12.00",
            "Lineitem discount": "0.00"
        }
    ]

    for item in order_1004_items:
        orders_data.append({
            "Name": "#1004",
            "Email": "vip@example.com",
            "Financial Status": "paid",
            "Fulfillment Status": "",
            "Currency": "BGN",
            "Subtotal": "85.00",
            "Shipping": "8.00",
            "Taxes": "0.00",
            "Total": "93.00",
            "Discount Code": "VIP20",
            "Discount Amount": "17.00",
            "Shipping Method": "DHL Express",
            "Created at": (base_date - timedelta(hours=2)).strftime("%Y-%m-%d %H:%M:%S"),
            "Lineitem quantity": item["Lineitem quantity"],
            "Lineitem name": item["Lineitem name"],
            "Lineitem sku": item["Lineitem sku"],
            "Lineitem price": item["Lineitem price"],
            "Billing Name": "Maria Garcia",
            "Billing Street": "321 Elite St",
            "Billing City": "Sofia",
            "Billing Zip": "1505",
            "Billing Province": "Sofia",
            "Billing Country": "Bulgaria",
            "Billing Phone": "+359888456789",
            "Shipping Name": "Maria Garcia",
            "Shipping Street": "321 Elite St",
            "Shipping City": "Sofia",
            "Shipping Zip": "1505",
            "Shipping Province": "Sofia",
            "Shipping Country": "Bulgaria",
            "Shipping Phone": "+359888456789",
            "Notes": "VIP Customer - Rush order",
            "Tags": "Priority, VIP",
            "Cancelled at": "",
            "Payment Method": "Credit Card",
            "Payment Reference": "ch_3GHI789",
            "Refunded Amount": "0.00",
            "Vendor": "M Cosmetics",
            "Outstanding Balance": "0.00",
            "Risk Level": "low",
            "Source": "web",
            "Lineitem discount": item["Lineitem discount"]
        })

    # Order 1005: Multi Speedy - Competing for low stock items
    order_1005_items = [
        {
            "Lineitem quantity": 3,
            "Lineitem name": "Eyelet Flare Denim, Size Medium (32)",
            "Lineitem sku": "01-DM-0339-006-M",
            "Lineitem price": "32.00",
            "Lineitem discount": "0.00"
        },
        {
            "Lineitem quantity": 1,
            "Lineitem name": "Pearl Denim - Black, Size Medium (32)",
            "Lineitem sku": "01-DM-0334-001-M",
            "Lineitem price": "42.00",
            "Lineitem discount": "0.00"
        }
    ]

    for item in order_1005_items:
        orders_data.append({
            "Name": "#1005",
            "Email": "customer5@example.com",
            "Financial Status": "paid",
            "Fulfillment Status": "",
            "Currency": "BGN",
            "Subtotal": "138.00",
            "Shipping": "6.00",
            "Taxes": "0.00",
            "Total": "144.00",
            "Discount Code": "",
            "Discount Amount": "0.00",
            "Shipping Method": "Speedy",
            "Created at": (base_date - timedelta(hours=3)).strftime("%Y-%m-%d %H:%M:%S"),
            "Lineitem quantity": item["Lineitem quantity"],
            "Lineitem name": item["Lineitem name"],
            "Lineitem sku": item["Lineitem sku"],
            "Lineitem price": item["Lineitem price"],
            "Billing Name": "Alex Brown",
            "Billing Street": "555 Market St",
            "Billing City": "Burgas",
            "Billing Zip": "8000",
            "Billing Province": "Burgas",
            "Billing Country": "Bulgaria",
            "Billing Phone": "+359888567890",
            "Shipping Name": "Alex Brown",
            "Shipping Street": "555 Market St",
            "Shipping City": "Burgas",
            "Shipping Zip": "8000",
            "Shipping Province": "Burgas",
            "Shipping Country": "Bulgaria",
            "Shipping Phone": "+359888567890",
            "Notes": "",
            "Tags": "",
            "Cancelled at": "",
            "Payment Method": "Bank Transfer",
            "Payment Reference": "BNK-2025-001",
            "Refunded Amount": "0.00",
            "Vendor": "M Cosmetics",
            "Outstanding Balance": "0.00",
            "Risk Level": "medium",
            "Source": "web",
            "Lineitem discount": item["Lineitem discount"]
        })

    # ========================================
    # SCENARIO 3: Not fulfillable orders (Insufficient stock)
    # ========================================
    # Order 1006: Single - Out of stock item
    orders_data.append({
        "Name": "#1006",
        "Email": "customer6@example.com",
        "Financial Status": "paid",
        "Fulfillment Status": "",
        "Currency": "BGN",
        "Subtotal": "55.00",
        "Shipping": "5.00",
        "Taxes": "0.00",
        "Total": "60.00",
        "Discount Code": "",
        "Discount Amount": "0.00",
        "Shipping Method": "DHL",
        "Created at": (base_date - timedelta(hours=5)).strftime("%Y-%m-%d %H:%M:%S"),
        "Lineitem quantity": 5,
        "Lineitem name": "Limited Edition Hoodie - Black, Size Small",
        "Lineitem sku": "01-HD-0341-104-S",
        "Lineitem price": "55.00",
        "Billing Name": "Sarah Wilson",
        "Billing Street": "777 Fashion Ave",
        "Billing City": "Sofia",
        "Billing Zip": "1000",
        "Billing Province": "Sofia",
        "Billing Country": "Bulgaria",
        "Billing Phone": "+359888678901",
        "Shipping Name": "Sarah Wilson",
        "Shipping Street": "777 Fashion Ave",
        "Shipping City": "Sofia",
        "Shipping Zip": "1000",
        "Shipping Province": "Sofia",
        "Shipping Country": "Bulgaria",
        "Shipping Phone": "+359888678901",
        "Notes": "",
        "Tags": "",
        "Cancelled at": "",
        "Payment Method": "Credit Card",
        "Payment Reference": "ch_3JKL012",
        "Refunded Amount": "0.00",
        "Vendor": "M Cosmetics",
        "Outstanding Balance": "0.00",
        "Risk Level": "low",
        "Source": "instagram",
        "Lineitem discount": "0.00"
    })

    # ========================================
    # SCENARIO 4: International orders
    # ========================================
    # Order 1007: International DHL - Germany
    orders_data.append({
        "Name": "#1007",
        "Email": "customer7@example.de",
        "Financial Status": "paid",
        "Fulfillment Status": "",
        "Currency": "EUR",
        "Subtotal": "45.00",
        "Shipping": "15.00",
        "Taxes": "8.55",
        "Total": "68.55",
        "Discount Code": "",
        "Discount Amount": "0.00",
        "Shipping Method": "DHL International",
        "Created at": (base_date - timedelta(hours=6)).strftime("%Y-%m-%d %H:%M:%S"),
        "Lineitem quantity": 1,
        "Lineitem name": "Workwear Denim Pant, Size Large (34)",
        "Lineitem sku": "01-DM-0342-104-L",
        "Lineitem price": "45.00",
        "Billing Name": "Hans Mueller",
        "Billing Street": "Hauptstrasse 123",
        "Billing City": "Berlin",
        "Billing Zip": "10115",
        "Billing Province": "Berlin",
        "Billing Country": "Germany",
        "Billing Phone": "+4930123456",
        "Shipping Name": "Hans Mueller",
        "Shipping Street": "Hauptstrasse 123",
        "Shipping City": "Berlin",
        "Shipping Zip": "10115",
        "Shipping Province": "Berlin",
        "Shipping Country": "Germany",
        "Shipping Phone": "+4930123456",
        "Notes": "International - Check customs",
        "Tags": "International",
        "Cancelled at": "",
        "Payment Method": "Credit Card",
        "Payment Reference": "ch_3MNO345",
        "Refunded Amount": "0.00",
        "Vendor": "M Cosmetics",
        "Outstanding Balance": "0.00",
        "Risk Level": "low",
        "Source": "web",
        "Lineitem discount": "0.00"
    })

    # ========================================
    # SCENARIO 5: Repeat customer order
    # ========================================
    # Order 1008: Repeat customer (same email as #1001)
    orders_data.append({
        "Name": "#1008",
        "Email": "customer1@example.com",  # Same as #1001
        "Financial Status": "paid",
        "Fulfillment Status": "",
        "Currency": "BGN",
        "Subtotal": "38.00",
        "Shipping": "5.00",
        "Taxes": "0.00",
        "Total": "43.00",
        "Discount Code": "LOYAL15",
        "Discount Amount": "6.70",
        "Shipping Method": "DHL",
        "Created at": base_date.strftime("%Y-%m-%d %H:%M:%S"),
        "Lineitem quantity": 1,
        "Lineitem name": "Flare Canvas Pants - Taupe, Size Medium (32)",
        "Lineitem sku": "01-PT-0269-066-M",
        "Lineitem price": "38.00",
        "Billing Name": "John Doe",
        "Billing Street": "123 Main St",
        "Billing City": "Sofia",
        "Billing Zip": "1000",
        "Billing Province": "Sofia",
        "Billing Country": "Bulgaria",
        "Billing Phone": "+359888123456",
        "Shipping Name": "John Doe",
        "Shipping Street": "123 Main St",
        "Shipping City": "Sofia",
        "Shipping Zip": "1000",
        "Shipping Province": "Sofia",
        "Shipping Country": "Bulgaria",
        "Shipping Phone": "+359888123456",
        "Notes": "Returning customer",
        "Tags": "Repeat",
        "Cancelled at": "",
        "Payment Method": "Credit Card",
        "Payment Reference": "ch_3PQR678",
        "Refunded Amount": "0.00",
        "Vendor": "M Cosmetics",
        "Outstanding Balance": "0.00",
        "Risk Level": "low",
        "Source": "web",
        "Lineitem discount": "0.00"
    })

    # ========================================
    # SCENARIO 6: Orders with exclude SKUs
    # ========================================
    # Order 1009: Contains "07" SKU (should be excluded from packing lists)
    order_1009_items = [
        {
            "Lineitem quantity": 1,
            "Lineitem name": "Python Camo Denim - Size Large (34)",
            "Lineitem sku": "01-DM-0379-110-L",
            "Lineitem price": "45.00",
            "Lineitem discount": "0.00"
        },
        {
            "Lineitem quantity": 1,
            "Lineitem name": "Size Change Fee",
            "Lineitem sku": "07",
            "Lineitem price": "5.00",
            "Lineitem discount": "0.00"
        }
    ]

    for item in order_1009_items:
        orders_data.append({
            "Name": "#1009",
            "Email": "customer9@example.com",
            "Financial Status": "paid",
            "Fulfillment Status": "",
            "Currency": "BGN",
            "Subtotal": "50.00",
            "Shipping": "5.00",
            "Taxes": "0.00",
            "Total": "55.00",
            "Discount Code": "",
            "Discount Amount": "0.00",
            "Shipping Method": "DPD",
            "Created at": base_date.strftime("%Y-%m-%d %H:%M:%S"),
            "Lineitem quantity": item["Lineitem quantity"],
            "Lineitem name": item["Lineitem name"],
            "Lineitem sku": item["Lineitem sku"],
            "Lineitem price": item["Lineitem price"],
            "Billing Name": "Emma Davis",
            "Billing Street": "999 Style Blvd",
            "Billing City": "Plovdiv",
            "Billing Zip": "4000",
            "Billing Province": "Plovdiv",
            "Billing Country": "Bulgaria",
            "Billing Phone": "+359888789012",
            "Shipping Name": "Emma Davis",
            "Shipping Street": "999 Style Blvd",
            "Shipping City": "Plovdiv",
            "Shipping Zip": "4000",
            "Shipping Province": "Plovdiv",
            "Shipping Country": "Bulgaria",
            "Shipping Phone": "+359888789012",
            "Notes": "Size exchange",
            "Tags": "",
            "Cancelled at": "",
            "Payment Method": "Credit Card",
            "Payment Reference": "ch_3STU901",
            "Refunded Amount": "0.00",
            "Vendor": "M Cosmetics",
            "Outstanding Balance": "0.00",
            "Risk Level": "low",
            "Source": "web",
            "Lineitem discount": item["Lineitem discount"]
        })

    # Order 1010: With Shipping Protection
    order_1010_items = [
        {
            "Lineitem quantity": 2,
            "Lineitem name": "Reputation Socks - Mocha, Size S/M",
            "Lineitem sku": "03-SK-0321-074-S/M",
            "Lineitem price": "12.00",
            "Lineitem discount": "0.00"
        },
        {
            "Lineitem quantity": 1,
            "Lineitem name": "Shipping Protection",
            "Lineitem sku": "Shipping protection",
            "Lineitem price": "2.00",
            "Lineitem discount": "0.00"
        }
    ]

    for item in order_1010_items:
        orders_data.append({
            "Name": "#1010",
            "Email": "customer10@example.com",
            "Financial Status": "paid",
            "Fulfillment Status": "",
            "Currency": "BGN",
            "Subtotal": "26.00",
            "Shipping": "3.50",
            "Taxes": "0.00",
            "Total": "29.50",
            "Discount Code": "",
            "Discount Amount": "0.00",
            "Shipping Method": "PostOne",
            "Created at": base_date.strftime("%Y-%m-%d %H:%M:%S"),
            "Lineitem quantity": item["Lineitem quantity"],
            "Lineitem name": item["Lineitem name"],
            "Lineitem sku": item["Lineitem sku"],
            "Lineitem price": item["Lineitem price"],
            "Billing Name": "Olivia Martinez",
            "Billing Street": "111 Safe St",
            "Billing City": "Varna",
            "Billing Zip": "9000",
            "Billing Province": "Varna",
            "Billing Country": "Bulgaria",
            "Billing Phone": "+359888890123",
            "Shipping Name": "Olivia Martinez",
            "Shipping Street": "111 Safe St",
            "Shipping City": "Varna",
            "Shipping Zip": "9000",
            "Shipping Province": "Varna",
            "Shipping Country": "Bulgaria",
            "Shipping Phone": "+359888890123",
            "Notes": "Protected shipping",
            "Tags": "",
            "Cancelled at": "",
            "Payment Method": "PayPal",
            "Payment Reference": "PAYID-DEF789",
            "Refunded Amount": "0.00",
            "Vendor": "M Cosmetics",
            "Outstanding Balance": "0.00",
            "Risk Level": "low",
            "Source": "mobile",
            "Lineitem discount": item["Lineitem discount"]
        })

    # ========================================
    # SCENARIO 7: Edge cases
    # ========================================
    # Order 1011: Very low stock competition
    order_1011_items = [
        {
            "Lineitem quantity": 1,
            "Lineitem name": "Limited Edition Hoodie - Black, Size Small",
            "Lineitem sku": "01-HD-0341-104-S",
            "Lineitem price": "55.00",
            "Lineitem discount": "0.00"
        },
        {
            "Lineitem quantity": 1,
            "Lineitem name": "Embellish Pattern Denim - Black, Size Medium (32)",
            "Lineitem sku": "01-DM-0380-001-M",
            "Lineitem price": "48.00",
            "Lineitem discount": "0.00"
        }
    ]

    for item in order_1011_items:
        orders_data.append({
            "Name": "#1011",
            "Email": "customer11@example.com",
            "Financial Status": "paid",
            "Fulfillment Status": "",
            "Currency": "BGN",
            "Subtotal": "103.00",
            "Shipping": "5.00",
            "Taxes": "0.00",
            "Total": "108.00",
            "Discount Code": "",
            "Discount Amount": "0.00",
            "Shipping Method": "DHL",
            "Created at": base_date.strftime("%Y-%m-%d %H:%M:%S"),
            "Lineitem quantity": item["Lineitem quantity"],
            "Lineitem name": item["Lineitem name"],
            "Lineitem sku": item["Lineitem sku"],
            "Lineitem price": item["Lineitem price"],
            "Billing Name": "Liam Anderson",
            "Billing Street": "222 Rare Ave",
            "Billing City": "Sofia",
            "Billing Zip": "1202",
            "Billing Province": "Sofia",
            "Billing Country": "Bulgaria",
            "Billing Phone": "+359888901234",
            "Shipping Name": "Liam Anderson",
            "Shipping Street": "222 Rare Ave",
            "Shipping City": "Sofia",
            "Shipping Zip": "1202",
            "Shipping Province": "Sofia",
            "Shipping Country": "Bulgaria",
            "Shipping Phone": "+359888901234",
            "Notes": "Limited items",
            "Tags": "",
            "Cancelled at": "",
            "Payment Method": "Credit Card",
            "Payment Reference": "ch_3VWX234",
            "Refunded Amount": "0.00",
            "Vendor": "M Cosmetics",
            "Outstanding Balance": "0.00",
            "Risk Level": "low",
            "Source": "web",
            "Lineitem discount": item["Lineitem discount"]
        })

    # Order 1012: High priority international
    order_1012_items = [
        {
            "Lineitem quantity": 1,
            "Lineitem name": "Diamond Mind Tee, Size Small",
            "Lineitem sku": "01-DM-03-Diamond-S",
            "Lineitem price": "28.00",
            "Lineitem discount": "0.00"
        },
        {
            "Lineitem quantity": 1,
            "Lineitem name": "Athletic Dept Tee - Vintage Grey, Size Large",
            "Lineitem sku": "01-TE-0350-105-L",
            "Lineitem price": "25.00",
            "Lineitem discount": "0.00"
        }
    ]

    for item in order_1012_items:
        orders_data.append({
            "Name": "#1012",
            "Email": "urgent@example.co.uk",
            "Financial Status": "paid",
            "Fulfillment Status": "",
            "Currency": "GBP",
            "Subtotal": "53.00",
            "Shipping": "20.00",
            "Taxes": "10.60",
            "Total": "83.60",
            "Discount Code": "",
            "Discount Amount": "0.00",
            "Shipping Method": "DHL Express International",
            "Created at": base_date.strftime("%Y-%m-%d %H:%M:%S"),
            "Lineitem quantity": item["Lineitem quantity"],
            "Lineitem name": item["Lineitem name"],
            "Lineitem sku": item["Lineitem sku"],
            "Lineitem price": item["Lineitem price"],
            "Billing Name": "Oliver Thompson",
            "Billing Street": "10 Downing St",
            "Billing City": "London",
            "Billing Zip": "SW1A 2AA",
            "Billing Province": "Greater London",
            "Billing Country": "United Kingdom",
            "Billing Phone": "+442071234567",
            "Shipping Name": "Oliver Thompson",
            "Shipping Street": "10 Downing St",
            "Shipping City": "London",
            "Shipping Zip": "SW1A 2AA",
            "Shipping Province": "Greater London",
            "Shipping Country": "United Kingdom",
            "Shipping Phone": "+442071234567",
            "Notes": "URGENT - Express delivery required",
            "Tags": "Priority, International, Express",
            "Cancelled at": "",
            "Payment Method": "Credit Card",
            "Payment Reference": "ch_3YZA567",
            "Refunded Amount": "0.00",
            "Vendor": "M Cosmetics",
            "Outstanding Balance": "0.00",
            "Risk Level": "low",
            "Source": "web",
            "Lineitem discount": item["Lineitem discount"]
        })

    # Convert to DataFrame
    df = pd.DataFrame(orders_data)

    # Save to CSV
    if output_path is None:
        output_path = Path("data/test_input/comprehensive_orders.csv")
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, index=False, encoding='utf-8-sig')

    print(f"  + Created: {output_path}")
    print(f"    Total orders: {df['Name'].nunique()}")
    print(f"    Total line items: {len(df)}")
    print(f"    Date range: {df['Created at'].min()} to {df['Created at'].max()}")

    return output_path


def create_comprehensive_stock(output_path: Path = None):
    """Create comprehensive stock CSV matching all order SKUs.

    Args:
        output_path: Optional path for output CSV. Defaults to data/test_input/comprehensive_stock.csv
    """

    print("Creating comprehensive stock inventory...")

    stock_data = {
        "Артикул": [
            # High stock items (100+)
            "01-DM-0379-110-L",  # Python Camo Denim - Used in multiple orders
            "01-DM-03-Diamond-L",  # Diamond Mind Tee L
            "01-DM-03-Diamond-S",  # Diamond Mind Tee S
            "03-SK-0230-001-OS",  # R.S. Socks Black
            "01-PT-0269-066-M",  # Flare Canvas Pants

            # Medium stock items (20-50)
            "01-DM-0239-003-M",  # Flare Repaired Denim
            "01-DM-0342-104-L",  # Workwear Denim Pant
            "03-SK-0321-074-S/M",  # Reputation Socks
            "01-TE-0350-105-L",  # Athletic Dept Tee

            # Low stock items (5-15) - COMPETITION ZONE
            "01-DM-0339-006-M",  # Eyelet Flare Denim - CRITICAL (Orders #1003 + #1005 compete)
            "01-DM-0334-001-M",  # Pearl Denim Black
            "01-DM-0380-001-M",  # Embellish Pattern Denim

            # Very low stock (1-4) - NOT ENOUGH
            "01-HD-0341-104-S",  # Limited Edition Hoodie - INSUFFICIENT (Orders #1006 + #1011 compete)

            # Exclude SKUs - High stock
            "07",  # Fee SKU
            "Shipping protection",  # Protection SKU
        ],
        "Име": [
            # High stock
            "Python Camo Denim - Size Large (34)",
            "Diamond Mind Tee, Size Large",
            "Diamond Mind Tee, Size Small",
            "R.S. Socks - Black",
            "Flare Canvas Pants - Taupe, Size Medium (32)",

            # Medium stock
            "Flare Repaired Denim - Cream Wash, Size Medium",
            "Workwear Denim Pant, Size Large (34)",
            "Reputation Socks - Mocha, Size S/M",
            "Athletic Dept Tee - Vintage Grey, Size Large",

            # Low stock
            "Eyelet Flare Denim, Size Medium (32)",
            "Pearl Denim - Black, Size Medium (32)",
            "Embellish Pattern Denim - Black, Size Medium (32)",

            # Very low stock
            "Limited Edition Hoodie - Black, Size Small",

            # Exclude SKUs
            "Size Change Fee",
            "Shipping Protection Service",
        ],
        "Наличност": [
            # High stock (150-250)
            200,  # Python Camo Denim - enough for all
            100,  # Diamond Mind L
            80,   # Diamond Mind S
            150,  # Socks
            120,  # Canvas Pants

            # Medium stock (25-60)
            50,   # Flare Repaired
            45,   # Workwear Denim
            60,   # Reputation Socks
            35,   # Athletic Tee

            # Low stock (4-12) - CRITICAL ZONE
            4,    # Eyelet Flare - Orders want 2+3=5, only 4 available!
            10,   # Pearl Denim
            8,    # Embellish Pattern

            # Very low (1-3) - NOT ENOUGH
            2,    # Limited Hoodie - Orders want 5+1=6, only 2 available!

            # Exclude - Always high
            999,  # Fee
            999,  # Protection
        ]
    }

    df = pd.DataFrame(stock_data)

    # Save to CSV
    if output_path is None:
        output_path = Path("data/test_input/comprehensive_stock.csv")
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, index=False, sep=";", encoding='utf-8-sig')

    print(f"  + Created: {output_path}")
    print(f"    Total SKUs: {len(df)}")
    print(f"    Total stock quantity: {df['Наличност'].sum()}")
    print(f"    Low stock items (<=15): {len(df[df['Наличност'] <= 15])}")

    return output_path


if __name__ == "__main__":
    print("=" * 70)
    print("CREATING COMPREHENSIVE TEST DATA")
    print("=" * 70)
    print()

    try:
        create_comprehensive_orders()
        print()
        create_comprehensive_stock()

        print()
        print("=" * 70)
        print("✅ COMPREHENSIVE TEST DATA CREATED SUCCESSFULLY")
        print("=" * 70)
        print()
        print("Files created:")
        print("  - data/test_input/comprehensive_orders.csv")
        print("  - data/test_input/comprehensive_stock.csv")
        print()
        print("Next steps:")
        print("  1. Review TEST_SCENARIOS.md for expected results")
        print("  2. Run TESTING_CHECKLIST.md to verify all functionality")
        print("  3. Use these files in Shopify Tool for analysis")
        print()

    except Exception as e:
        print(f"\n❌ Error creating comprehensive test data: {e}")
        import traceback
        traceback.print_exc()
