#!/usr/bin/env python3
"""Script to analyze project dependencies."""

import ast
import os
import re
from pathlib import Path
from typing import Dict, Set, List
from collections import defaultdict


def parse_requirements(filepath: str = 'requirements.txt') -> Dict[str, str]:
    """Parse requirements.txt file."""
    requirements = {}

    try:
        with open(filepath, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    # Parse package==version or package>=version
                    match = re.match(r'([a-zA-Z0-9_-]+)([><=!]+)([0-9.]+)', line)
                    if match:
                        package, operator, version = match.groups()
                        requirements[package.lower()] = f"{operator}{version}"

    except FileNotFoundError:
        print(f"Warning: {filepath} not found")

    return requirements


def find_all_imports() -> Dict[str, Set[str]]:
    """Find all imports used in the codebase."""
    imports_by_file = defaultdict(set)
    all_imports = set()
    directories = ['shopify_tool', 'gui', 'shared', 'gui_main.py']

    for directory in directories:
        if os.path.isfile(directory):
            # It's a file
            files_to_check = [Path(directory)]
        elif os.path.exists(directory):
            # It's a directory
            files_to_check = Path(directory).rglob('*.py')
        else:
            continue

        for py_file in files_to_check:
            if '__pycache__' in str(py_file):
                continue

            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()

                tree = ast.parse(content)

                for node in ast.walk(tree):
                    if isinstance(node, ast.Import):
                        for alias in node.names:
                            module = alias.name.split('.')[0]
                            imports_by_file[str(py_file)].add(module)
                            all_imports.add(module)

                    elif isinstance(node, ast.ImportFrom):
                        if node.module:
                            module = node.module.split('.')[0]
                            imports_by_file[str(py_file)].add(module)
                            all_imports.add(module)

            except Exception as e:
                print(f"Error parsing {py_file}: {e}")

    return {'by_file': dict(imports_by_file), 'all': all_imports}


# Common standard library modules
STDLIB_MODULES = {
    'abc', 'ast', 'asyncio', 'base64', 'collections', 'copy', 'csv', 'datetime',
    'decimal', 'enum', 'functools', 'gc', 'glob', 'hashlib', 'io', 'itertools',
    'json', 'logging', 'math', 'operator', 'os', 'pathlib', 'pickle', 'platform',
    'queue', 'random', 're', 'shutil', 'signal', 'socket', 'sqlite3', 'statistics',
    'string', 'struct', 'subprocess', 'sys', 'tempfile', 'textwrap', 'threading',
    'time', 'traceback', 'typing', 'unittest', 'uuid', 'warnings', 'weakref',
    'xml', 'zipfile', '__future__',
}

# Mapping of import names to PyPI package names
IMPORT_TO_PACKAGE = {
    'pandas': 'pandas',
    'pd': 'pandas',
    'numpy': 'numpy',
    'np': 'numpy',
    'openpyxl': 'openpyxl',
    'xlsxwriter': 'xlsxwriter',
    'xlrd': 'xlrd',
    'xlwt': 'xlwt',
    'xlutils': 'xlutils',
    'PySide6': 'PySide6',
    'dateutil': 'python-dateutil',
    'pytz': 'pytz',
    'tzdata': 'tzdata',
    'six': 'six',
    'typing_extensions': 'typing_extensions',
}


def main():
    """Main analysis function."""
    print("# Dependency Analysis\n")

    # Parse requirements
    requirements = parse_requirements('requirements.txt')
    dev_requirements = parse_requirements('requirements-dev.txt') if os.path.exists('requirements-dev.txt') else {}

    print("## 1. Declared Dependencies\n")
    print("### Production Requirements (requirements.txt)\n")

    if requirements:
        print("| Package | Version Constraint |")
        print("|---------|-------------------|")
        for package, version in sorted(requirements.items()):
            print(f"| `{package}` | `{version}` |")
        print()
    else:
        print("⚠️ No requirements.txt found\n")

    if dev_requirements:
        print("### Development Requirements (requirements-dev.txt)\n")
        print("| Package | Version Constraint |")
        print("|---------|-------------------|")
        for package, version in sorted(dev_requirements.items()):
            print(f"| `{package}` | `{version}` |")
        print()

    # Find all imports
    print("## 2. Actual Imports Used in Code\n")
    imports_data = find_all_imports()
    all_imports = imports_data['all']

    # Separate into categories
    stdlib_used = sorted(all_imports & STDLIB_MODULES)
    third_party_used = sorted(all_imports - STDLIB_MODULES - {'shopify_tool', 'gui', 'shared'})
    internal_used = sorted(all_imports & {'shopify_tool', 'gui', 'shared'})

    print(f"**Total unique imports:** {len(all_imports)}\n")

    print("### Standard Library Imports\n")
    print(f"**Count:** {len(stdlib_used)}\n")
    print("Modules used:", ', '.join(f"`{m}`" for m in stdlib_used[:20]))
    if len(stdlib_used) > 20:
        print(f" ... and {len(stdlib_used) - 20} more")
    print("\n")

    print("### Third-Party Library Imports\n")
    print(f"**Count:** {len(third_party_used)}\n")
    for imp in third_party_used:
        print(f"- `{imp}`")
    print()

    print("### Internal Package Imports\n")
    print(f"**Count:** {len(internal_used)}\n")
    for imp in internal_used:
        print(f"- `{imp}`")
    print()

    # Cross-reference
    print("## 3. Dependency Verification\n")

    # Map imports to package names
    packages_used = set()
    for imp in third_party_used:
        package = IMPORT_TO_PACKAGE.get(imp, imp.lower())
        packages_used.add(package)

    # Find missing from requirements
    declared_packages = set(requirements.keys())
    missing_from_requirements = packages_used - declared_packages

    # Find unused in requirements
    potentially_unused = declared_packages - packages_used

    if missing_from_requirements:
        print("### ⚠️ Packages Used But Not in requirements.txt\n")
        for package in sorted(missing_from_requirements):
            print(f"- `{package}` (imported in code but not declared)")
        print("\n**Recommendation:** 🔴 Add these packages to requirements.txt")
        print("**Priority:** HIGH\n")
    else:
        print("### ✅ All Used Packages Are Declared\n")

    if potentially_unused:
        print("### ⚠️ Packages in requirements.txt Potentially Not Used\n")
        print("**Note:** This may include packages used only at runtime or indirectly.\n")
        for package in sorted(potentially_unused):
            print(f"- `{package}` (declared but not directly imported)")
        print("\n**Recommendation:** 🟡 Verify if these packages are actually needed")
        print("**Priority:** MEDIUM\n")
    else:
        print("### ✅ All Declared Packages Appear to Be Used\n")

    # Dependency tree insights
    print("## 4. Dependency Usage by Module\n")

    core_deps = set()
    gui_deps = set()
    shared_deps = set()

    for filepath, imports in imports_data['by_file'].items():
        third_party = imports - STDLIB_MODULES
        if 'shopify_tool' in filepath:
            core_deps.update(third_party)
        elif 'gui' in filepath:
            gui_deps.update(third_party)
        elif 'shared' in filepath:
            shared_deps.update(third_party)

    print("### Core Business Logic (`shopify_tool/`)\n")
    print(f"Third-party dependencies: {', '.join(sorted(core_deps - {'shopify_tool', 'shared'}))}\n")

    print("### GUI Layer (`gui/`)\n")
    print(f"Third-party dependencies: {', '.join(sorted(gui_deps - {'gui', 'shopify_tool', 'shared'}))}\n")

    print("### Shared Utilities (`shared/`)\n")
    print(f"Third-party dependencies: {', '.join(sorted(shared_deps - {'shared'}))}\n")

    # Version constraints analysis
    print("## 5. Version Constraint Analysis\n")

    flexible = []
    pinned = []
    ranges = []

    for package, version in requirements.items():
        if version.startswith('>='):
            flexible.append(package)
        elif version.startswith('=='):
            pinned.append(package)
        elif any(op in version for op in ['>', '<', '!=']):
            ranges.append(package)

    print(f"### Flexible Versions (>=)\n")
    print(f"**Count:** {len(flexible)}\n")
    if flexible:
        print("Packages:", ', '.join(f"`{p}`" for p in flexible))
        print("\n✅ **Good:** Allows minor and patch updates\n")

    print(f"### Pinned Versions (==)\n")
    print(f"**Count:** {len(pinned)}\n")
    if pinned:
        print("Packages:", ', '.join(f"`{p}`" for p in pinned))
        print("\n⚠️ **Note:** Pinned versions prevent security updates\n")

    print(f"### Range Constraints\n")
    print(f"**Count:** {len(ranges)}\n")
    if ranges:
        print("Packages:", ', '.join(f"`{p}`" for p in ranges))
        print()

    # Security considerations
    print("## 6. Security & Maintenance\n")

    print("### Version Update Strategy\n")
    if len(flexible) > len(pinned):
        print("✅ **Status:** GOOD - Mostly using flexible version constraints (>=)\n")
        print("**Benefit:** Allows receiving security patches and bug fixes\n")
    else:
        print("⚠️ **Status:** CAUTIOUS - Many pinned versions\n")
        print("**Recommendation:** Consider using >= instead of == for most packages\n")

    print("\n### Recommendations for Dependency Management\n")
    print("1. **Regular Updates:** Run `pip list --outdated` to check for updates")
    print("2. **Security Scanning:** Use `pip-audit` or `safety` to check for vulnerabilities")
    print("3. **Lock File:** Consider using `pip-compile` to generate a lock file for reproducible builds")
    print("4. **Virtual Environment:** Always use virtual environments to isolate dependencies")
    print("5. **Minimal Dependencies:** Periodically review and remove unused packages")

    # Summary
    print("\n## Summary\n")
    print("| Metric | Value | Status |")
    print("|--------|-------|--------|")
    print(f"| Declared Dependencies | {len(requirements)} | - |")
    print(f"| Dev Dependencies | {len(dev_requirements)} | - |")
    print(f"| Third-Party Imports | {len(third_party_used)} | - |")
    print(f"| Missing from requirements.txt | {len(missing_from_requirements)} | {'🔴 ACTION NEEDED' if missing_from_requirements else '✅ GOOD'} |")
    print(f"| Potentially Unused | {len(potentially_unused)} | {'🟡 REVIEW' if potentially_unused else '✅ GOOD'} |")
    print(f"| Flexible Version Constraints | {len(flexible)} | ✅ GOOD |")
    print(f"| Pinned Versions | {len(pinned)} | {'⚠️ REVIEW' if pinned else '✅ GOOD'} |")

    # Priority actions
    print("\n## Priority Actions\n")

    if missing_from_requirements:
        print("### 🔴 HIGH PRIORITY\n")
        print("1. Add missing packages to requirements.txt:")
        for package in sorted(missing_from_requirements):
            print(f"   - `{package}`")
        print()

    if potentially_unused:
        print("### 🟡 MEDIUM PRIORITY\n")
        print("1. Review potentially unused packages:")
        for package in sorted(potentially_unused):
            print(f"   - `{package}` - check if really needed")
        print()

    print("### 🟢 LOW PRIORITY\n")
    print("1. Set up automated dependency scanning")
    print("2. Create a dependency update schedule")
    print("3. Document dependency purposes in requirements.txt")


if __name__ == '__main__':
    main()
