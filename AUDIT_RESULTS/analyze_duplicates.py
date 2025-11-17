#!/usr/bin/env python3
"""Script to find code duplication patterns in the codebase."""

import os
import re
from pathlib import Path
from typing import List, Dict, Set
from difflib import SequenceMatcher


def normalize_code(code: str) -> str:
    """Normalize code for comparison by removing comments and extra whitespace."""
    # Remove comments
    code = re.sub(r'#.*$', '', code, flags=re.MULTILINE)
    # Remove docstrings
    code = re.sub(r'""".*?"""', '', code, flags=re.DOTALL)
    code = re.sub(r"'''.*?'''", '', code, flags=re.DOTALL)
    # Normalize whitespace
    code = re.sub(r'\s+', ' ', code)
    return code.strip()


def find_pattern_in_files(pattern: str, min_occurrence: int = 2) -> List[Dict]:
    """Find specific code patterns across files."""
    results = []
    directories = ['shopify_tool', 'gui', 'shared']

    for directory in directories:
        if not os.path.exists(directory):
            continue

        for py_file in Path(directory).rglob('*.py'):
            if '__pycache__' in str(py_file):
                continue

            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()

                # Count pattern occurrences
                matches = list(re.finditer(pattern, content, re.MULTILINE))
                if matches:
                    for match in matches:
                        # Find line number
                        line_num = content[:match.start()].count('\n') + 1
                        results.append({
                            'file': str(py_file),
                            'line': line_num,
                            'match': match.group(0)
                        })

            except Exception as e:
                print(f"Error reading {py_file}: {e}")

    return results


def find_file_locking_patterns():
    """Find file locking patterns."""
    # Look for common file locking patterns
    pattern = r'with\s+FileLock\([^)]+\):'
    return find_pattern_in_files(pattern)


def find_json_operations():
    """Find JSON load/save patterns."""
    results = {
        'load': find_pattern_in_files(r'json\.load\('),
        'dump': find_pattern_in_files(r'json\.dump\('),
        'loads': find_pattern_in_files(r'json\.loads\('),
        'dumps': find_pattern_in_files(r'json\.dumps\(')
    }
    return results


def find_dataframe_validations():
    """Find DataFrame column validation patterns."""
    patterns = {
        'required_columns': find_pattern_in_files(r'required_columns\s*='),
        'missing_cols': find_pattern_in_files(r'missing_cols\s*='),
        'column_check': find_pattern_in_files(r'if.*not in.*columns'),
    }
    return patterns


def find_try_except_patterns():
    """Find error handling patterns."""
    patterns = {
        'broad_except': find_pattern_in_files(r'except\s+Exception\s*:'),
        'bare_except': find_pattern_in_files(r'except\s*:'),
        'specific_except': find_pattern_in_files(r'except\s+\w+Error\s*:'),
    }
    return patterns


def find_logger_patterns():
    """Find logger usage patterns."""
    patterns = {
        'getLogger': find_pattern_in_files(r'logger\s*=\s*logging\.getLogger'),
        'debug': find_pattern_in_files(r'logger\.debug\('),
        'info': find_pattern_in_files(r'logger\.info\('),
        'warning': find_pattern_in_files(r'logger\.warning\('),
        'error': find_pattern_in_files(r'logger\.error\('),
    }
    return patterns


def analyze_similar_functions():
    """Find potentially duplicate function definitions."""
    function_signatures = {}
    directories = ['shopify_tool', 'gui', 'shared']

    for directory in directories:
        if not os.path.exists(directory):
            continue

        for py_file in Path(directory).rglob('*.py'):
            if '__pycache__' in str(py_file):
                continue

            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()

                # Find function definitions
                func_pattern = r'^\s*def\s+(\w+)\s*\([^)]*\):'
                for match in re.finditer(func_pattern, content, re.MULTILINE):
                    func_name = match.group(1)
                    if func_name not in function_signatures:
                        function_signatures[func_name] = []
                    function_signatures[func_name].append(str(py_file))

            except Exception as e:
                print(f"Error reading {py_file}: {e}")

    # Find functions with same names in different files (potential duplicates)
    duplicates = {name: files for name, files in function_signatures.items()
                  if len(files) > 1 and not name.startswith('_')}

    return duplicates


def main():
    """Main analysis function."""
    print("# Code Duplication Analysis\n")

    # File Locking Patterns
    print("## 1. File Locking Patterns\n")
    file_locks = find_file_locking_patterns()
    if file_locks:
        print(f"**Found:** {len(file_locks)} occurrences\n")
        print("**Locations:**")
        for lock in file_locks[:10]:  # Show first 10
            print(f"- {lock['file']}:{lock['line']}")
        if len(file_locks) > 10:
            print(f"- ... and {len(file_locks) - 10} more\n")
        print("\n**Recommendation:** 🟡 Consider creating `shared/file_lock_utils.py` with reusable locking context managers")
        print("**Priority:** MEDIUM\n")
    else:
        print("No file locking patterns found.\n")

    # JSON Operations
    print("## 2. JSON Operations\n")
    json_ops = find_json_operations()
    total_json = sum(len(ops) for ops in json_ops.values())
    print(f"**Total JSON operations:** {total_json}\n")
    for op_type, ops in json_ops.items():
        if ops:
            print(f"### `json.{op_type}()` - {len(ops)} occurrences")
            # Group by file
            files = {}
            for op in ops:
                file = op['file']
                if file not in files:
                    files[file] = 0
                files[file] += 1
            for file, count in sorted(files.items(), key=lambda x: x[1], reverse=True)[:5]:
                print(f"- {file}: {count} times")
    print("\n**Recommendation:** 🟢 JSON operations are varied, but consider utility functions for common patterns")
    print("**Priority:** LOW\n")

    # DataFrame Validations
    print("## 3. DataFrame Column Validation Patterns\n")
    df_patterns = find_dataframe_validations()
    total_df = sum(len(patterns) for patterns in df_patterns.values())
    if total_df > 0:
        print(f"**Total validation patterns:** {total_df}\n")
        for pattern_type, patterns in df_patterns.items():
            if patterns:
                print(f"### {pattern_type} - {len(patterns)} occurrences")
                files = set(p['file'] for p in patterns)
                for file in sorted(files)[:5]:
                    count = sum(1 for p in patterns if p['file'] == file)
                    print(f"- {file}: {count} times")
                print()
        print("**Recommendation:** 🟡 Create `shopify_tool/dataframe_validators.py` with common validation patterns")
        print("**Priority:** MEDIUM\n")
    else:
        print("No DataFrame validation patterns found.\n")

    # Error Handling
    print("## 4. Error Handling Patterns\n")
    error_patterns = find_try_except_patterns()
    for pattern_type, patterns in error_patterns.items():
        if patterns:
            print(f"### {pattern_type} - {len(patterns)} occurrences")
            files = {}
            for p in patterns:
                file = p['file']
                if file not in files:
                    files[file] = []
                files[file].append(p['line'])

            for file, lines in sorted(files.items())[:10]:
                print(f"- {file}: lines {', '.join(map(str, sorted(lines)[:5]))}")
                if len(lines) > 5:
                    print(f"  ... and {len(lines) - 5} more")
            print()

    if error_patterns['broad_except']:
        print("**⚠️ Warning:** Found broad `except Exception:` blocks")
        print("**Recommendation:** 🔴 Replace with specific exception types where possible")
        print("**Priority:** HIGH\n")

    if error_patterns['bare_except']:
        print("**⚠️ Warning:** Found bare `except:` blocks (catches everything including KeyboardInterrupt)")
        print("**Recommendation:** 🔴 Replace with specific exception types")
        print("**Priority:** CRITICAL\n")

    # Logger Patterns
    print("## 5. Logger Initialization Patterns\n")
    logger_patterns = find_logger_patterns()
    if logger_patterns['getLogger']:
        print(f"**Found:** {len(logger_patterns['getLogger'])} logger initializations\n")
        files = set(p['file'] for p in logger_patterns['getLogger'])
        print(f"**Files with loggers:** {len(files)}\n")
        print("**Logger usage breakdown:**")
        for level in ['debug', 'info', 'warning', 'error']:
            count = len(logger_patterns[level])
            print(f"- logger.{level}(): {count} calls")
        print("\n**Recommendation:** ✅ Consistent logger usage detected")
        print("**Priority:** LOW - No action needed\n")

    # Similar Function Names
    print("## 6. Functions with Same Names (Potential Duplicates)\n")
    similar_funcs = analyze_similar_functions()
    if similar_funcs:
        print(f"**Found:** {len(similar_funcs)} function names appearing in multiple files\n")
        # Sort by number of occurrences
        sorted_funcs = sorted(similar_funcs.items(), key=lambda x: len(x[1]), reverse=True)
        for func_name, files in sorted_funcs[:15]:  # Top 15
            if len(files) > 2:  # Show functions in 3+ files
                print(f"### `{func_name}()` - {len(files)} locations")
                for file in sorted(files)[:5]:
                    print(f"- {file}")
                if len(files) > 5:
                    print(f"- ... and {len(files) - 5} more")
                print()

        print("\n**Recommendation:** 🟡 Review these functions - some may be legitimate, others may benefit from consolidation")
        print("**Priority:** MEDIUM\n")

    # Summary
    print("\n## Summary of Duplication Issues\n")
    print("| Pattern Type | Occurrences | Priority | Action Needed |")
    print("|--------------|-------------|----------|---------------|")
    print(f"| File Locking | {len(file_locks)} | 🟡 MEDIUM | Create utility module |")
    print(f"| JSON Operations | {total_json} | 🟢 LOW | Consider utility functions |")
    print(f"| DataFrame Validations | {total_df} | 🟡 MEDIUM | Create validator module |")
    print(f"| Broad Exception Catching | {len(error_patterns['broad_except'])} | 🔴 HIGH | Use specific exceptions |")
    print(f"| Bare Exception Catching | {len(error_patterns['bare_except'])} | 🔴 CRITICAL | Use specific exceptions |")
    print(f"| Duplicate Function Names | {len(similar_funcs)} | 🟡 MEDIUM | Review and consolidate |")


if __name__ == '__main__':
    main()
