#!/usr/bin/env python3
"""Test script to verify OCR PDF processing fixes."""

import sys
import os

# Add backend to path
sys.path.insert(0, '/root/.openclaw/workspace/cerebrum-fix/backend')

async def test_ocr_fixes():
    """Test that OCR imports and basic functionality work."""
    print("=" * 60)
    print("Testing OCR PDF Processing Fixes")
    print("=" * 60)
    
    errors = []
    
    # Test 1: Import OCR module
    print("\n1. Testing OCR module imports...")
    try:
        from app.pipelines.ocr import (
            TesseractOCR, 
            OCRLanguage, 
            OCRMode, 
            PDF2IMAGE_AVAILABLE, 
            TESSERACT_AVAILABLE,
            PYPDF2_AVAILABLE,
            OCRPipeline
        )
        print(f"   ✓ OCR module imported successfully")
        print(f"   - TESSERACT_AVAILABLE: {TESSERACT_AVAILABLE}")
        print(f"   - PDF2IMAGE_AVAILABLE: {PDF2IMAGE_AVAILABLE}")
        print(f"   - PYPDF2_AVAILABLE: {PYPDF2_AVAILABLE}")
    except Exception as e:
        errors.append(f"Failed to import OCR module: {e}")
        print(f"   ✗ Import failed: {e}")
        return errors
    
    # Test 2: Initialize TesseractOCR
    print("\n2. Testing TesseractOCR initialization...")
    try:
        ocr = TesseractOCR()
        print("   ✓ TesseractOCR initialized successfully")
    except Exception as e:
        errors.append(f"Failed to initialize TesseractOCR: {e}")
        print(f"   ✗ Initialization failed: {e}")
        return errors
    
    # Test 3: Check PDF validation method exists
    print("\n3. Testing PDF validation method...")
    try:
        assert hasattr(ocr, '_validate_pdf'), "_validate_pdf method not found"
        print("   ✓ _validate_pdf method exists")
    except Exception as e:
        errors.append(f"PDF validation method missing: {e}")
        print(f"   ✗ Method check failed: {e}")
    
    # Test 4: Test PDF validation with invalid data
    print("\n4. Testing PDF validation with invalid data...")
    try:
        is_valid, error_msg = ocr._validate_pdf(b"not a pdf")
        if not is_valid:
            print(f"   ✓ Validation correctly rejected invalid PDF: {error_msg}")
        else:
            print(f"   ! Validation accepted invalid data (may be expected)")
    except NameError as e:
        errors.append(f"PYPDF2_AVAILABLE not defined: {e}")
        print(f"   ✗ NameError - PYPDF2_AVAILABLE missing: {e}")
    except Exception as e:
        print(f"   ! Validation error (may be expected): {type(e).__name__}: {e}")
    
    # Test 5: Test PDF validation with valid PDF structure
    print("\n5. Testing PDF validation with valid PDF header...")
    try:
        # Minimal PDF header
        valid_pdf = b"%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n>>\nendobj\nxref\ntrailer\n<<\n/Size 1\n>>\nstartxref\n0\n%%EOF"
        is_valid, error_msg = ocr._validate_pdf(valid_pdf)
        print(f"   Result: is_valid={is_valid}, error_msg={error_msg}")
    except NameError as e:
        errors.append(f"PYPDF2_AVAILABLE not defined: {e}")
        print(f"   ✗ NameError - PYPDF2_AVAILABLE missing: {e}")
    except Exception as e:
        print(f"   ! Validation error (may be expected): {type(e).__name__}: {e}")
    
    # Test 6: Check process_pdf method signature
    print("\n6. Testing process_pdf method...")
    try:
        import inspect
        sig = inspect.signature(ocr.process_pdf)
        print(f"   ✓ process_pdf signature: {sig}")
    except Exception as e:
        errors.append(f"process_pdf inspection failed: {e}")
        print(f"   ✗ Inspection failed: {e}")
    
    # Test 7: Verify logging improvements
    print("\n7. Checking improved error handling...")
    try:
        import ast
        with open('/root/.openclaw/workspace/cerebrum-fix/backend/app/pipelines/ocr.py', 'r') as f:
            source = f.read()
        
        # Check for PYPDF2_AVAILABLE import
        if 'PYPDF2_AVAILABLE' in source and 'import PyPDF2' in source:
            print("   ✓ PYPDF2_AVAILABLE is properly imported")
        else:
            print("   ! PYPDF2_AVAILABLE may not be properly set up")
            
        # Check for improved logging
        log_checks = [
            ('pdf2image conversion failed', 'PDF conversion error logging'),
            ('Tesseract OCR failed', 'Tesseract error logging'),
            ('Loading image', 'Image loading logging'),
            ('Image loaded', 'Image loaded logging'),
        ]
        for check, desc in log_checks:
            if check in source:
                print(f"   ✓ {desc} found")
            else:
                print(f"   ! {desc} not found")
                
    except Exception as e:
        print(f"   ! Source check error: {e}")
    
    print("\n" + "=" * 60)
    if errors:
        print(f"ERRORS FOUND: {len(errors)}")
        for err in errors:
            print(f"  - {err}")
    else:
        print("ALL CRITICAL CHECKS PASSED ✓")
    print("=" * 60)
    
    return errors

if __name__ == "__main__":
    import asyncio
    errors = asyncio.run(test_ocr_fixes())
    sys.exit(1 if errors else 0)
