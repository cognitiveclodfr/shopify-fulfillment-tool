#!/usr/bin/env python3
"""Test delimiter detection for different CSV files."""

import pandas as pd
import csv

def test_pandas_autodetect():
    """Test pandas auto-detection with sep=None."""
    print("=" * 80)
    print("Testing Pandas Auto-Detection (sep=None, engine='python')")
    print("=" * 80)

    files = [
        ("test_comma.csv", "Comma-separated"),
        ("test_semicolon.csv", "Semicolon-separated"),
        ("test_tab.csv", "Tab-separated")
    ]

    for filename, description in files:
        print(f"\n{description}: {filename}")
        try:
            df = pd.read_csv(filename, sep=None, engine='python')
            print(f"  ✓ Loaded successfully")
            print(f"  Shape: {df.shape}")
            print(f"  Columns: {list(df.columns)[:3]}...")
        except Exception as e:
            print(f"  ✗ Failed: {e}")

def test_csv_sniffer():
    """Test csv.Sniffer for delimiter detection."""
    print("\n" + "=" * 80)
    print("Testing csv.Sniffer")
    print("=" * 80)

    files = [
        ("test_comma.csv", "Comma-separated"),
        ("test_semicolon.csv", "Semicolon-separated"),
        ("test_tab.csv", "Tab-separated")
    ]

    for filename, description in files:
        print(f"\n{description}: {filename}")
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                sample = f.read(1024)
                sniffer = csv.Sniffer()
                dialect = sniffer.sniff(sample)
                delimiter = dialect.delimiter

                # Convert tab to visible representation
                delimiter_display = repr(delimiter) if delimiter == '\t' else delimiter
                print(f"  ✓ Detected delimiter: {delimiter_display}")

                # Verify by loading with pandas
                df = pd.read_csv(filename, delimiter=delimiter)
                print(f"  Shape: {df.shape}")
                print(f"  Columns: {list(df.columns)[:3]}...")
        except Exception as e:
            print(f"  ✗ Failed: {e}")

def test_manual_detection():
    """Test manual delimiter detection by counting occurrences."""
    print("\n" + "=" * 80)
    print("Testing Manual Detection (count occurrences)")
    print("=" * 80)

    files = [
        ("test_comma.csv", "Comma-separated"),
        ("test_semicolon.csv", "Semicolon-separated"),
        ("test_tab.csv", "Tab-separated")
    ]

    for filename, description in files:
        print(f"\n{description}: {filename}")
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                first_line = f.readline()
                counts = {
                    ',': first_line.count(','),
                    ';': first_line.count(';'),
                    '\t': first_line.count('\t'),
                    '|': first_line.count('|')
                }

                print(f"  Delimiter counts: {counts}")
                detected = max(counts, key=counts.get)
                detected_display = repr(detected) if detected == '\t' else detected
                print(f"  ✓ Detected delimiter: {detected_display}")

                # Verify
                df = pd.read_csv(filename, delimiter=detected)
                print(f"  Shape: {df.shape}")
                print(f"  Columns: {list(df.columns)[:3]}...")
        except Exception as e:
            print(f"  ✗ Failed: {e}")

def test_current_implementation():
    """Test current hardcoded implementation."""
    print("\n" + "=" * 80)
    print("Testing Current Implementation (hardcoded delimiters)")
    print("=" * 80)

    # Simulate current behavior
    tests = [
        ("test_comma.csv", ",", "Orders file (comma)"),
        ("test_semicolon.csv", ";", "Stock file (semicolon)"),
        ("test_comma.csv", ";", "WRONG: comma file with semicolon delimiter"),
        ("test_semicolon.csv", ",", "WRONG: semicolon file with comma delimiter"),
    ]

    for filename, delimiter, description in tests:
        print(f"\n{description}")
        print(f"  File: {filename}, Delimiter: '{delimiter}'")
        try:
            df = pd.read_csv(filename, delimiter=delimiter)
            print(f"  ✓ Loaded")
            print(f"  Shape: {df.shape}")
            print(f"  Columns: {list(df.columns)[:3]}...")

            # Check if it loaded correctly (more than 1 column expected)
            if df.shape[1] == 1:
                print(f"  ⚠️  WARNING: Only 1 column detected - likely wrong delimiter!")
        except Exception as e:
            print(f"  ✗ Failed: {e}")

if __name__ == "__main__":
    test_pandas_autodetect()
    test_csv_sniffer()
    test_manual_detection()
    test_current_implementation()

    print("\n" + "=" * 80)
    print("Summary")
    print("=" * 80)
    print("✓ Pandas sep=None: Works well, automatic detection")
    print("✓ csv.Sniffer: Works well, standard library")
    print("✓ Manual counting: Simple and reliable for most cases")
    print("✗ Current implementation: Hardcoded, fails with wrong delimiter")
