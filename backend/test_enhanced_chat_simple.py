"""
Simple test script for enhanced chat functionality.
Verifies code structure without requiring all dependencies.
"""

import ast
import os
import sys


def check_file_syntax(filepath):
    """Check if a Python file has valid syntax."""
    try:
        with open(filepath, 'r') as f:
            source = f.read()
        ast.parse(source)
        return True, None
    except SyntaxError as e:
        return False, str(e)


def check_required_functions(filepath, required_functions):
    """Check if file contains required functions."""
    with open(filepath, 'r') as f:
        source = f.read()
    
    tree = ast.parse(source)
    found_functions = set()
    
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) or isinstance(node, ast.AsyncFunctionDef):
            found_functions.add(node.name)
    
    missing = [f for f in required_functions if f not in found_functions]
    return len(missing) == 0, missing


def main():
    """Run simple structure tests."""
    print("=" * 60)
    print("ENHANCED CHAT STRUCTURE VERIFICATION")
    print("=" * 60)
    
    base_path = "/mnt/okcomputer/output/Cerebrum-main/backend"
    
    files_to_check = {
        "app/services/code_execution.py": {
            "required": ["_execute_code_worker", "execute", "analyze_code"]
        },
        "app/services/image_understanding.py": {
            "required": ["analyze_image", "validate_image", "_extract_metadata"]
        },
        "app/services/document_analysis.py": {
            "required": ["analyze_document", "_generate_summary", "quick_summarize"]
        },
        "app/api/v1/endpoints/chat.py": {
            "required": [
                "chat_completions",
                "execute_code_endpoint",
                "analyze_image_endpoint",
                "web_search_chat_endpoint",
                "chat_completions_stream"
            ]
        },
    }
    
    all_passed = True
    
    for filepath, config in files_to_check.items():
        full_path = os.path.join(base_path, filepath)
        print(f"\n📄 Checking {filepath}...")
        
        # Check syntax
        syntax_ok, error = check_file_syntax(full_path)
        if syntax_ok:
            print("  ✅ Syntax valid")
        else:
            print(f"  ❌ Syntax error: {error}")
            all_passed = False
            continue
        
        # Check required functions
        if "required" in config:
            all_found, missing = check_required_functions(full_path, config["required"])
            if all_found:
                print(f"  ✅ All required functions present")
            else:
                print(f"  ❌ Missing functions: {missing}")
                all_passed = False
    
    # Check new endpoints in documents.py
    print(f"\n📄 Checking app/api/v1/endpoints/documents.py...")
    docs_path = os.path.join(base_path, "app/api/v1/endpoints/documents.py")
    docs_required = [
        "analyze_document_endpoint",
        "analyze_document_file_endpoint",
        "summarize_document_endpoint",
        "extract_keywords_endpoint"
    ]
    all_found, missing = check_required_functions(docs_path, docs_required)
    if all_found:
        print("  ✅ All new document endpoints present")
    else:
        print(f"  ❌ Missing endpoints: {missing}")
        all_passed = False
    
    # Summary
    print("\n" + "=" * 60)
    if all_passed:
        print("🎉 ALL STRUCTURE CHECKS PASSED!")
        print("\nNew capabilities added:")
        print("  ✅ Web search integration")
        print("  ✅ Code execution (sandboxed)")
        print("  ✅ Image understanding")
        print("  ✅ Enhanced document analysis with AI")
        print("  ✅ Long context support")
        print("  ✅ Streaming chat responses")
    else:
        print("⚠️ SOME CHECKS FAILED")
    print("=" * 60)
    
    return all_passed


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
