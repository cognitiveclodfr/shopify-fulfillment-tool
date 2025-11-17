#!/usr/bin/env python3
"""Script to analyze code quality metrics."""

import ast
import os
import re
from pathlib import Path
from typing import Dict, List, Set, Tuple


def analyze_file_metrics(filepath: Path) -> Dict:
    """Analyze various code quality metrics for a file."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
            lines = content.split('\n')

        tree = ast.parse(content, filename=str(filepath))

        metrics = {
            'filepath': str(filepath),
            'total_lines': len(lines),
            'code_lines': sum(1 for line in lines if line.strip() and not line.strip().startswith('#')),
            'comment_lines': sum(1 for line in lines if line.strip().startswith('#')),
            'blank_lines': sum(1 for line in lines if not line.strip()),
            'long_lines': [],
            'functions': [],
            'classes': [],
            'imports': [],
            'type_hints': 0,
            'docstrings': 0,
            'magic_numbers': [],
            'deep_nesting': [],
            'global_vars': [],
        }

        # Find long lines (>120 characters)
        for i, line in enumerate(lines, 1):
            if len(line) > 120:
                metrics['long_lines'].append((i, len(line)))

        # Analyze AST
        analyzer = QualityAnalyzer(content)
        analyzer.visit(tree)

        metrics['functions'] = analyzer.functions
        metrics['classes'] = analyzer.classes
        metrics['imports'] = analyzer.imports
        metrics['type_hints'] = analyzer.type_hints
        metrics['docstrings'] = analyzer.docstrings
        metrics['magic_numbers'] = analyzer.magic_numbers
        metrics['deep_nesting'] = analyzer.deep_nesting
        metrics['global_vars'] = analyzer.global_vars

        return metrics

    except SyntaxError:
        return None
    except Exception as e:
        print(f"Error analyzing {filepath}: {e}")
        return None


class QualityAnalyzer(ast.NodeVisitor):
    """AST visitor to collect code quality metrics."""

    def __init__(self, content: str):
        self.content = content
        self.functions = []
        self.classes = []
        self.imports = []
        self.type_hints = 0
        self.docstrings = 0
        self.magic_numbers = []
        self.deep_nesting = []
        self.global_vars = []
        self.in_function = False
        self.nesting_level = 0

    def visit_FunctionDef(self, node):
        """Visit function definitions."""
        func_info = {
            'name': node.name,
            'line': node.lineno,
            'has_docstring': ast.get_docstring(node) is not None,
            'has_type_hints': False,
            'params': len(node.args.args),
        }

        # Check for return type hint
        if node.returns is not None:
            func_info['has_type_hints'] = True
            self.type_hints += 1

        # Check for parameter type hints
        for arg in node.args.args:
            if arg.annotation is not None:
                func_info['has_type_hints'] = True
                self.type_hints += 1

        if func_info['has_docstring']:
            self.docstrings += 1

        self.functions.append(func_info)

        old_in_function = self.in_function
        self.in_function = True
        self.generic_visit(node)
        self.in_function = old_in_function

    def visit_ClassDef(self, node):
        """Visit class definitions."""
        class_info = {
            'name': node.name,
            'line': node.lineno,
            'has_docstring': ast.get_docstring(node) is not None,
        }

        if class_info['has_docstring']:
            self.docstrings += 1

        self.classes.append(class_info)
        self.generic_visit(node)

    def visit_Import(self, node):
        """Visit import statements."""
        for alias in node.names:
            self.imports.append({
                'type': 'import',
                'name': alias.name,
                'line': node.lineno,
            })
        self.generic_visit(node)

    def visit_ImportFrom(self, node):
        """Visit from...import statements."""
        module = node.module or ''
        for alias in node.names:
            self.imports.append({
                'type': 'from',
                'module': module,
                'name': alias.name,
                'line': node.lineno,
            })
        self.generic_visit(node)

    def visit_Num(self, node):
        """Visit numeric constants (magic numbers)."""
        # Skip common values like 0, 1, -1
        if isinstance(node.n, (int, float)) and node.n not in [0, 1, -1, 2]:
            self.magic_numbers.append({
                'value': node.n,
                'line': node.lineno,
            })
        self.generic_visit(node)

    def visit_Constant(self, node):
        """Visit constant values (Python 3.8+)."""
        # Check for magic numbers
        if isinstance(node.value, (int, float)) and node.value not in [0, 1, -1, 2]:
            self.magic_numbers.append({
                'value': node.value,
                'line': node.lineno,
            })
        self.generic_visit(node)

    def visit_If(self, node):
        """Track nesting depth."""
        self.nesting_level += 1
        if self.nesting_level > 4 and self.in_function:
            self.deep_nesting.append(node.lineno)
        self.generic_visit(node)
        self.nesting_level -= 1

    def visit_For(self, node):
        """Track nesting depth."""
        self.nesting_level += 1
        if self.nesting_level > 4 and self.in_function:
            self.deep_nesting.append(node.lineno)
        self.generic_visit(node)
        self.nesting_level -= 1

    def visit_While(self, node):
        """Track nesting depth."""
        self.nesting_level += 1
        if self.nesting_level > 4 and self.in_function:
            self.deep_nesting.append(node.lineno)
        self.generic_visit(node)
        self.nesting_level -= 1

    def visit_Assign(self, node):
        """Find global variable assignments."""
        if not self.in_function:
            for target in node.targets:
                if isinstance(target, ast.Name):
                    # Skip imports and class definitions
                    if not target.id.isupper() and not target.id.startswith('_'):
                        self.global_vars.append({
                            'name': target.id,
                            'line': node.lineno,
                        })
        self.generic_visit(node)


def analyze_codebase():
    """Analyze entire codebase for quality metrics."""
    directories = ['shopify_tool', 'gui', 'shared']
    all_metrics = []

    for directory in directories:
        if not os.path.exists(directory):
            continue

        for py_file in Path(directory).rglob('*.py'):
            if '__pycache__' in str(py_file) or '__init__.py' in str(py_file):
                continue

            metrics = analyze_file_metrics(py_file)
            if metrics:
                all_metrics.append(metrics)

    return all_metrics


def print_quality_report(metrics: List[Dict]):
    """Print comprehensive quality report."""
    print("# Code Quality Analysis\n")

    # Aggregate statistics
    total_files = len(metrics)
    total_lines = sum(m['total_lines'] for m in metrics)
    total_code_lines = sum(m['code_lines'] for m in metrics)
    total_comment_lines = sum(m['comment_lines'] for m in metrics)
    total_functions = sum(len(m['functions']) for m in metrics)
    total_classes = sum(len(m['classes']) for m in metrics)

    functions_with_docstrings = sum(
        sum(1 for f in m['functions'] if f['has_docstring'])
        for m in metrics
    )
    functions_with_type_hints = sum(
        sum(1 for f in m['functions'] if f['has_type_hints'])
        for m in metrics
    )

    print("## Overall Statistics\n")
    print(f"- **Total Files Analyzed:** {total_files}")
    print(f"- **Total Lines:** {total_lines:,}")
    print(f"- **Code Lines:** {total_code_lines:,} ({100*total_code_lines//total_lines}%)")
    print(f"- **Comment Lines:** {total_comment_lines:,} ({100*total_comment_lines//total_lines}%)")
    print(f"- **Total Functions:** {total_functions}")
    print(f"- **Total Classes:** {total_classes}")
    print()

    # Type Hints Coverage
    print("## 1. Type Hints Coverage\n")
    if total_functions > 0:
        type_hint_pct = (100 * functions_with_type_hints) // total_functions
        print(f"**Functions with type hints:** {functions_with_type_hints}/{total_functions} ({type_hint_pct}%)\n")

        if type_hint_pct < 30:
            print("**Status:** 🔴 CRITICAL - Very low type hint coverage")
            print("**Recommendation:** Add type hints to improve code maintainability")
            print("**Priority:** HIGH\n")
        elif type_hint_pct < 60:
            print("**Status:** 🟡 MEDIUM - Moderate type hint coverage")
            print("**Recommendation:** Continue adding type hints to new and modified functions")
            print("**Priority:** MEDIUM\n")
        else:
            print("**Status:** ✅ GOOD - Strong type hint coverage")
            print("**Priority:** LOW\n")

        # Files with worst type hint coverage
        print("### Files with No/Low Type Hints\n")
        files_no_hints = []
        for m in metrics:
            if m['functions']:
                funcs_with_hints = sum(1 for f in m['functions'] if f['has_type_hints'])
                coverage = funcs_with_hints / len(m['functions']) if m['functions'] else 0
                if coverage < 0.3:
                    files_no_hints.append((m['filepath'], len(m['functions']), funcs_with_hints, coverage))

        files_no_hints.sort(key=lambda x: x[1], reverse=True)  # Sort by function count
        for filepath, total_funcs, with_hints, coverage in files_no_hints[:10]:
            print(f"- `{filepath}`: {with_hints}/{total_funcs} functions ({int(coverage*100)}%)")
        print()

    # Docstrings Coverage
    print("## 2. Docstrings Coverage\n")
    if total_functions > 0:
        docstring_pct = (100 * functions_with_docstrings) // total_functions
        print(f"**Functions with docstrings:** {functions_with_docstrings}/{total_functions} ({docstring_pct}%)\n")

        if docstring_pct < 50:
            print("**Status:** 🔴 CRITICAL - Low documentation coverage")
            print("**Recommendation:** Add docstrings to public functions and methods")
            print("**Priority:** HIGH\n")
        elif docstring_pct < 70:
            print("**Status:** 🟡 MEDIUM - Moderate documentation")
            print("**Recommendation:** Continue improving documentation")
            print("**Priority:** MEDIUM\n")
        else:
            print("**Status:** ✅ GOOD - Well documented code")
            print("**Priority:** LOW\n")

    # Long Lines
    print("## 3. Long Lines (>120 characters)\n")
    total_long_lines = sum(len(m['long_lines']) for m in metrics)
    print(f"**Total long lines:** {total_long_lines}\n")

    if total_long_lines > 0:
        files_with_long_lines = [(m['filepath'], len(m['long_lines']))
                                 for m in metrics if m['long_lines']]
        files_with_long_lines.sort(key=lambda x: x[1], reverse=True)

        print("### Files with Most Long Lines\n")
        for filepath, count in files_with_long_lines[:10]:
            print(f"- `{filepath}`: {count} long lines")
        print()

        if total_long_lines > 100:
            print("**Status:** 🟡 MEDIUM - Many long lines detected")
            print("**Recommendation:** Consider breaking long lines for better readability")
            print("**Priority:** LOW\n")

    # Deep Nesting
    print("## 4. Deep Nesting (>4 levels)\n")
    total_deep_nesting = sum(len(m['deep_nesting']) for m in metrics)
    print(f"**Total deep nesting occurrences:** {total_deep_nesting}\n")

    if total_deep_nesting > 0:
        files_with_nesting = [(m['filepath'], len(m['deep_nesting']))
                              for m in metrics if m['deep_nesting']]
        files_with_nesting.sort(key=lambda x: x[1], reverse=True)

        print("### Files with Deep Nesting\n")
        for filepath, count in files_with_nesting[:10]:
            print(f"- `{filepath}`: {count} occurrences")
        print()

        if total_deep_nesting > 20:
            print("**Status:** 🔴 HIGH - Excessive deep nesting")
            print("**Recommendation:** Refactor deeply nested code to reduce complexity")
            print("**Priority:** HIGH\n")
        else:
            print("**Status:** 🟡 MEDIUM - Some deep nesting detected")
            print("**Recommendation:** Consider flattening logic where possible")
            print("**Priority:** MEDIUM\n")

    # Magic Numbers
    print("## 5. Magic Numbers\n")
    total_magic_numbers = sum(len(m['magic_numbers']) for m in metrics)
    print(f"**Total magic numbers:** {total_magic_numbers}\n")

    if total_magic_numbers > 0:
        files_with_magic = [(m['filepath'], len(m['magic_numbers']))
                            for m in metrics if m['magic_numbers']]
        files_with_magic.sort(key=lambda x: x[1], reverse=True)

        print("### Files with Most Magic Numbers\n")
        for filepath, count in files_with_magic[:10]:
            print(f"- `{filepath}`: {count} magic numbers")
        print()

        if total_magic_numbers > 100:
            print("**Status:** 🟡 MEDIUM - Many hardcoded numbers")
            print("**Recommendation:** Extract magic numbers to named constants")
            print("**Priority:** MEDIUM\n")
        else:
            print("**Status:** 🟢 LOW - Acceptable number of magic numbers")
            print("**Priority:** LOW\n")

    # Global Variables
    print("## 6. Global Variables\n")
    total_globals = sum(len(m['global_vars']) for m in metrics)
    print(f"**Total global variables:** {total_globals}\n")

    if total_globals > 0:
        print("### Global Variables Found\n")
        all_globals = []
        for m in metrics:
            for gvar in m['global_vars']:
                all_globals.append((m['filepath'], gvar['name'], gvar['line']))

        all_globals.sort()
        for filepath, name, line in all_globals[:20]:
            print(f"- `{filepath}:{line}` - `{name}`")
        if len(all_globals) > 20:
            print(f"- ... and {len(all_globals) - 20} more")
        print()

        if total_globals > 10:
            print("**Status:** 🟡 MEDIUM - Multiple global variables found")
            print("**Recommendation:** Consider using classes or module-level configuration")
            print("**Priority:** MEDIUM\n")
        else:
            print("**Status:** 🟢 LOW - Few global variables")
            print("**Priority:** LOW\n")

    # Summary
    print("\n## Summary\n")
    print("| Metric | Value | Status | Priority |")
    print("|--------|-------|--------|----------|")
    print(f"| Type Hints Coverage | {functions_with_type_hints}/{total_functions} ({(100*functions_with_type_hints//total_functions) if total_functions else 0}%) | {'🔴' if (100*functions_with_type_hints//total_functions) < 30 else '🟡' if (100*functions_with_type_hints//total_functions) < 60 else '✅'} | {'HIGH' if (100*functions_with_type_hints//total_functions) < 30 else 'MEDIUM' if (100*functions_with_type_hints//total_functions) < 60 else 'LOW'} |")
    print(f"| Docstrings Coverage | {functions_with_docstrings}/{total_functions} ({(100*functions_with_docstrings//total_functions) if total_functions else 0}%) | {'🔴' if (100*functions_with_docstrings//total_functions) < 50 else '🟡' if (100*functions_with_docstrings//total_functions) < 70 else '✅'} | {'HIGH' if (100*functions_with_docstrings//total_functions) < 50 else 'MEDIUM' if (100*functions_with_docstrings//total_functions) < 70 else 'LOW'} |")
    print(f"| Long Lines (>120) | {total_long_lines} | {'🟡' if total_long_lines > 100 else '🟢'} | {'MEDIUM' if total_long_lines > 100 else 'LOW'} |")
    print(f"| Deep Nesting (>4) | {total_deep_nesting} | {'🔴' if total_deep_nesting > 20 else '🟡' if total_deep_nesting > 0 else '✅'} | {'HIGH' if total_deep_nesting > 20 else 'MEDIUM' if total_deep_nesting > 0 else 'LOW'} |")
    print(f"| Magic Numbers | {total_magic_numbers} | {'🟡' if total_magic_numbers > 100 else '🟢'} | {'MEDIUM' if total_magic_numbers > 100 else 'LOW'} |")
    print(f"| Global Variables | {total_globals} | {'🟡' if total_globals > 10 else '🟢'} | {'MEDIUM' if total_globals > 10 else 'LOW'} |")


if __name__ == '__main__':
    metrics = analyze_codebase()
    print_quality_report(metrics)
