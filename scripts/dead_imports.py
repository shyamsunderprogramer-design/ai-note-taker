"""
Tool: dead_imports.py

Scans a Python project for unused imports — symbols imported but
never referenced in the file. Used by the Fix #44 repo-hygiene
pass to flag files that need a cleanup round.

Usage:
    python3 scripts/dead_imports.py backend/ --exclude venv
    python3 scripts/dead_imports.py backend/ --exclude venv --json
"""

import ast
import json
import os
import sys
from pathlib import Path
from typing import Dict, List, Set, Tuple


def find_imports(tree: ast.AST) -> List[Tuple[str, str, int]]:
    """Return [(module, name, lineno), ...] for all imports in a file.

    Each `import x.y` produces (x.y, y, lineno). Each
    `from x.y import z` produces (x.y, z, lineno).
    """
    imports = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for n in node.names:
                # `import x.y as z` → track 'z' as the local name
                local = n.asname or n.name.split(".")[0]
                imports.append((n.name, local, node.lineno))
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            for n in node.names:
                local = n.asname or n.name
                imports.append((f"{module}.{n.name}", local, node.lineno))
    return imports


def find_names_used(tree: ast.AST) -> Set[str]:
    """Return all Name nodes (the bare names referenced in the file)."""
    used = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Name):
            used.add(node.id)
        elif isinstance(node, ast.Attribute):
            # Walk the chain to find the root
            cur = node
            while isinstance(cur, ast.Attribute):
                cur = cur.value
            if isinstance(cur, ast.Name):
                used.add(cur.id)
    return used


def scan_file(path: Path) -> List[Dict]:
    """Return list of unused imports in a single file."""
    try:
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(path))
    except (SyntaxError, UnicodeDecodeError):
        return []

    imports = find_imports(tree)
    used = find_names_used(tree)

    # `import os` → use 'os'
    # `from x import y` → use 'y' (or 'asname' if aliased)
    unused = []
    for module, local, lineno in imports:
        # 'from x import *' — local == '*' — skip
        if local == "*":
            continue
        if local not in used:
            unused.append({
                "module": module,
                "local": local,
                "lineno": lineno,
            })
    return unused


def scan_directory(
    root: Path,
    exclude: List[str] = None,
) -> Dict[str, List[Dict]]:
    """Scan a directory tree for unused imports.

    Returns {filepath: [unused_imports]}.
    """
    exclude = exclude or []
    results: Dict[str, List[Dict]] = {}

    for path in root.rglob("*.py"):
        # Skip excluded paths
        if any(ex in str(path) for ex in exclude):
            continue
        unused = scan_file(path)
        if unused:
            results[str(path)] = unused
    return results


def main() -> int:
    import argparse
    p = argparse.ArgumentParser(description="Find unused Python imports")
    p.add_argument("root", type=Path, help="Directory to scan")
    p.add_argument("--exclude", action="append", default=[],
                   help="Substring to exclude (can repeat)")
    p.add_argument("--json", action="store_true", help="JSON output")
    args = p.parse_args()

    if not args.root.exists():
        print(f"error: {args.root} does not exist", file=sys.stderr)
        return 1

    results = scan_directory(args.root, exclude=args.exclude)

    if args.json:
        print(json.dumps(results, indent=2))
    else:
        total = sum(len(v) for v in results.values())
        print(f"Found {total} unused imports across {len(results)} files")
        for path, unused in sorted(results.items())[:50]:
            print(f"\n{path}")
            for u in unused:
                print(f"  L{u['lineno']}: {u['module']} (as {u['local']})")
        if len(results) > 50:
            print(f"\n... and {len(results) - 50} more files")
    return 0


if __name__ == "__main__":
    sys.exit(main())
