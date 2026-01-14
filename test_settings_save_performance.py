#!/usr/bin/env python3
"""
Performance Test: Settings Save with 70+ Sets

This script measures the performance characteristics of saving a configuration
with 70+ set decoders to diagnose the save failure issue.

Metrics measured:
- JSON serialization time
- JSON string size (bytes)
- File write time
- Atomic rename time
- Total save time
"""

import json
import time
import tempfile
import shutil
from pathlib import Path
from datetime import datetime


def generate_large_config(num_sets=70, components_per_set=5):
    """Generate a realistic config with many sets."""
    config = {
        "client_id": "TEST",
        "client_name": "Test Client",
        "created_at": datetime.now().isoformat(),

        "column_mappings": {
            "version": 2,
            "orders": {
                "Name": "Order_Number",
                "Lineitem sku": "SKU",
                "Lineitem quantity": "Quantity",
                "Lineitem name": "Product_Name",
                "Shipping Method": "Shipping_Method",
                "Shipping Country": "Shipping_Country",
                "Tags": "Tags",
                "Notes": "Notes",
                "Total": "Total_Price"
            },
            "stock": {
                "Артикул": "SKU",
                "Име": "Product_Name",
                "Наличност": "Stock"
            }
        },

        "courier_mappings": {
            "DHL": {
                "patterns": ["dhl", "dhl express", "dhl_express"],
                "case_sensitive": False
            },
            "DPD": {
                "patterns": ["dpd", "dpd bulgaria"],
                "case_sensitive": False
            },
            "Speedy": {
                "patterns": ["speedy"],
                "case_sensitive": False
            }
        },

        "settings": {
            "low_stock_threshold": 5,
            "stock_csv_delimiter": ";",
            "orders_csv_delimiter": ","
        },

        "rules": [],
        "order_rules": [],
        "packing_list_configs": [],
        "stock_export_configs": [],
        "packaging_rules": [],

        # Generate many sets
        "set_decoders": {
            f"SET-{i:03d}": [
                {
                    "sku": f"COMP-{i:03d}-{j:02d}",
                    "quantity": 1
                }
                for j in range(components_per_set)
            ]
            for i in range(num_sets)
        },

        "tag_categories": {
            "packaging": {
                "label": "Packaging",
                "color": "#4CAF50",
                "tags": ["SMALL_BAG", "LARGE_BAG", "BOX", "NO_BOX", "BOX+ANY"]
            },
            "priority": {
                "label": "Priority",
                "color": "#FF9800",
                "tags": ["URGENT", "HIGH_VALUE", "DOUBLE_TRACK"]
            },
            "status": {
                "label": "Status",
                "color": "#2196F3",
                "tags": ["CHECKED", "PROBLEM", "VERIFIED"]
            },
            "custom": {
                "label": "Custom",
                "color": "#9E9E9E",
                "tags": []
            }
        }
    }

    return config


def measure_json_serialization(config):
    """Measure JSON serialization time and size."""
    print("\n📊 JSON Serialization Metrics:")
    print("=" * 60)

    # Measure serialization time
    start = time.perf_counter()
    json_str = json.dumps(config, indent=2, ensure_ascii=False)
    duration_ms = (time.perf_counter() - start) * 1000

    # Measure size
    size_bytes = len(json_str.encode('utf-8'))
    size_kb = size_bytes / 1024

    print(f"  JSON Size: {size_bytes:,} bytes ({size_kb:.2f} KB)")
    print(f"  Serialization Time: {duration_ms:.2f} ms")

    return json_str, size_bytes, duration_ms


def measure_file_write(json_str, test_dir):
    """Measure file write performance (temp file + atomic rename)."""
    print("\n💾 File Write Metrics:")
    print("=" * 60)

    final_path = test_dir / "shopify_config.json"
    temp_path = test_dir / "shopify_config.json.tmp"

    # Measure temp file write
    write_start = time.perf_counter()
    with open(temp_path, 'w', encoding='utf-8') as f:
        f.write(json_str)
    write_duration_ms = (time.perf_counter() - write_start) * 1000

    print(f"  Temp File Write Time: {write_duration_ms:.2f} ms")

    # Measure atomic rename
    rename_start = time.perf_counter()
    shutil.move(str(temp_path), str(final_path))
    rename_duration_ms = (time.perf_counter() - rename_start) * 1000

    print(f"  Atomic Rename Time: {rename_duration_ms:.2f} ms")

    # Verify file
    if final_path.exists():
        actual_size = final_path.stat().st_size
        print(f"  Written File Size: {actual_size:,} bytes")

    return write_duration_ms, rename_duration_ms


def simulate_windows_lock_save(config, test_dir):
    """Simulate the actual _save_with_windows_lock method."""
    print("\n🔒 Simulated Windows Lock Save:")
    print("=" * 60)

    import msvcrt

    final_path = test_dir / "shopify_config_locked.json"
    temp_path = test_dir / "shopify_config_locked.json.tmp"

    total_start = time.perf_counter()

    try:
        with open(temp_path, 'w', encoding='utf-8') as f:
            # Try to acquire lock
            lock_start = time.perf_counter()
            try:
                msvcrt.locking(f.fileno(), msvcrt.LK_NBLCK, 1)
                lock_duration_ms = (time.perf_counter() - lock_start) * 1000
                print(f"  Lock Acquired: {lock_duration_ms:.2f} ms")
            except IOError as e:
                print(f"  ❌ Lock Failed: {e}")
                return None

            try:
                # Write JSON
                write_start = time.perf_counter()
                json.dump(config, f, indent=2, ensure_ascii=False)
                write_duration_ms = (time.perf_counter() - write_start) * 1000
                print(f"  JSON Write Time: {write_duration_ms:.2f} ms")
            finally:
                # Unlock
                unlock_start = time.perf_counter()
                msvcrt.locking(f.fileno(), msvcrt.LK_UNLCK, 1)
                unlock_duration_ms = (time.perf_counter() - unlock_start) * 1000
                print(f"  Lock Released: {unlock_duration_ms:.2f} ms")

        # Atomic move
        rename_start = time.perf_counter()
        shutil.move(str(temp_path), str(final_path))
        rename_duration_ms = (time.perf_counter() - rename_start) * 1000
        print(f"  Atomic Rename Time: {rename_duration_ms:.2f} ms")

        total_duration_ms = (time.perf_counter() - total_start) * 1000
        print(f"  Total Save Time: {total_duration_ms:.2f} ms")

        return total_duration_ms

    except Exception as e:
        print(f"  ❌ Save Failed: {e}")
        if temp_path.exists():
            temp_path.unlink()
        return None


def test_multiple_sizes():
    """Test with different numbers of sets to find the breaking point."""
    print("\n🔬 Testing Multiple Configuration Sizes:")
    print("=" * 60)

    test_sizes = [10, 30, 50, 70, 100, 150]
    results = []

    for num_sets in test_sizes:
        print(f"\n  Testing {num_sets} sets...")
        config = generate_large_config(num_sets=num_sets, components_per_set=5)

        # Measure serialization
        json_str = json.dumps(config, indent=2, ensure_ascii=False)
        size_kb = len(json_str.encode('utf-8')) / 1024

        start = time.perf_counter()
        json.dumps(config, indent=2, ensure_ascii=False)
        duration_ms = (time.perf_counter() - start) * 1000

        results.append({
            "sets": num_sets,
            "size_kb": size_kb,
            "time_ms": duration_ms
        })

        print(f"    Size: {size_kb:.2f} KB, Time: {duration_ms:.2f} ms")

    return results


def main():
    """Run all performance tests."""
    print("=" * 60)
    print("🔍 Settings Save Performance Test - 70+ Sets")
    print("=" * 60)

    # Test with 70 sets (the problematic case)
    num_sets = 70
    components_per_set = 5

    print(f"\n📦 Configuration:")
    print(f"  Number of Sets: {num_sets}")
    print(f"  Components per Set: {components_per_set}")
    print(f"  Total Components: {num_sets * components_per_set}")

    # Generate config
    print("\n⏱️  Generating configuration...")
    config = generate_large_config(num_sets, components_per_set)

    # Test 1: JSON Serialization
    json_str, size_bytes, serial_time_ms = measure_json_serialization(config)

    # Test 2: File Write (without lock)
    with tempfile.TemporaryDirectory() as tmpdir:
        test_dir = Path(tmpdir)
        write_time_ms, rename_time_ms = measure_file_write(json_str, test_dir)

    # Test 3: Full Windows Lock Save (if on Windows)
    import platform
    if platform.system() == 'Windows':
        with tempfile.TemporaryDirectory() as tmpdir:
            test_dir = Path(tmpdir)
            total_save_ms = simulate_windows_lock_save(config, test_dir)
    else:
        print("\n⚠️  Not on Windows - skipping msvcrt lock test")
        total_save_ms = None

    # Test 4: Multiple sizes
    size_results = test_multiple_sizes()

    # Summary
    print("\n\n" + "=" * 60)
    print("📋 SUMMARY - 70 Sets Configuration")
    print("=" * 60)
    print(f"  JSON Size: {size_bytes:,} bytes ({size_bytes/1024:.2f} KB)")
    print(f"  Serialization: {serial_time_ms:.2f} ms")
    print(f"  File Write: {write_time_ms:.2f} ms")
    print(f"  Atomic Rename: {rename_time_ms:.2f} ms")
    if total_save_ms:
        print(f"  Total Save (with lock): {total_save_ms:.2f} ms")

    print("\n📊 Size vs Time Analysis:")
    print("-" * 60)
    for result in size_results:
        print(f"  {result['sets']:3d} sets: {result['size_kb']:6.2f} KB, {result['time_ms']:6.2f} ms")

    # Find potential bottlenecks
    print("\n\n" + "=" * 60)
    print("⚠️  POTENTIAL BOTTLENECKS")
    print("=" * 60)

    if size_bytes > 100 * 1024:  # > 100 KB
        print("  ⚠️  File size is large (>100KB)")
        print("      → May cause issues with Windows file locking")

    if serial_time_ms > 100:  # > 100ms
        print("  ⚠️  JSON serialization is slow (>100ms)")
        print("      → Consider optimizing indent or disabling ensure_ascii")

    if write_time_ms > 200:  # > 200ms
        print("  ⚠️  File write is slow (>200ms)")
        print("      → Possible network/disk latency issue")

    print("\n✅ Test completed!")


if __name__ == "__main__":
    main()
