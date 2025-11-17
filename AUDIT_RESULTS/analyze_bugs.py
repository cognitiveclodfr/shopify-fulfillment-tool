#!/usr/bin/env python3
"""Script to find potential bugs and code smells."""

import ast
import os
from pathlib import Path
from typing import List, Dict


class BugDetector(ast.NodeVisitor):
    """AST visitor to detect potential bugs and code smells."""

    def __init__(self, filepath: str, content: str):
        self.filepath = filepath
        self.content = content
        self.issues = []

    def visit_FunctionDef(self, node):
        """Check function definitions for issues."""
        # Check for mutable default arguments
        for arg in node.args.defaults:
            if isinstance(arg, (ast.List, ast.Dict, ast.Set)):
                self.issues.append({
                    'type': 'mutable_default',
                    'severity': 'HIGH',
                    'line': node.lineno,
                    'function': node.name,
                    'message': f'Mutable default argument in function {node.name}()'
                })

        # Check for too many parameters
        num_params = len(node.args.args)
        if num_params > 7:
            self.issues.append({
                'type': 'too_many_params',
                'severity': 'MEDIUM',
                'line': node.lineno,
                'function': node.name,
                'message': f'Function {node.name}() has {num_params} parameters (>7)'
            })

        self.generic_visit(node)

    def visit_ExceptHandler(self, node):
        """Check exception handling."""
        # Check for bare except
        if node.type is None:
            self.issues.append({
                'type': 'bare_except',
                'severity': 'CRITICAL',
                'line': node.lineno,
                'message': 'Bare except: clause (catches all exceptions including KeyboardInterrupt)'
            })
        # Check for broad Exception catching
        elif isinstance(node.type, ast.Name) and node.type.id == 'Exception':
            self.issues.append({
                'type': 'broad_except',
                'severity': 'HIGH',
                'line': node.lineno,
                'message': 'Catching broad Exception type - consider specific exceptions'
            })

        self.generic_visit(node)

    def visit_Try(self, node):
        """Check try-except structure."""
        # Count nesting depth of try-except
        nested_tries = sum(1 for child in ast.walk(node) if isinstance(child, ast.Try) and child != node)
        if nested_tries >= 2:
            self.issues.append({
                'type': 'nested_try',
                'severity': 'MEDIUM',
                'line': node.lineno,
                'message': f'Deeply nested try-except blocks (depth: {nested_tries + 1})'
            })

        self.generic_visit(node)

    def visit_Compare(self, node):
        """Check comparison operations."""
        # Check for comparison with True/False
        for comp in node.comparators:
            if isinstance(comp, ast.Constant):
                if comp.value is True:
                    self.issues.append({
                        'type': 'compare_true',
                        'severity': 'LOW',
                        'line': node.lineno,
                        'message': 'Comparison with True - use implicit boolean check'
                    })
                elif comp.value is False:
                    self.issues.append({
                        'type': 'compare_false',
                        'severity': 'LOW',
                        'line': node.lineno,
                        'message': 'Comparison with False - use implicit boolean check or not'
                    })

        self.generic_visit(node)

    def visit_Call(self, node):
        """Check function calls for potential issues."""
        # Check for eval/exec usage
        if isinstance(node.func, ast.Name):
            if node.func.id in ['eval', 'exec']:
                self.issues.append({
                    'type': 'dangerous_call',
                    'severity': 'CRITICAL',
                    'line': node.lineno,
                    'message': f'Dangerous function call: {node.func.id}() - potential security risk'
                })

        self.generic_visit(node)


def analyze_file_for_bugs(filepath: Path) -> List[Dict]:
    """Analyze a single file for potential bugs."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()

        tree = ast.parse(content, filename=str(filepath))
        detector = BugDetector(str(filepath), content)
        detector.visit(tree)

        return detector.issues

    except SyntaxError:
        return []
    except Exception as e:
        print(f"Error analyzing {filepath}: {e}")
        return []


def find_circular_imports() -> List[str]:
    """Attempt to detect potential circular imports."""
    import_map = {}
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

                tree = ast.parse(content)
                imports = []

                for node in ast.walk(tree):
                    if isinstance(node, ast.ImportFrom):
                        if node.module and not node.module.startswith('.'):
                            imports.append(node.module)

                import_map[str(py_file)] = imports

            except:
                pass

    # Simple circular import detection (A -> B -> A)
    potential_circles = []
    for file_a, imports_a in import_map.items():
        for imported_module in imports_a:
            # Find file that matches this module
            for file_b, imports_b in import_map.items():
                if file_a != file_b and imported_module in str(file_b):
                    # Check if file_b imports back to file_a's module
                    file_a_module = file_a.replace('/', '.').replace('.py', '')
                    if any(file_a_module in imp for imp in imports_b):
                        potential_circles.append((file_a, file_b))

    return potential_circles


def main():
    """Main analysis function."""
    print("# Potential Bugs and Code Smells\n")

    # Collect all issues
    all_issues = []
    directories = ['shopify_tool', 'gui', 'shared']

    for directory in directories:
        if not os.path.exists(directory):
            continue

        for py_file in Path(directory).rglob('*.py'):
            if '__pycache__' in str(py_file):
                continue

            issues = analyze_file_for_bugs(py_file)
            all_issues.extend(issues)

    # Group by severity
    critical_issues = [i for i in all_issues if i['severity'] == 'CRITICAL']
    high_issues = [i for i in all_issues if i['severity'] == 'HIGH']
    medium_issues = [i for i in all_issues if i['severity'] == 'MEDIUM']
    low_issues = [i for i in all_issues if i['severity'] == 'LOW']

    print(f"## Summary\n")
    print(f"**Total Issues Found:** {len(all_issues)}\n")
    print(f"- 🔴 **CRITICAL:** {len(critical_issues)}")
    print(f"- 🔴 **HIGH:** {len(high_issues)}")
    print(f"- 🟡 **MEDIUM:** {len(medium_issues)}")
    print(f"- 🟢 **LOW:** {len(low_issues)}")
    print()

    # Critical Issues
    if critical_issues:
        print("## 🔴 CRITICAL Issues\n")
        print("These issues require immediate attention.\n")

        # Group by type
        by_type = {}
        for issue in critical_issues:
            issue_type = issue['type']
            if issue_type not in by_type:
                by_type[issue_type] = []
            by_type[issue_type].append(issue)

        for issue_type, issues in by_type.items():
            print(f"### {issue_type.replace('_', ' ').title()} ({len(issues)} occurrences)\n")
            for issue in issues[:20]:  # Limit to 20 per type
                print(f"- `{issue.get('filepath', 'unknown')}:{issue['line']}` - {issue['message']}")
            if len(issues) > 20:
                print(f"- ... and {len(issues) - 20} more")
            print()

    # High Priority Issues
    if high_issues:
        print("## 🔴 HIGH Priority Issues\n")

        by_type = {}
        for issue in high_issues:
            issue_type = issue['type']
            if issue_type not in by_type:
                by_type[issue_type] = []
            by_type[issue_type].append(issue)

        for issue_type, issues in by_type.items():
            print(f"### {issue_type.replace('_', ' ').title()} ({len(issues)} occurrences)\n")
            for issue in issues[:15]:
                print(f"- `{issue.get('filepath', 'unknown')}:{issue['line']}` - {issue['message']}")
            if len(issues) > 15:
                print(f"- ... and {len(issues) - 15} more")
            print()

    # Medium Priority Issues
    if medium_issues:
        print("## 🟡 MEDIUM Priority Issues\n")

        by_type = {}
        for issue in medium_issues:
            issue_type = issue['type']
            if issue_type not in by_type:
                by_type[issue_type] = []
            by_type[issue_type].append(issue)

        for issue_type, issues in by_type.items():
            print(f"### {issue_type.replace('_', ' ').title()} ({len(issues)} occurrences)\n")
            print(f"**Count:** {len(issues)}\n")
            # Just show a few examples
            for issue in issues[:10]:
                print(f"- `{issue.get('filepath', 'unknown')}:{issue['line']}` - {issue['message']}")
            if len(issues) > 10:
                print(f"- ... and {len(issues) - 10} more")
            print()

    # Circular Imports
    print("## Circular Import Detection\n")
    circles = find_circular_imports()
    if circles:
        print(f"**Potential circular imports found:** {len(circles)}\n")
        for file_a, file_b in circles[:10]:
            print(f"- `{file_a}` ↔ `{file_b}`")
        if len(circles) > 10:
            print(f"- ... and {len(circles) - 10} more")
        print("\n**Recommendation:** 🔴 Review and refactor to eliminate circular dependencies")
        print("**Priority:** HIGH\n")
    else:
        print("✅ No obvious circular imports detected\n")

    # Recommendations
    print("\n## Recommendations by Priority\n")
    print("### 🔴 Critical (Immediate Action Required)\n")
    if critical_issues:
        print("1. **Fix all bare except: clauses** - They catch system exits and keyboard interrupts")
        print("2. **Remove eval/exec calls** - Major security vulnerability")
        print("3. **Review exception handling** - Use specific exception types")
    else:
        print("✅ No critical issues found\n")

    print("\n### 🔴 High Priority\n")
    if high_issues:
        print("1. **Fix mutable default arguments** - Can cause subtle bugs")
        print("2. **Narrow exception catching** - Replace broad Exception with specific types")
        print("3. **Review circular imports** - Can cause import-time errors")
    else:
        print("✅ No high priority issues found\n")

    print("\n### 🟡 Medium Priority\n")
    if medium_issues:
        print("1. **Refactor functions with too many parameters** - Use config objects or dataclasses")
        print("2. **Simplify nested try-except blocks** - Improve code readability")
        print("3. **Review deep nesting** - Consider flattening control flow")
    else:
        print("✅ No medium priority issues found\n")


if __name__ == '__main__':
    main()
