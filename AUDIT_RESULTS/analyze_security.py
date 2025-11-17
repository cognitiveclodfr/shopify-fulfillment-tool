#!/usr/bin/env python3
"""Script to perform basic security analysis."""

import ast
import os
import re
from pathlib import Path
from typing import List, Dict


class SecurityScanner(ast.NodeVisitor):
    """AST visitor to detect potential security issues."""

    def __init__(self, filepath: str, content: str):
        self.filepath = filepath
        self.content = content
        self.lines = content.split('\n')
        self.issues = []

    def visit_Call(self, node):
        """Check function calls for security issues."""
        # Check for eval/exec
        if isinstance(node.func, ast.Name):
            if node.func.id in ['eval', 'exec']:
                self.issues.append({
                    'type': 'dangerous_function',
                    'severity': 'CRITICAL',
                    'line': node.lineno,
                    'function': node.func.id,
                    'message': f'Dangerous function: {node.func.id}() - arbitrary code execution risk'
                })

            # Check for compile()
            elif node.func.id == 'compile':
                self.issues.append({
                    'type': 'dangerous_function',
                    'severity': 'HIGH',
                    'line': node.lineno,
                    'function': 'compile',
                    'message': 'compile() function - potential code injection risk'
                })

        # Check for pickle usage
        if isinstance(node.func, ast.Attribute):
            if node.func.attr in ['load', 'loads', 'dump', 'dumps']:
                if isinstance(node.func.value, ast.Name):
                    if node.func.value.id == 'pickle':
                        self.issues.append({
                            'type': 'pickle_usage',
                            'severity': 'HIGH',
                            'line': node.lineno,
                            'message': 'pickle usage - can execute arbitrary code during deserialization'
                        })

            # Check for subprocess with shell=True
            elif node.func.attr in ['call', 'run', 'Popen']:
                for keyword in node.keywords:
                    if keyword.arg == 'shell':
                        if isinstance(keyword.value, ast.Constant) and keyword.value.value is True:
                            self.issues.append({
                                'type': 'shell_injection',
                                'severity': 'CRITICAL',
                                'line': node.lineno,
                                'message': 'subprocess with shell=True - command injection risk'
                            })

        self.generic_visit(node)

    def visit_Import(self, node):
        """Check imports for security-sensitive modules."""
        for alias in node.names:
            if alias.name == 'pickle':
                self.issues.append({
                    'type': 'risky_import',
                    'severity': 'MEDIUM',
                    'line': node.lineno,
                    'message': 'pickle imported - ensure only trusted data is unpickled'
                })

        self.generic_visit(node)

    def visit_ImportFrom(self, node):
        """Check from...import for security issues."""
        if node.module == 'pickle':
            self.issues.append({
                'type': 'risky_import',
                'severity': 'MEDIUM',
                'line': node.lineno,
                'message': 'pickle functions imported - ensure only trusted data is unpickled'
            })

        self.generic_visit(node)


def find_hardcoded_secrets(filepath: Path) -> List[Dict]:
    """Find potential hardcoded secrets."""
    issues = []

    # Patterns that might indicate hardcoded secrets
    patterns = [
        (r'password\s*=\s*["\'](?!.*\{.*\})([^"\']{8,})["\']', 'hardcoded_password', 'CRITICAL'),
        (r'api[_-]?key\s*=\s*["\'](?!.*\{.*\})([^"\']{16,})["\']', 'hardcoded_api_key', 'CRITICAL'),
        (r'secret\s*=\s*["\'](?!.*\{.*\})([^"\']{16,})["\']', 'hardcoded_secret', 'CRITICAL'),
        (r'token\s*=\s*["\'](?!.*\{.*\})([^"\']{16,})["\']', 'hardcoded_token', 'CRITICAL'),
        (r'aws_access_key', 'aws_credential', 'CRITICAL'),
        (r'private_key\s*=\s*["\']', 'private_key', 'CRITICAL'),
    ]

    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        for i, line in enumerate(lines, 1):
            # Skip comments (but still check for accidentally committed secrets)
            stripped = line.strip()

            for pattern, issue_type, severity in patterns:
                if re.search(pattern, line, re.IGNORECASE):
                    # Exclude obvious false positives
                    if 'example' in line.lower() or 'test' in line.lower() or 'dummy' in line.lower():
                        continue

                    issues.append({
                        'type': issue_type,
                        'severity': severity,
                        'line': i,
                        'message': f'Potential hardcoded secret: {issue_type.replace("_", " ")}',
                        'preview': line.strip()[:80]
                    })

    except Exception as e:
        print(f"Error scanning {filepath}: {e}")

    return issues


def find_path_traversal_risks(filepath: Path) -> List[Dict]:
    """Find potential path traversal vulnerabilities."""
    issues = []

    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
            lines = content.split('\n')

        tree = ast.parse(content)

        for node in ast.walk(tree):
            # Look for path operations with user input
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Attribute):
                    # Path.open(), os.path.join() etc with potential user input
                    if node.func.attr in ['open', 'join', 'read', 'write']:
                        # Check if any arguments look like they might be user-controlled
                        for arg in node.args:
                            if isinstance(arg, ast.Name):
                                # Variable names that might indicate user input
                                if any(keyword in arg.id.lower() for keyword in ['input', 'user', 'file', 'path', 'name']):
                                    issues.append({
                                        'type': 'path_traversal_risk',
                                        'severity': 'MEDIUM',
                                        'line': node.lineno,
                                        'message': f'Potential path traversal - validate/sanitize path input: {arg.id}'
                                    })

                elif isinstance(node.func, ast.Name):
                    if node.func.id == 'open':
                        # Check for open() with variable paths
                        if node.args and isinstance(node.args[0], ast.Name):
                            var_name = node.args[0].id
                            if any(keyword in var_name.lower() for keyword in ['input', 'user', 'file', 'path']):
                                issues.append({
                                    'type': 'path_traversal_risk',
                                    'severity': 'MEDIUM',
                                    'line': node.lineno,
                                    'message': f'open() with user-controlled path - validate input: {var_name}'
                                })

    except Exception as e:
        print(f"Error analyzing {filepath}: {e}")

    return issues


def analyze_file_security(filepath: Path) -> List[Dict]:
    """Analyze a file for security issues."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()

        tree = ast.parse(content, filename=str(filepath))
        scanner = SecurityScanner(str(filepath), content)
        scanner.visit(tree)

        # Add other security checks
        secret_issues = find_hardcoded_secrets(filepath)
        path_issues = find_path_traversal_risks(filepath)

        all_issues = scanner.issues + secret_issues + path_issues

        # Add filepath to all issues
        for issue in all_issues:
            issue['filepath'] = str(filepath)

        return all_issues

    except SyntaxError:
        return []
    except Exception as e:
        print(f"Error analyzing {filepath}: {e}")
        return []


def main():
    """Main security analysis function."""
    print("# Security Analysis Report\n")

    # Collect all issues
    all_issues = []
    directories = ['shopify_tool', 'gui', 'shared']

    for directory in directories:
        if not os.path.exists(directory):
            continue

        for py_file in Path(directory).rglob('*.py'):
            if '__pycache__' in str(py_file):
                continue

            issues = analyze_file_security(py_file)
            all_issues.extend(issues)

    # Group by severity
    critical_issues = [i for i in all_issues if i['severity'] == 'CRITICAL']
    high_issues = [i for i in all_issues if i['severity'] == 'HIGH']
    medium_issues = [i for i in all_issues if i['severity'] == 'MEDIUM']
    low_issues = [i for i in all_issues if i['severity'] == 'LOW']

    print("## Executive Summary\n")
    print(f"**Total Security Issues Found:** {len(all_issues)}\n")
    print(f"- 🔴 **CRITICAL:** {len(critical_issues)}")
    print(f"- 🔴 **HIGH:** {len(high_issues)}")
    print(f"- 🟡 **MEDIUM:** {len(medium_issues)}")
    print(f"- 🟢 **LOW:** {len(low_issues)}")
    print()

    if not all_issues:
        print("✅ **No major security issues detected!**\n")
        print("Note: This is a basic static analysis. Consider additional security measures:\n")
        print("1. Use tools like `bandit` for comprehensive Python security scanning")
        print("2. Perform dependency vulnerability scanning with `pip-audit` or `safety`")
        print("3. Conduct code reviews focused on security")
        print("4. Implement input validation throughout the application")
        print("5. Use secure coding practices for file I/O and data processing")
        return

    # Critical Issues
    if critical_issues:
        print("## 🔴 CRITICAL Security Issues\n")
        print("**IMMEDIATE ACTION REQUIRED**\n")

        by_type = {}
        for issue in critical_issues:
            issue_type = issue['type']
            if issue_type not in by_type:
                by_type[issue_type] = []
            by_type[issue_type].append(issue)

        for issue_type, issues in sorted(by_type.items()):
            print(f"### {issue_type.replace('_', ' ').title()} ({len(issues)} occurrences)\n")

            if issue_type == 'dangerous_function':
                print("**Risk:** Arbitrary code execution vulnerability\n")
                print("**Impact:** Attacker could execute malicious code\n")
                print("**Mitigation:** Remove eval()/exec() or use safe alternatives like ast.literal_eval()\n")

            elif issue_type == 'shell_injection':
                print("**Risk:** Command injection vulnerability\n")
                print("**Impact:** Attacker could execute system commands\n")
                print("**Mitigation:** Use shell=False and pass commands as lists, not strings\n")

            elif issue_type == 'hardcoded_password':
                print("**Risk:** Exposed credentials\n")
                print("**Impact:** Unauthorized access to systems/data\n")
                print("**Mitigation:** Use environment variables or secure credential management\n")

            elif issue_type == 'hardcoded_api_key':
                print("**Risk:** Exposed API credentials\n")
                print("**Impact:** Unauthorized API access, potential data breach\n")
                print("**Mitigation:** Use environment variables or secure vault\n")

            elif issue_type == 'hardcoded_secret':
                print("**Risk:** Exposed secret keys\n")
                print("**Impact:** Compromised security mechanisms\n")
                print("**Mitigation:** Use secure configuration management\n")

            print("**Locations:**")
            for issue in issues:
                print(f"- `{issue['filepath']}:{issue['line']}` - {issue['message']}")
                if 'preview' in issue:
                    print(f"  ```python")
                    print(f"  {issue['preview']}")
                    print(f"  ```")
            print()

    # High Priority Issues
    if high_issues:
        print("## 🔴 HIGH Priority Security Issues\n")

        by_type = {}
        for issue in high_issues:
            issue_type = issue['type']
            if issue_type not in by_type:
                by_type[issue_type] = []
            by_type[issue_type].append(issue)

        for issue_type, issues in sorted(by_type.items()):
            print(f"### {issue_type.replace('_', ' ').title()} ({len(issues)} occurrences)\n")

            if issue_type == 'pickle_usage':
                print("**Risk:** Arbitrary code execution during deserialization\n")
                print("**Impact:** Malicious pickle files can execute code when loaded\n")
                print("**Mitigation:** Use JSON or other safe serialization formats\n")
                print("**If pickle is necessary:** Only unpickle data from trusted sources\n")

            print("**Locations:**")
            for issue in issues[:15]:
                print(f"- `{issue['filepath']}:{issue['line']}` - {issue['message']}")
            if len(issues) > 15:
                print(f"- ... and {len(issues) - 15} more")
            print()

    # Medium Priority Issues
    if medium_issues:
        print("## 🟡 MEDIUM Priority Security Issues\n")

        by_type = {}
        for issue in medium_issues:
            issue_type = issue['type']
            if issue_type not in by_type:
                by_type[issue_type] = []
            by_type[issue_type].append(issue)

        for issue_type, issues in sorted(by_type.items()):
            print(f"### {issue_type.replace('_', ' ').title()} ({len(issues)} occurrences)\n")

            if issue_type == 'path_traversal_risk':
                print("**Risk:** Potential directory traversal vulnerability\n")
                print("**Mitigation:** Validate file paths, use Path.resolve() and check parent directory\n")
                print("**Example:**")
                print("```python")
                print("from pathlib import Path")
                print("safe_base = Path('/safe/directory').resolve()")
                print("user_path = Path(user_input).resolve()")
                print("if not user_path.is_relative_to(safe_base):")
                print("    raise ValueError('Invalid path')")
                print("```\n")

            elif issue_type == 'risky_import':
                print("**Risk:** Using potentially dangerous module\n")
                print("**Mitigation:** Ensure proper security measures when using this module\n")

            # Show file summary instead of all instances
            files = {}
            for issue in issues:
                file = issue['filepath']
                if file not in files:
                    files[file] = 0
                files[file] += 1

            print("**Files affected:**")
            for file, count in sorted(files.items(), key=lambda x: x[1], reverse=True)[:10]:
                print(f"- `{file}`: {count} occurrences")
            if len(files) > 10:
                print(f"- ... and {len(files) - 10} more files")
            print()

    # Recommendations
    print("\n## Security Recommendations\n")

    print("### 🔴 Immediate Actions (Critical/High Priority)\n")
    if critical_issues or high_issues:
        actions = []
        if any(i['type'] == 'dangerous_function' for i in critical_issues):
            actions.append("1. **Remove eval()/exec() calls** - Replace with safe alternatives")
        if any(i['type'] == 'shell_injection' for i in critical_issues):
            actions.append("2. **Fix subprocess calls** - Use shell=False with list arguments")
        if any(i['type'] in ['hardcoded_password', 'hardcoded_api_key', 'hardcoded_secret'] for i in critical_issues):
            actions.append("3. **Remove hardcoded secrets** - Use environment variables or vault")
        if any(i['type'] == 'pickle_usage' for i in high_issues):
            actions.append("4. **Replace pickle with JSON** - Or ensure only trusted data is unpickled")

        for action in actions:
            print(action)
        print()
    else:
        print("✅ No immediate critical actions needed\n")

    print("### 🟡 Recommended Improvements\n")
    print("1. **Input Validation:** Implement comprehensive input validation for all user data")
    print("2. **Path Sanitization:** Validate and sanitize all file paths from user input")
    print("3. **Secure Configuration:** Use environment variables for sensitive configuration")
    print("4. **Error Handling:** Avoid exposing sensitive information in error messages")
    print("5. **Logging:** Ensure logs don't contain sensitive data")
    print()

    print("### 🔧 Security Tools & Practices\n")
    print("1. **Static Analysis:** Run `bandit` for comprehensive security scanning")
    print("   ```bash")
    print("   pip install bandit")
    print("   bandit -r shopify_tool/ gui/ shared/")
    print("   ```")
    print()
    print("2. **Dependency Scanning:** Use `pip-audit` to check for vulnerable dependencies")
    print("   ```bash")
    print("   pip install pip-audit")
    print("   pip-audit")
    print("   ```")
    print()
    print("3. **Code Review:** Conduct security-focused code reviews")
    print("4. **Testing:** Add security test cases")
    print("5. **Documentation:** Document security considerations and assumptions")

    # Summary table
    print("\n## Summary Table\n")
    print("| Issue Type | Count | Severity | Priority |")
    print("|------------|-------|----------|----------|")

    all_types = {}
    for issue in all_issues:
        issue_type = issue['type']
        severity = issue['severity']
        if issue_type not in all_types:
            all_types[issue_type] = {'count': 0, 'severity': severity}
        all_types[issue_type]['count'] += 1

    for issue_type, data in sorted(all_types.items(), key=lambda x: (
        {'CRITICAL': 0, 'HIGH': 1, 'MEDIUM': 2, 'LOW': 3}[x[1]['severity']], -x[1]['count']
    )):
        icon = '🔴' if data['severity'] in ['CRITICAL', 'HIGH'] else '🟡' if data['severity'] == 'MEDIUM' else '🟢'
        priority = 'IMMEDIATE' if data['severity'] == 'CRITICAL' else 'HIGH' if data['severity'] == 'HIGH' else 'MEDIUM' if data['severity'] == 'MEDIUM' else 'LOW'
        print(f"| {issue_type.replace('_', ' ').title()} | {data['count']} | {icon} {data['severity']} | {priority} |")


if __name__ == '__main__':
    main()
