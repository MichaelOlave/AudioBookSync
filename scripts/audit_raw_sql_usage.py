#!/usr/bin/env python
"""Audit codebase for raw SQL module usage.

This script identifies all imports and usages of raw SQL modules to verify
they can be safely removed without breaking functionality.
"""

import os
import re
from pathlib import Path
from collections import defaultdict
from typing import Dict, List, Set


# Raw SQL modules to audit
RAW_SQL_MODULES = [
    "db_users",
    "db_books", 
    "db_sync",
    "db_errors",
    "db_book_metadata",
    "db_contributors",
    "db_book_contributors",
    "db_media_info",
    "db_reading_progress",
    "db_book_availability",
    "db_companion_materials",
    "db_downloads",
    "db_decryptions",
    "db_pool",
    "db_books_consolidated",
    "db_operations_consolidated",
]


def find_imports_in_file(filepath: str, modules: List[str]) -> Dict[str, List[str]]:
    """Find imports of raw SQL modules in a file.
    
    Args:
        filepath: Path to Python file
        modules: List of module names to search for
        
    Returns:
        Dict mapping module names to list of import statements found
    """
    imports = defaultdict(list)
    
    try:
        with open(filepath, 'r') as f:
            content = f.read()
    except Exception:
        return imports
    
    for module in modules:
        # Pattern 1: from ...database.db_users import X
        pattern1 = rf"from\s+[.\w]*database\.{module}\s+import"
        matches1 = re.findall(pattern1, content)
        if matches1:
            imports[module].extend(matches1)
        
        # Pattern 2: import ...database.db_users
        pattern2 = rf"import\s+[.\w]*database\.{module}"
        matches2 = re.findall(pattern2, content)
        if matches2:
            imports[module].extend(matches2)
        
        # Pattern 3: db_users.function_name
        pattern3 = rf"{module}\."
        if re.search(pattern3, content):
            imports[module].append(f"{module}.<function_calls>")
    
    return imports


def audit_codebase(root_dir: str = "src") -> Dict[str, List[tuple]]:
    """Audit entire codebase for raw SQL module usage.
    
    Args:
        root_dir: Root directory to search (default: src)
        
    Returns:
        Dict mapping module names to list of (filepath, usage_count) tuples
    """
    usage_map = defaultdict(list)
    
    # Find all Python files
    for root, dirs, files in os.walk(root_dir):
        # Skip test directories (tests are being migrated)
        if 'test' in root or '__pycache__' in root:
            continue
            
        for file in files:
            if file.endswith('.py'):
                filepath = os.path.join(root, file)
                imports = find_imports_in_file(filepath, RAW_SQL_MODULES)
                
                for module, import_stmts in imports.items():
                    if import_stmts:
                        usage_map[module].append((filepath, len(import_stmts)))
    
    return usage_map


def print_audit_report(usage_map: Dict[str, List[tuple]]):
    """Print formatted audit report.
    
    Args:
        usage_map: Results from audit_codebase()
    """
    print("\n" + "=" * 80)
    print("RAW SQL MODULE AUDIT REPORT")
    print("=" * 80)
    
    active_imports = {k: v for k, v in usage_map.items() if v}
    unused_modules = {k for k in RAW_SQL_MODULES if k not in active_imports}
    
    print(f"\nTotal Modules to Audit: {len(RAW_SQL_MODULES)}")
    print(f"Modules with Active Imports: {len(active_imports)}")
    print(f"Modules Safe to Remove: {len(unused_modules)}")
    
    if active_imports:
        print("\n" + "-" * 80)
        print("MODULES WITH ACTIVE IMPORTS (CANNOT REMOVE YET)")
        print("-" * 80)
        
        for module in sorted(active_imports.keys()):
            files = active_imports[module]
            total_usage = sum(count for _, count in files)
            print(f"\n{module}:")
            print(f"  Total imports: {total_usage}")
            print(f"  Files using it ({len(files)}):")
            for filepath, count in sorted(files):
                print(f"    • {filepath} ({count} import(s))")
    
    if unused_modules:
        print("\n" + "-" * 80)
        print("MODULES SAFE TO REMOVE (NO ACTIVE IMPORTS)")
        print("-" * 80)
        for module in sorted(unused_modules):
            print(f"  ✓ {module}")
    
    print("\n" + "=" * 80)
    print("PHASE 7 READINESS CHECK")
    print("=" * 80)
    
    if not active_imports:
        print("\n✅ ALL RAW SQL MODULES CAN BE SAFELY REMOVED")
        print("   No active imports found in src/ codebase")
        print("   Ready to proceed with Phase 7 cleanup")
        return 0
    else:
        print(f"\n⚠️  {len(active_imports)} MODULES STILL IN USE")
        print("   Cannot proceed with Phase 7 until imports are migrated")
        print("\n   Required Actions:")
        for module in sorted(active_imports.keys()):
            print(f"   - Migrate imports from {module} to ORM services")
        return 1


if __name__ == "__main__":
    print("Starting raw SQL module audit...")
    usage_map = audit_codebase()
    exit_code = print_audit_report(usage_map)
    
    exit(exit_code)
