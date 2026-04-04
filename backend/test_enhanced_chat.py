"""
Test script for enhanced chat functionality.
Tests web search, code execution, and image understanding capabilities.
"""

import asyncio
import sys
import os

# Add the backend directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


async def test_code_execution():
    """Test code execution service."""
    print("\n=== Testing Code Execution Service ===")
    
    try:
        from app.services.code_execution import get_code_execution_service
        
        service = get_code_execution_service()
        
        # Test simple calculation
        code = """
result = 42 * 23
print(f"The answer is: {result}")
"""
        result = await service.execute(code)
        
        print(f"Success: {result.success}")
        print(f"Output: {result.output}")
        print(f"Execution time: {result.execution_time_ms:.0f}ms")
        
        # Test code analysis
        analysis = service.analyze_code(code)
        print(f"Analysis - Safe: {analysis['safe']}")
        print(f"Analysis - Line count: {analysis['line_count']}")
        
        return result.success
        
    except Exception as e:
        print(f"Code execution test failed: {e}")
        return False


async def test_image_understanding():
    """Test image understanding service."""
    print("\n=== Testing Image Understanding Service ===")
    
    try:
        from app.services.image_understanding import get_image_understanding_service
        
        service = get_image_understanding_service()
        
        # Test validation with invalid data
        is_valid, error = service.validate_image(b"invalid data")
        print(f"Validation test - Valid: {is_valid}, Error: {error}")
        
        # Test metadata extraction would require a real image
        print("Image understanding service initialized successfully")
        
        return True
        
    except Exception as e:
        print(f"Image understanding test failed: {e}")
        return False


async def test_document_analysis():
    """Test document analysis service."""
    print("\n=== Testing Document Analysis Service ===")
    
    try:
        from app.services.document_analysis import get_document_analysis_service
        
        service = get_document_analysis_service()
        
        # Test document analysis
        sample_text = """
        Construction Project Update
        
        The project is progressing well with concrete work completed ahead of schedule.
        The steel framework installation will begin next week. Budget remains on track
        with a 5% contingency remaining. Safety incidents have been minimal with zero
        lost-time accidents this month.
        
        Key milestones:
        - Foundation completed: March 15
        - Steel delivery: April 1
        - Expected completion: December 30
        
        The team is working efficiently and quality metrics exceed expectations.
        """
        
        result = await service.analyze_document(sample_text, analysis_depth="basic")
        
        print(f"Analysis success: {result.success}")
        if result.success and result.summary:
            print(f"Summary overview: {result.summary.overview[:100]}...")
            print(f"Key points: {len(result.summary.key_points)}")
            print(f"Topics: {result.summary.topics}")
        
        # Test quick summarize
        quick_summary = await service.quick_summarize(sample_text)
        print(f"Quick summary: {quick_summary[:100]}...")
        
        return result.success
        
    except Exception as e:
        print(f"Document analysis test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_web_search():
    """Test web search functionality."""
    print("\n=== Testing Web Search Service ===")
    
    try:
        from app.agent.web_search import get_web_search_tool
        
        tool = get_web_search_tool()
        print(f"Web search tool initialized")
        print(f"Web search enabled: {tool.enabled}")
        print(f"API key configured: {bool(tool.api_key)}")
        
        return True
        
    except Exception as e:
        print(f"Web search test failed: {e}")
        return False


def test_chat_endpoints():
    """Test chat endpoint imports."""
    print("\n=== Testing Chat Endpoint Imports ===")
    
    try:
        from app.api.v1.endpoints.chat import (
            chat_completions,
            execute_code_endpoint,
            analyze_image_endpoint,
            web_search_chat_endpoint,
            ChatCompletionRequest,
            CodeExecutionRequest,
        )
        
        print("Chat endpoints imported successfully")
        print(f"- chat_completions: {chat_completions}")
        print(f"- execute_code_endpoint: {execute_code_endpoint}")
        print(f"- analyze_image_endpoint: {analyze_image_endpoint}")
        print(f"- web_search_chat_endpoint: {web_search_chat_endpoint}")
        
        return True
        
    except Exception as e:
        print(f"Chat endpoint import failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_document_endpoints():
    """Test document endpoint imports."""
    print("\n=== Testing Document Endpoint Imports ===")
    
    try:
        from app.api.v1.endpoints.documents import (
            analyze_document_endpoint,
            analyze_document_file_endpoint,
            summarize_document_endpoint,
            extract_keywords_endpoint,
        )
        
        print("Document endpoints imported successfully")
        print(f"- analyze_document_endpoint: {analyze_document_endpoint}")
        print(f"- analyze_document_file_endpoint: {analyze_document_file_endpoint}")
        print(f"- summarize_document_endpoint: {summarize_document_endpoint}")
        print(f"- extract_keywords_endpoint: {extract_keywords_endpoint}")
        
        return True
        
    except Exception as e:
        print(f"Document endpoint import failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def run_all_tests():
    """Run all tests."""
    print("=" * 60)
    print("ENHANCED CHAT FUNCTIONALITY TESTS")
    print("=" * 60)
    
    results = {
        "code_execution": await test_code_execution(),
        "image_understanding": await test_image_understanding(),
        "document_analysis": await test_document_analysis(),
        "web_search": await test_web_search(),
        "chat_endpoints": test_chat_endpoints(),
        "document_endpoints": test_document_endpoints(),
    }
    
    print("\n" + "=" * 60)
    print("TEST RESULTS SUMMARY")
    print("=" * 60)
    
    for test_name, passed in results.items():
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"{test_name}: {status}")
    
    all_passed = all(results.values())
    print("\n" + "=" * 60)
    if all_passed:
        print("🎉 ALL TESTS PASSED!")
    else:
        print("⚠️ SOME TESTS FAILED")
    print("=" * 60)
    
    return all_passed


if __name__ == "__main__":
    # Run tests
    result = asyncio.run(run_all_tests())
    sys.exit(0 if result else 1)
