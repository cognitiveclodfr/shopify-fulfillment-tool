#!/usr/bin/env python3
"""Script to find potential performance issues."""

import ast
import os
import re
from pathlib import Path
from typing import List, Dict


class PerformanceDetector(ast.NodeVisitor):
    """AST visitor to detect potential performance issues."""

    def __init__(self, filepath: str, content: str):
        self.filepath = filepath
        self.content = content
        self.issues = []
        self.in_loop = 0
        self.loop_depth = 0

    def visit_For(self, node):
        """Track for loops."""
        self.in_loop += 1
        self.loop_depth += 1

        # Check for DataFrame.iterrows() usage
        if isinstance(node.iter, ast.Call):
            if isinstance(node.iter.func, ast.Attribute):
                if node.iter.func.attr == 'iterrows':
                    self.issues.append({
                        'type': 'df_iterrows',
                        'severity': 'HIGH',
                        'line': node.lineno,
                        'message': 'Using DataFrame.iterrows() - consider vectorized operations instead'
                    })
                elif node.iter.func.attr == 'itertuples':
                    self.issues.append({
                        'type': 'df_itertuples',
                        'severity': 'MEDIUM',
                        'line': node.lineno,
                        'message': 'Using DataFrame.itertuples() - consider vectorized operations if possible'
                    })

        # Check for nested loops (O(n²) or worse)
        if self.loop_depth >= 3:
            self.issues.append({
                'type': 'nested_loops',
                'severity': 'HIGH',
                'line': node.lineno,
                'message': f'Deeply nested loops (depth: {self.loop_depth}) - potential O(n^{self.loop_depth}) complexity'
            })

        self.generic_visit(node)
        self.in_loop -= 1
        self.loop_depth -= 1

    def visit_While(self, node):
        """Track while loops."""
        self.in_loop += 1
        self.loop_depth += 1
        self.generic_visit(node)
        self.in_loop -= 1
        self.loop_depth -= 1

    def visit_Call(self, node):
        """Check for performance-related function calls."""
        if isinstance(node.func, ast.Attribute):
            # File I/O in loops
            if self.in_loop > 0:
                if node.func.attr in ['open', 'read', 'write', 'load', 'dump']:
                    self.issues.append({
                        'type': 'io_in_loop',
                        'severity': 'HIGH',
                        'line': node.lineno,
                        'message': f'File I/O operation ({node.func.attr}) inside loop - consider batching'
                    })

            # String concatenation in loops
            if self.in_loop > 0:
                if node.func.attr in ['append'] and isinstance(node.func.value, ast.Name):
                    # Check if it's string concatenation pattern
                    self.issues.append({
                        'type': 'append_in_loop',
                        'severity': 'MEDIUM',
                        'line': node.lineno,
                        'message': 'List append in loop - ensure not used for string building (use join instead)'
                    })

        elif isinstance(node.func, ast.Name):
            # Check for open() in loops
            if self.in_loop > 0 and node.func.id == 'open':
                self.issues.append({
                    'type': 'io_in_loop',
                    'severity': 'HIGH',
                    'line': node.lineno,
                    'message': 'File open() inside loop - consider batching operations'
                })

        self.generic_visit(node)

    def visit_BinOp(self, node):
        """Check for string concatenation."""
        if self.in_loop > 0:
            if isinstance(node.op, ast.Add):
                # Check if it might be string concatenation
                if isinstance(node.left, ast.Constant) or isinstance(node.right, ast.Constant):
                    self.issues.append({
                        'type': 'string_concat_in_loop',
                        'severity': 'MEDIUM',
                        'line': node.lineno,
                        'message': 'Potential string concatenation in loop - use join() or list for better performance'
                    })

        self.generic_visit(node)


def find_large_data_operations(filepath: Path) -> List[Dict]:
    """Find operations that might be memory-intensive."""
    issues = []

    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
            lines = content.split('\n')

        # Look for patterns that might indicate memory issues
        patterns = [
            (r'\.copy\(\)', 'DataFrame.copy()', 'MEDIUM', 'DataFrame copy operation - ensure necessary'),
            (r'pd\.concat\(', 'pd.concat()', 'MEDIUM', 'Concatenation - ensure not in loop'),
            (r'\.merge\(', 'DataFrame.merge()', 'MEDIUM', 'Merge operation - verify data size'),
            (r'\.read_csv\([^)]*\)', 'pd.read_csv()', 'LOW', 'CSV reading - consider chunking for large files'),
        ]

        for i, line in enumerate(lines, 1):
            for pattern, operation, severity, message in patterns:
                if re.search(pattern, line):
                    issues.append({
                        'type': 'large_data_op',
                        'severity': severity,
                        'line': i,
                        'operation': operation,
                        'message': message
                    })

    except Exception as e:
        print(f"Error analyzing {filepath}: {e}")

    return issues


def analyze_file_performance(filepath: Path) -> List[Dict]:
    """Analyze a single file for performance issues."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()

        tree = ast.parse(content, filename=str(filepath))
        detector = PerformanceDetector(str(filepath), content)
        detector.visit(tree)

        # Add large data operations
        large_data_issues = find_large_data_operations(filepath)
        detector.issues.extend(large_data_issues)

        return detector.issues

    except SyntaxError:
        return []
    except Exception as e:
        print(f"Error analyzing {filepath}: {e}")
        return []


def main():
    """Main analysis function."""
    print("# Performance Issues Analysis\n")

    # Collect all issues
    all_issues = []
    directories = ['shopify_tool', 'gui', 'shared']

    for directory in directories:
        if not os.path.exists(directory):
            continue

        for py_file in Path(directory).rglob('*.py'):
            if '__pycache__' in str(py_file):
                continue

            issues = analyze_file_performance(py_file)
            for issue in issues:
                issue['filepath'] = str(py_file)
            all_issues.extend(issues)

    # Group by severity
    critical_issues = [i for i in all_issues if i['severity'] == 'CRITICAL']
    high_issues = [i for i in all_issues if i['severity'] == 'HIGH']
    medium_issues = [i for i in all_issues if i['severity'] == 'MEDIUM']
    low_issues = [i for i in all_issues if i['severity'] == 'LOW']

    print(f"## Summary\n")
    print(f"**Total Performance Issues Found:** {len(all_issues)}\n")
    print(f"- 🔴 **CRITICAL:** {len(critical_issues)}")
    print(f"- 🔴 **HIGH:** {len(high_issues)}")
    print(f"- 🟡 **MEDIUM:** {len(medium_issues)}")
    print(f"- 🟢 **LOW:** {len(low_issues)}")
    print()

    # High Priority Issues
    if high_issues:
        print("## 🔴 HIGH Priority Performance Issues\n")

        # Group by type
        by_type = {}
        for issue in high_issues:
            issue_type = issue['type']
            if issue_type not in by_type:
                by_type[issue_type] = []
            by_type[issue_type].append(issue)

        for issue_type, issues in by_type.items():
            print(f"### {issue_type.replace('_', ' ').title()} ({len(issues)} occurrences)\n")

            if issue_type == 'df_iterrows':
                print("**Problem:** `DataFrame.iterrows()` is very slow for large DataFrames\n")
                print("**Solution:** Use vectorized operations or `.apply()` method\n")
                print("**Example:**")
                print("```python")
                print("# Bad")
                print("for idx, row in df.iterrows():")
                print("    df.at[idx, 'new_col'] = row['col1'] + row['col2']")
                print()
                print("# Good")
                print("df['new_col'] = df['col1'] + df['col2']")
                print("```\n")

            elif issue_type == 'io_in_loop':
                print("**Problem:** File I/O operations in loops are very slow\n")
                print("**Solution:** Batch operations or collect data first, then write once\n")

            elif issue_type == 'nested_loops':
                print("**Problem:** Nested loops can have exponential time complexity\n")
                print("**Solution:** Consider using dictionaries/sets for lookups, or vectorized operations\n")

            print("**Occurrences:**")
            for issue in issues[:15]:
                print(f"- `{issue['filepath']}:{issue['line']}` - {issue['message']}")
            if len(issues) > 15:
                print(f"- ... and {len(issues) - 15} more")
            print()

    # Medium Priority Issues
    if medium_issues:
        print("## 🟡 MEDIUM Priority Performance Issues\n")

        by_type = {}
        for issue in medium_issues:
            issue_type = issue['type']
            if issue_type not in by_type:
                by_type[issue_type] = []
            by_type[issue_type].append(issue)

        for issue_type, issues in by_type.items():
            print(f"### {issue_type.replace('_', ' ').title()} ({len(issues)} occurrences)\n")

            if issue_type == 'df_itertuples':
                print("**Note:** `.itertuples()` is faster than `.iterrows()` but vectorized ops are still better\n")
            elif issue_type == 'string_concat_in_loop':
                print("**Problem:** String concatenation in loops creates many intermediate objects\n")
                print("**Solution:** Use `''.join(list)` or accumulate in a list\n")
            elif issue_type == 'large_data_op':
                print("**Note:** These operations can be memory-intensive with large datasets\n")

            # Show counts by file
            files = {}
            for issue in issues:
                file = issue['filepath']
                if file not in files:
                    files[file] = 0
                files[file] += 1

            print("**Files with most occurrences:**")
            for file, count in sorted(files.items(), key=lambda x: x[1], reverse=True)[:10]:
                print(f"- `{file}`: {count} occurrences")
            print()

    # Low Priority Issues
    if low_issues:
        print("## 🟢 LOW Priority Performance Notes\n")

        by_type = {}
        for issue in low_issues:
            issue_type = issue['type']
            if issue_type not in by_type:
                by_type[issue_type] = []
            by_type[issue_type].append(issue)

        for issue_type, issues in by_type.items():
            print(f"### {issue_type.replace('_', ' ').title()}: {len(issues)} occurrences\n")

    # Recommendations
    print("\n## Performance Optimization Recommendations\n")

    print("### 🔴 Immediate Actions\n")
    if high_issues:
        print("1. **Replace DataFrame.iterrows()** with vectorized operations")
        print("2. **Move file I/O outside of loops** - batch read/write operations")
        print("3. **Optimize nested loops** - use dictionaries for O(1) lookups")
        print()
    else:
        print("✅ No critical performance issues detected\n")

    print("### 🟡 Recommended Improvements\n")
    if medium_issues:
        print("1. **Review DataFrame operations** - ensure they're necessary")
        print("2. **Check string building in loops** - use join() where appropriate")
        print("3. **Consider chunking for large files** - reduce memory usage")
        print()
    else:
        print("✅ No major performance improvements needed\n")

    print("### General Best Practices\n")
    print("1. **Profile before optimizing** - use cProfile or line_profiler to find bottlenecks")
    print("2. **Use vectorized operations** - NumPy/Pandas operations are much faster than Python loops")
    print("3. **Batch I/O operations** - minimize disk access")
    print("4. **Consider caching** - for expensive repeated calculations")
    print("5. **Monitor memory usage** - especially with large DataFrames")

    # Summary table
    print("\n## Summary Table\n")
    print("| Issue Type | Count | Severity | Est. Impact |")
    print("|------------|-------|----------|-------------|")

    all_types = {}
    for issue in all_issues:
        issue_type = issue['type']
        if issue_type not in all_types:
            all_types[issue_type] = {'count': 0, 'severity': issue['severity']}
        all_types[issue_type]['count'] += 1

    for issue_type, data in sorted(all_types.items(), key=lambda x: (x[1]['severity'], -x[1]['count'])):
        severity_icon = '🔴' if data['severity'] in ['CRITICAL', 'HIGH'] else '🟡' if data['severity'] == 'MEDIUM' else '🟢'
        impact = 'High' if data['severity'] in ['CRITICAL', 'HIGH'] else 'Medium' if data['severity'] == 'MEDIUM' else 'Low'
        print(f"| {issue_type.replace('_', ' ').title()} | {data['count']} | {severity_icon} {data['severity']} | {impact} |")


if __name__ == '__main__':
    main()
