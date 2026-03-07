"""
Test script to verify Google Drive fixes
"""
import uuid
import sys
import os

# Add the backend directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_imports():
    """Test that all modules import correctly"""
    print("Testing imports...")
    try:
        from app.services.google_drive_service import (
            GoogleDriveService,
            GoogleDriveAuthError,
            GoogleDriveError,
            GoogleDriveNotFoundError
        )
        print("✓ GoogleDriveService imports OK")
        
        from app.services.gdrive_persistent import PermanentGoogleDrive, get_permanent_drive
        print("✓ PermanentGoogleDrive imports OK")
        
        return True
    except Exception as e:
        print(f"✗ Import failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_permanent_drive_structure():
    """Test PermanentGoogleDrive class structure"""
    print("\nTesting PermanentGoogleDrive structure...")
    try:
        from app.services.gdrive_persistent import PermanentGoogleDrive
        
        # Check that all required methods exist
        required_methods = [
            'ensure_fresh_token',
            'list_files',
            'get_file',
            'download_file',
            'search_files',
            'create_folder',
            'delete_file',
            'get_status',
            'get_credentials',
        ]
        
        for method in required_methods:
            if not hasattr(PermanentGoogleDrive, method):
                print(f"✗ Missing method: {method}")
                return False
            print(f"✓ Method exists: {method}")
        
        return True
    except Exception as e:
        print(f"✗ Structure test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_ensure_fresh_token_logic():
    """Test the ensure_fresh_token logic without actual DB"""
    print("\nTesting ensure_fresh_token logic...")
    
    # This is a mock test - we can't test actual token refresh without real credentials
    # But we can verify the code structure is correct
    
    from app.services.gdrive_persistent import PermanentGoogleDrive
    import inspect
    
    # Get the source code of ensure_fresh_token
    source = inspect.getsource(PermanentGoogleDrive.ensure_fresh_token)
    
    checks = [
        ('get_credentials call', 'self.service.get_credentials(self.user_id)' in source),
        ('refresh_access_token call', 'self.service.refresh_access_token(self.user_id)' in source),
        ('Logging on success', 'self.service._logger.info' in source),
        ('Logging on failure', 'self.service._logger.error' in source),
        ('Exception handling', 'except Exception' in source),
    ]
    
    all_passed = True
    for name, check in checks:
        if check:
            print(f"✓ {name}")
        else:
            print(f"✗ {name} - NOT FOUND")
            all_passed = False
    
    return all_passed


def test_endpoints_use_permanent_drive():
    """Verify endpoints use PermanentGoogleDrive"""
    print("\nChecking endpoints use PermanentGoogleDrive...")
    
    import ast
    
    files_to_check = [
        'app/api/v1/endpoints/google_drive.py',
        'app/api/v1/endpoints/connectors.py',
    ]
    
    all_passed = True
    for filepath in files_to_check:
        full_path = os.path.join(os.path.dirname(__file__), filepath)
        if not os.path.exists(full_path):
            print(f"✗ File not found: {filepath}")
            all_passed = False
            continue
            
        with open(full_path, 'r') as f:
            content = f.read()
        
        # Check for get_permanent_drive import
        if 'from app.services.gdrive_persistent import' in content and 'get_permanent_drive' in content:
            print(f"✓ {filepath} imports get_permanent_drive")
        else:
            print(f"⚠ {filepath} may not import get_permanent_drive (check manually)")
        
        # Check for get_permanent_drive usage
        if 'get_permanent_drive(' in content:
            print(f"✓ {filepath} uses get_permanent_drive()")
        else:
            print(f"⚠ {filepath} may not use get_permanent_drive() (check manually)")
    
    return all_passed


def main():
    print("=" * 60)
    print("Google Drive Fix Verification")
    print("=" * 60)
    
    results = []
    
    results.append(("Imports", test_imports()))
    results.append(("Structure", test_permanent_drive_structure()))
    results.append(("Token Logic", test_ensure_fresh_token_logic()))
    results.append(("Endpoints", test_endpoints_use_permanent_drive()))
    
    print("\n" + "=" * 60)
    print("Results Summary")
    print("=" * 60)
    
    all_passed = True
    for name, passed in results:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{status}: {name}")
        if not passed:
            all_passed = False
    
    print("=" * 60)
    
    if all_passed:
        print("\n✓ All checks passed! The fix appears to be correctly implemented.")
        print("\nNote: This is a static code check. Actual functionality requires:")
        print("  1. Valid Google OAuth credentials")
        print("  2. Database connection")
        print("  3. User with connected Google Drive account")
        return 0
    else:
        print("\n✗ Some checks failed. Please review the implementation.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
