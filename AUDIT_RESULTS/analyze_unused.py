#!/usr/bin/env python3
"""Script to find unused code, imports, and variables."""

import ast
import os
import re
from pathlib import Path
from typing import Dict, List, Set
from collections import defaultdict


def find_unused_imports() -> Dict[str, List]:
    """Find potentially unused imports."""
    results = defaultdict(list)
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
                imports = set()
                used_names = set()

                # Collect imports
                for node in ast.walk(tree):
                    if isinstance(node, ast.Import):
                        for alias in node.names:
                            name = alias.asname if alias.asname else alias.name
                            imports.add((name, node.lineno, alias.name))
                    elif isinstance(node, ast.ImportFrom):
                        for alias in node.names:
                            name = alias.asname if alias.asname else alias.name
                            imports.add((name, node.lineno, f"{node.module}.{alias.name}"))

                # Collect used names (simplified - doesn't catch all cases)
                for node in ast.walk(tree):
                    if isinstance(node, ast.Name):
                        used_names.add(node.id)
                    elif isinstance(node, ast.Attribute):
                        if isinstance(node.value, ast.Name):
                            used_names.add(node.value.id)

                # Find potentially unused
                for name, lineno, full_name in imports:
                    if name not in used_names and name != '*':
                        results[str(py_file)].append({
                            'name': name,
                            'full_name': full_name,
                            'line': lineno
                        })

            except Exception as e:
                print(f"Error analyzing {py_file}: {e}")

    return results


def find_commented_code() -> Dict[str, List]:
    """Find blocks of commented out code."""
    results = defaultdict(list)
    directories = ['shopify_tool', 'gui', 'shared']

    # Pattern to detect code-like comments
    code_patterns = [
        r'#\s*(def |class |import |from |if |for |while |try |except |with )',
        r'#\s*\w+\s*=\s*',
        r'#\s*return ',
        r'#\s*print\(',
    ]

    for directory in directories:
        if not os.path.exists(directory):
            continue

        for py_file in Path(directory).rglob('*.py'):
            if '__pycache__' in str(py_file):
                continue

            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    lines = f.readlines()

                in_code_block = False
                block_start = 0
                block_lines = []

                for i, line in enumerate(lines, 1):
                    stripped = line.strip()
                    is_code_comment = any(re.search(pattern, stripped) for pattern in code_patterns)

                    if is_code_comment:
                        if not in_code_block:
                            in_code_block = True
                            block_start = i
                            block_lines = [i]
                        else:
                            block_lines.append(i)
                    else:
                        if in_code_block and len(block_lines) >= 3:
                            results[str(py_file)].append({
                                'start': block_start,
                                'end': block_lines[-1],
                                'count': len(block_lines)
                            })
                        in_code_block = False
                        block_lines = []

            except Exception as e:
                print(f"Error analyzing {py_file}: {e}")

    return results


def find_todo_fixme_comments() -> Dict[str, List]:
    """Find TODO, FIXME, XXX, HACK comments."""
    results = defaultdict(list)
    directories = ['shopify_tool', 'gui', 'shared']

    patterns = {
        'TODO': re.compile(r'#.*\bTODO\b', re.IGNORECASE),
        'FIXME': re.compile(r'#.*\bFIXME\b', re.IGNORECASE),
        'XXX': re.compile(r'#.*\bXXX\b'),
        'HACK': re.compile(r'#.*\bHACK\b', re.IGNORECASE),
        'BUG': re.compile(r'#.*\bBUG\b', re.IGNORECASE),
    }

    for directory in directories:
        if not os.path.exists(directory):
            continue

        for py_file in Path(directory).rglob('*.py'):
            if '__pycache__' in str(py_file):
                continue

            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    lines = f.readlines()

                for i, line in enumerate(lines, 1):
                    for tag, pattern in patterns.items():
                        if pattern.search(line):
                            results[str(py_file)].append({
                                'tag': tag,
                                'line': i,
                                'text': line.strip()
                            })

            except Exception as e:
                print(f"Error analyzing {py_file}: {e}")

    return results


def main():
    """Main analysis function."""
    print("# Unused Code Analysis\n")

    # Unused imports
    print("## 1. Potentially Unused Imports\n")
    unused_imports = find_unused_imports()

    if unused_imports:
        total_unused = sum(len(imports) for imports in unused_imports.values())
        print(f"**Found:** {total_unused} potentially unused imports in {len(unused_imports)} files\n")
        print("**Note:** This is a heuristic analysis and may have false positives.\n")

        # Sort by file with most unused imports
        sorted_files = sorted(unused_imports.items(), key=lambda x: len(x[1]), reverse=True)

        print("### Files with Most Unused Imports\n")
        for filepath, imports in sorted_files[:15]:
            print(f"#### `{filepath}` ({len(imports)} unused)\n")
            for imp in imports[:10]:
                print(f"- Line {imp['line']}: `{imp['full_name']}`")
            if len(imports) > 10:
                print(f"- ... and {len(imports) - 10} more")
            print()

        print("**Recommendation:** 🟡 Review and remove unused imports to reduce clutter")
        print("**Priority:** MEDIUM\n")
        print("**Note:** Use a linter like `pylint` or `flake8` with `--select=F401` for more accurate results\n")
    else:
        print("✅ No obviously unused imports detected\n")

    # Commented code
    print("## 2. Commented Out Code Blocks\n")
    commented_code = find_commented_code()

    if commented_code:
        total_blocks = sum(len(blocks) for blocks in commented_code.values())
        print(f"**Found:** {total_blocks} blocks of commented code in {len(commented_code)} files\n")

        sorted_files = sorted(commented_code.items(), key=lambda x: sum(b['count'] for b in x[1]), reverse=True)

        for filepath, blocks in sorted_files[:10]:
            total_lines = sum(b['count'] for b in blocks)
            print(f"### `{filepath}` ({len(blocks)} blocks, {total_lines} lines)\n")
            for block in blocks:
                print(f"- Lines {block['start']}-{block['end']} ({block['count']} lines)")
            print()

        print("**Recommendation:** 🟡 Remove commented code or document why it's kept")
        print("**Priority:** MEDIUM")
        print("**Rationale:** Version control (git) maintains history - commented code adds clutter\n")
    else:
        print("✅ No large blocks of commented code detected\n")

    # TODO/FIXME comments
    print("## 3. TODO, FIXME, and Similar Comments\n")
    todos = find_todo_fixme_comments()

    if todos:
        # Count by tag type
        by_tag = defaultdict(int)
        for filepath, comments in todos.items():
            for comment in comments:
                by_tag[comment['tag']] += 1

        total_todos = sum(by_tag.values())
        print(f"**Found:** {total_todos} action comments across {len(todos)} files\n")

        print("### Breakdown by Type\n")
        for tag, count in sorted(by_tag.items(), key=lambda x: x[1], reverse=True):
            print(f"- **{tag}:** {count}")
        print()

        # Show examples by tag
        for tag in ['FIXME', 'BUG', 'TODO', 'HACK', 'XXX']:
            tag_items = []
            for filepath, comments in todos.items():
                for comment in comments:
                    if comment['tag'] == tag:
                        tag_items.append((filepath, comment))

            if tag_items:
                print(f"### {tag} Comments ({len(tag_items)})\n")
                for filepath, comment in tag_items[:10]:
                    print(f"- `{filepath}:{comment['line']}` - {comment['text'][1:].strip()}")
                if len(tag_items) > 10:
                    print(f"- ... and {len(tag_items) - 10} more")
                print()

        priority = "HIGH" if by_tag['FIXME'] + by_tag.get('BUG', 0) > 5 else "MEDIUM"
        icon = "🔴" if priority == "HIGH" else "🟡"

        print(f"**Recommendation:** {icon} Review and address action comments, especially FIXME and BUG")
        print(f"**Priority:** {priority}\n")
    else:
        print("✅ No TODO/FIXME comments found\n")

    # Summary
    print("\n## Summary\n")
    print("| Category | Count | Priority | Action |")
    print("|----------|-------|----------|--------|")

    unused_count = sum(len(imports) for imports in unused_imports.values())
    commented_count = sum(len(blocks) for blocks in commented_code.values())
    todo_count = sum(len(comments) for comments in todos.values())
    fixme_count = sum(1 for filepath, comments in todos.items() for c in comments if c['tag'] in ['FIXME', 'BUG'])

    print(f"| Unused Imports | {unused_count} | 🟡 MEDIUM | Review and remove |")
    print(f"| Commented Code Blocks | {commented_count} | 🟡 MEDIUM | Remove or document |")
    print(f"| TODO Comments | {todo_count - fixme_count} | 🟢 LOW | Track and address |")
    print(f"| FIXME/BUG Comments | {fixme_count} | {'🔴 HIGH' if fixme_count > 5 else '🟡 MEDIUM'} | Address issues |")

    print("\n## Recommendations\n")
    print("1. **Run linter:** Use `pylint` or `flake8` for more accurate unused import detection")
    print("2. **Clean commented code:** Remove or add explanation for why it's kept")
    print("3. **Address FIXMEs:** Prioritize fixing issues marked as FIXME or BUG")
    print("4. **Track TODOs:** Consider moving TODOs to issue tracker for better visibility")


if __name__ == '__main__':
    main()
