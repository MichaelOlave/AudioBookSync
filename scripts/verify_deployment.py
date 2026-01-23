#!/usr/bin/env python
"""Verify deployment of eliminate local storage changes."""

import sys
from pathlib import Path

def print_header(title):
    """Print section header."""
    print(f"\n{'='*70}")
    print(f"  {title}")
    print(f"{'='*70}\n")

def check_config_changes():
    """Verify configuration changes."""
    print_header("Step 1: Configuration Changes")

    from src.core.config import Config

    checks = []

    # Check that old directories are removed
    has_download_dir = hasattr(Config, 'DOWNLOAD_DIR')
    has_decrypted_dir = hasattr(Config, 'DECRYPTED_DIR')
    has_log_dir = hasattr(Config, 'LOG_DIR')

    checks.append(("DOWNLOAD_DIR removed", not has_download_dir, "✓" if not has_download_dir else "✗"))
    checks.append(("DECRYPTED_DIR removed", not has_decrypted_dir, "✓" if not has_decrypted_dir else "✗"))
    checks.append(("LOG_DIR still exists", has_log_dir, "✓" if has_log_dir else "✗"))

    # Check LOG_DIR default value
    if has_log_dir:
        checks.append(("LOG_DIR default value", Config.LOG_DIR == "logs", f"✓ (logs)" if Config.LOG_DIR == "logs" else f"✗ ({Config.LOG_DIR})"))

    for check_name, result, symbol in checks:
        status = "PASS" if result else "FAIL"
        print(f"  {symbol} {check_name}: {status}")

    all_pass = all(c[1] for c in checks)
    print(f"\n  Configuration: {'✓ READY' if all_pass else '✗ ISSUES FOUND'}\n")
    return all_pass

def check_function_signatures():
    """Verify function parameter changes."""
    print_header("Step 2: Function Signatures")

    import inspect
    from src.operations.downloader import download_book as downloader_download_book
    from src.operations.decryptor import decrypt_book as decryptor_decrypt_book

    checks = []

    # Check downloader signature
    downloader_sig = inspect.signature(downloader_download_book)
    downloader_params = list(downloader_sig.parameters.keys())
    expected_downloader = ['book', 'user_id', 'progress_callback']
    checks.append((
        "download_book() signature",
        downloader_params == expected_downloader,
        f"{'✓' if downloader_params == expected_downloader else '✗'} {downloader_params}"
    ))

    # Check decryptor signature
    decryptor_sig = inspect.signature(decryptor_decrypt_book)
    decryptor_params = list(decryptor_sig.parameters.keys())
    required_params = ['book', 'user_id', 'encrypted_file_path', 'progress_callback', 'is_retry']
    has_required = all(p in decryptor_params for p in required_params)
    checks.append((
        "decrypt_book() parameters",
        has_required,
        f"{'✓' if has_required else '✗'} {decryptor_params}"
    ))

    for check_name, result, details in checks:
        status = "PASS" if result else "FAIL"
        print(f"  {details.split()[0]} {check_name}: {status}")
        if len(details.split()) > 1:
            print(f"      Details: {details[1:]}")

    all_pass = all(c[1] for c in checks)
    print(f"\n  Function Signatures: {'✓ READY' if all_pass else '✗ ISSUES FOUND'}\n")
    return all_pass

def check_removed_functions():
    """Verify deprecated functions are removed."""
    print_header("Step 3: Removed Functions")

    from src.operations import downloader, decryptor

    checks = []

    # Check functions are removed
    has_validate_book = hasattr(downloader, 'validate_book')
    has_validate_decrypted = hasattr(decryptor, 'validate_decrypted_book')
    has_upload_downloaded = hasattr(downloader, '_upload_downloaded_file_to_minio')

    checks.append(("validate_book() removed", not has_validate_book, "✓" if not has_validate_book else "✗"))
    checks.append(("validate_decrypted_book() removed", not has_validate_decrypted, "✓" if not has_validate_decrypted else "✗"))
    checks.append(("_upload_downloaded_file_to_minio() removed", not has_upload_downloaded, "✓" if not has_upload_downloaded else "✗"))

    # Check new functions exist
    has_upload_encrypted = hasattr(decryptor, '_upload_encrypted_file_to_minio')
    has_upload_decrypted = hasattr(decryptor, '_upload_decrypted_file_to_minio')

    checks.append(("_upload_encrypted_file_to_minio() added", has_upload_encrypted, "✓" if has_upload_encrypted else "✗"))
    checks.append(("_upload_decrypted_file_to_minio() added", has_upload_decrypted, "✓" if has_upload_decrypted else "✗"))

    for check_name, result, symbol in checks:
        status = "PASS" if result else "FAIL"
        print(f"  {symbol} {check_name}: {status}")

    all_pass = all(c[1] for c in checks)
    print(f"\n  Removed Functions: {'✓ READY' if all_pass else '✗ ISSUES FOUND'}\n")
    return all_pass

def check_database_model():
    """Verify database model changes."""
    print_header("Step 4: Database Model Changes")

    from src.database.models.decryption import DecryptionStatus
    from sqlalchemy import inspect as sqlalchemy_inspect

    mapper = sqlalchemy_inspect(DecryptionStatus)
    columns = {c.key for c in mapper.columns}

    checks = []

    # Check new column exists
    has_encrypted_key = 'encrypted_file_object_key' in columns
    checks.append(("encrypted_file_object_key column added", has_encrypted_key, "✓" if has_encrypted_key else "✗"))

    # Verify existing columns still present
    required_columns = ['asin', 'status', 'output_path', 'input_path', 'decryption_started_at', 'decryption_completed_at']
    has_all_columns = all(col in columns for col in required_columns)
    checks.append(("Existing columns preserved", has_all_columns, "✓" if has_all_columns else "✗"))

    for check_name, result, symbol in checks:
        status = "PASS" if result else "FAIL"
        print(f"  {symbol} {check_name}: {status}")

    all_pass = all(c[1] for c in checks)
    print(f"\n  Database Model: {'✓ READY' if all_pass else '✗ ISSUES FOUND'}\n")
    return all_pass

def check_migration_file():
    """Verify migration file exists and is valid."""
    print_header("Step 5: Database Migration")

    migration_path = Path("database/alembic/versions/003_add_encrypted_file_fallback.py")
    checks = []

    # Check migration file exists
    exists = migration_path.exists()
    checks.append(("Migration file exists", exists, "✓" if exists else "✗"))

    if exists:
        # Check migration structure
        with open(migration_path, 'r') as f:
            content = f.read()

        has_upgrade = 'def upgrade()' in content
        has_downgrade = 'def downgrade()' in content
        has_encrypted_column = "encrypted_file_object_key" in content
        has_revision_id = "003_encrypted_fallback" in content

        checks.append(("Has upgrade() function", has_upgrade, "✓" if has_upgrade else "✗"))
        checks.append(("Has downgrade() function", has_downgrade, "✓" if has_downgrade else "✗"))
        checks.append(("Adds encrypted_file_object_key", has_encrypted_column, "✓" if has_encrypted_column else "✗"))
        checks.append(("Has correct revision ID", has_revision_id, "✓" if has_revision_id else "✗"))

    for check_name, result, symbol in checks:
        status = "PASS" if result else "FAIL"
        print(f"  {symbol} {check_name}: {status}")

    all_pass = all(c[1] for c in checks)
    print(f"\n  Migration File: {'✓ READY' if all_pass else '✗ ISSUES FOUND'}\n")
    return all_pass

def check_retry_mechanism():
    """Verify retry mechanism is implemented."""
    print_header("Step 6: Retry Mechanism")

    from src.celery_app.tasks import retry_tasks
    import inspect

    checks = []

    # Check retry task exists
    has_retry_task = hasattr(retry_tasks, 'retry_failed_decrypts_from_minio')
    checks.append(("retry_failed_decrypts_from_minio() task exists", has_retry_task, "✓" if has_retry_task else "✗"))

    # Check cleanup task updated
    from src.celery_app.tasks import cleanup_tasks
    cleanup_code = inspect.getsource(cleanup_tasks._async_cleanup_minio)
    has_encrypted_query = 'encrypted_file_object_key' in cleanup_code
    checks.append(("Cleanup task handles encrypted files", has_encrypted_query, "✓" if has_encrypted_query else "✗"))

    for check_name, result, symbol in checks:
        status = "PASS" if result else "FAIL"
        print(f"  {symbol} {check_name}: {status}")

    all_pass = all(c[1] for c in checks)
    print(f"\n  Retry Mechanism: {'✓ READY' if all_pass else '✗ ISSUES FOUND'}\n")
    return all_pass

def check_imports():
    """Verify all imports work correctly."""
    print_header("Step 7: Import Verification")

    imports = [
        ("src.core.config", "Config"),
        ("src.operations.downloader", "download_book"),
        ("src.operations.decryptor", "decrypt_book"),
        ("src.database.models.decryption", "DecryptionStatus"),
        ("src.celery_app.tasks.cleanup_tasks", "cleanup_orphaned_minio_files"),
        ("src.celery_app.tasks.retry_tasks", "retry_failed_decrypts_from_minio"),
    ]

    checks = []
    for module_name, item_name in imports:
        try:
            module = __import__(module_name, fromlist=[item_name])
            has_item = hasattr(module, item_name)
            checks.append((f"{module_name}.{item_name}", has_item, "✓" if has_item else "✗"))
        except ImportError as e:
            checks.append((f"{module_name}.{item_name}", False, f"✗ {str(e)}"))

    for check_name, result, symbol in checks:
        status = "PASS" if result else "FAIL"
        print(f"  {symbol} {check_name}: {status}")

    all_pass = all(c[1] for c in checks)
    print(f"\n  Imports: {'✓ READY' if all_pass else '✗ ISSUES FOUND'}\n")
    return all_pass

def main():
    """Run all verification checks."""
    print("\n" + "="*70)
    print("  AudioBookSync Deployment Verification")
    print("  Eliminate Local Storage Changes")
    print("="*70)

    try:
        results = {
            "Config Changes": check_config_changes(),
            "Function Signatures": check_function_signatures(),
            "Removed Functions": check_removed_functions(),
            "Database Model": check_database_model(),
            "Migration File": check_migration_file(),
            "Retry Mechanism": check_retry_mechanism(),
            "Imports": check_imports(),
        }
    except Exception as e:
        print(f"\n✗ ERROR during verification: {e}")
        import traceback
        traceback.print_exc()
        return 1

    # Summary
    print_header("SUMMARY")
    all_pass = True
    for check_name, result in results.items():
        symbol = "✓" if result else "✗"
        status = "READY" if result else "ISSUES"
        print(f"  {symbol} {check_name}: {status}")
        all_pass = all_pass and result

    print("\n" + "="*70)
    if all_pass:
        print("  ✓ ALL CHECKS PASSED - READY FOR DEPLOYMENT")
        print("="*70 + "\n")
        return 0
    else:
        print("  ✗ SOME CHECKS FAILED - REVIEW ISSUES ABOVE")
        print("="*70 + "\n")
        return 1

if __name__ == "__main__":
    sys.exit(main())
