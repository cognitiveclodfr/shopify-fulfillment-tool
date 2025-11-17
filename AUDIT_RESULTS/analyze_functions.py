#!/usr/bin/env python3
"""Script to analyze Python functions and methods in the codebase."""

import ast
import os
from pathlib import Path
from typing import List, Dict, Tuple
import sys


class FunctionAnalyzer(ast.NodeVisitor):
    """Analyzes Python AST to find function metrics."""

    def __init__(self, filepath: str, content: str):
        self.filepath = filepath
        self.content = content
        self.lines = content.split('\n')
        self.functions = []
        self.current_class = None

    def visit_ClassDef(self, node):
        """Track current class for method context."""
        old_class = self.current_class
        self.current_class = node.name
        self.generic_visit(node)
        self.current_class = old_class

    def visit_FunctionDef(self, node):
        """Extract function/method information."""
        self._process_function(node)
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node):
        """Extract async function/method information."""
        self._process_function(node, is_async=True)
        self.generic_visit(node)

    def _process_function(self, node, is_async=False):
        """Process a function or method node."""
        start_line = node.lineno
        end_line = node.end_lineno or start_line
        num_lines = end_line - start_line + 1

        # Get function name with class prefix if it's a method
        if self.current_class:
            full_name = f"{self.current_class}.{node.name}"
        else:
            full_name = node.name

        # Count parameters
        num_params = len(node.args.args)

        # Estimate complexity by counting control flow statements
        complexity = self._estimate_complexity(node)

        # Count nesting depth
        max_depth = self._max_nesting_depth(node)

        self.functions.append({
            'name': full_name,
            'lines': num_lines,
            'start_line': start_line,
            'end_line': end_line,
            'params': num_params,
            'complexity': complexity,
            'max_depth': max_depth,
            'is_async': is_async,
            'has_docstring': ast.get_docstring(node) is not None
        })

    def _estimate_complexity(self, node) -> int:
        """Estimate cyclomatic complexity."""
        complexity = 1
        for child in ast.walk(node):
            if isinstance(child, (ast.If, ast.While, ast.For, ast.ExceptHandler,
                                ast.With, ast.Assert, ast.comprehension)):
                complexity += 1
            elif isinstance(child, ast.BoolOp):
                complexity += len(child.values) - 1
        return complexity

    def _max_nesting_depth(self, node, current_depth=0) -> int:
        """Calculate maximum nesting depth."""
        max_depth = current_depth
        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.If, ast.While, ast.For, ast.With, ast.Try)):
                child_depth = self._max_nesting_depth(child, current_depth + 1)
                max_depth = max(max_depth, child_depth)
            else:
                child_depth = self._max_nesting_depth(child, current_depth)
                max_depth = max(max_depth, child_depth)
        return max_depth


def analyze_file(filepath: Path) -> List[Dict]:
    """Analyze a single Python file."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()

        tree = ast.parse(content, filename=str(filepath))
        analyzer = FunctionAnalyzer(str(filepath), content)
        analyzer.visit(tree)
        return analyzer.functions
    except SyntaxError as e:
        print(f"Syntax error in {filepath}: {e}", file=sys.stderr)
        return []
    except Exception as e:
        print(f"Error analyzing {filepath}: {e}", file=sys.stderr)
        return []


def analyze_directory(directory: str, exclude_dirs=None) -> Dict[str, List[Dict]]:
    """Analyze all Python files in a directory."""
    if exclude_dirs is None:
        exclude_dirs = {'.git', '__pycache__', '.venv', 'venv', '.pytest_cache'}

    results = {}
    base_path = Path(directory).resolve()

    for py_file in base_path.rglob('*.py'):
        # Skip excluded directories
        if any(excluded in py_file.parts for excluded in exclude_dirs):
            continue

        functions = analyze_file(py_file)
        if functions:
            # Make path relative to current working directory
            try:
                rel_path = py_file.relative_to(Path.cwd().resolve())
            except ValueError:
                # If can't make relative, just use the file path as is
                rel_path = py_file
            results[str(rel_path)] = functions

    return results


def print_long_functions(results: Dict[str, List[Dict]], min_lines=100):
    """Print functions longer than min_lines."""
    long_functions = []

    for filepath, functions in results.items():
        for func in functions:
            if func['lines'] >= min_lines:
                long_functions.append((filepath, func))

    # Sort by number of lines (descending)
    long_functions.sort(key=lambda x: x[1]['lines'], reverse=True)

    print(f"# Long Functions (>={min_lines} lines)\n")
    print(f"Found {len(long_functions)} functions/methods with {min_lines}+ lines\n")

    for filepath, func in long_functions:
        complexity_level = "LOW" if func['complexity'] < 10 else "MEDIUM" if func['complexity'] < 20 else "HIGH"

        print(f"### {filepath}::{func['name']}")
        print(f"- **Lines:** {func['lines']} (lines {func['start_line']}-{func['end_line']})")
        print(f"- **Complexity:** {complexity_level} (cyclomatic: {func['complexity']})")
        print(f"- **Max Nesting Depth:** {func['max_depth']}")
        print(f"- **Parameters:** {func['params']}")
        print(f"- **Has Docstring:** {'Yes' if func['has_docstring'] else 'No'}")

        # Suggestions
        if func['lines'] > 200:
            print(f"- **Can be split:** YES - Critical refactoring needed")
        elif func['lines'] > 100:
            print(f"- **Can be split:** RECOMMENDED - Should be refactored")

        if func['complexity'] > 20:
            print(f"- **Suggestion:** High complexity - consider breaking into smaller functions")
        if func['max_depth'] > 4:
            print(f"- **Suggestion:** Deep nesting detected - consider flattening logic")
        if func['params'] > 5:
            print(f"- **Suggestion:** Too many parameters - consider using a config object")

        print()

    return long_functions


def print_quality_metrics(results: Dict[str, List[Dict]]):
    """Print overall code quality metrics."""
    total_functions = 0
    with_docstrings = 0
    total_lines = 0
    high_complexity = 0
    deep_nesting = 0
    many_params = 0

    for filepath, functions in results.items():
        for func in functions:
            total_functions += 1
            if func['has_docstring']:
                with_docstrings += 1
            total_lines += func['lines']
            if func['complexity'] > 15:
                high_complexity += 1
            if func['max_depth'] > 4:
                deep_nesting += 1
            if func['params'] > 5:
                many_params += 1

    print("# Code Quality Metrics\n")
    print(f"Total functions analyzed: {total_functions}")
    print(f"Functions with docstrings: {with_docstrings} ({100*with_docstrings//total_functions if total_functions else 0}%)")
    print(f"Average function length: {total_lines//total_functions if total_functions else 0} lines")
    print(f"Functions with high complexity (>15): {high_complexity}")
    print(f"Functions with deep nesting (>4): {deep_nesting}")
    print(f"Functions with many parameters (>5): {many_params}")
    print()


if __name__ == '__main__':
    # Analyze main source directories
    directories = ['shopify_tool', 'gui', 'shared', 'tests']
    all_results = {}

    for directory in directories:
        if os.path.exists(directory):
            results = analyze_directory(directory)
            all_results.update(results)

    # Print results
    print_long_functions(all_results, min_lines=100)
    print("\n" + "="*80 + "\n")
    print_quality_metrics(all_results)
