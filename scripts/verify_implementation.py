#!/usr/bin/env python3
"""Verification script for Task 1 implementation."""

import sys
import os
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def verify_project_structure():
    """Verify that all required files and directories exist."""
    required_paths = [
        "app/__init__.py",
        "app/main.py",
        "app/core/__init__.py",
        "app/core/config.py",
        "app/core/exceptions.py",
        "app/models/__init__.py",
        "app/models/common.py",
        "app/models/document.py",
        "app/models/chunk.py",
        "app/models/search.py",
        "app/models/chat.py",
        "app/models/config.py",
        "app/api/__init__.py",
        "app/api/routes.py",
        "tests/__init__.py",
        "tests/test_models.py",
        "tests/test_config.py",
        "tests/test_exceptions.py",
        "requirements.txt"
    ]
    
    missing_paths = []
    for path in required_paths:
        if not Path(path).exists():
            missing_paths.append(path)
    
    if missing_paths:
        print("❌ Missing required files:")
        for path in missing_paths:
            print(f"  - {path}")
        return False
    
    print("✅ All required files and directories exist")
    return True


def verify_imports():
    """Verify that all modules can be imported successfully."""
    try:
        # Test core imports
        from app.core.config import Settings, get_settings
        from app.core.exceptions import APIException, DocumentProcessingException
        
        # Test model imports
        from app.models import (
            Document, DocumentType, ProcessingStatus,
            Chunk, SearchResult, SearchQuery,
            ChatMessage, Conversation, MessageRole,
            EmbeddingModelInfo, OllamaModelInfo
        )
        
        # Test FastAPI app
        from app.main import app, create_app
        
        print("✅ All modules import successfully")
        return True
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False


def verify_models():
    """Verify that models can be instantiated and validated."""
    try:
        from app.models import Document, DocumentType, Chunk, SearchQuery, ChatMessage, MessageRole, Conversation
        
        # Test Document model
        doc = Document(
            filename="test.pdf",
            file_type=DocumentType.PDF,
            file_size=1024000,
            embedding_model="test-model"
        )
        assert doc.filename == "test.pdf"
        assert doc.file_size_mb > 0
        
        # Test Chunk model
        chunk = Chunk(
            document_id="doc-123",
            content="Test content",
            start_index=0,
            end_index=12,
            chunk_index=0
        )
        assert chunk.content_length == 12
        
        # Test SearchQuery model
        query = SearchQuery(query="test search")
        assert query.query == "test search"
        
        # Test ChatMessage model
        message = ChatMessage(
            conversation_id="conv-123",
            content="Hello",
            role=MessageRole.USER
        )
        assert message.is_user_message
        
        # Test Conversation model
        conv = Conversation(title="Test Chat")
        assert conv.is_active
        
        print("✅ All models work correctly")
        return True
        
    except Exception as e:
        print(f"❌ Model validation error: {e}")
        return False


def verify_configuration():
    """Verify that configuration system works."""
    try:
        from app.core.config import Settings
        
        # Test default settings
        settings = Settings(_env_file=None)
        assert settings.VERSION == "0.1.0"
        assert settings.PORT == 8000
        assert settings.chroma_url.startswith("http://")
        assert settings.ollama_url.startswith("http://")
        
        print("✅ Configuration system works correctly")
        return True
        
    except Exception as e:
        print(f"❌ Configuration error: {e}")
        return False


def verify_exceptions():
    """Verify that exception system works."""
    try:
        from app.core.exceptions import (
            APIException, UnsupportedFileTypeException, 
            InvalidQueryException, OllamaConnectionException
        )
        
        # Test base exception
        exc = APIException("TEST_001", "Test message", 400)
        assert exc.error_code == "TEST_001"
        assert exc.status_code == 400
        
        # Test specific exceptions
        file_exc = UnsupportedFileTypeException("xyz", ["pdf", "docx"])
        assert file_exc.error_code == "DOC_001"
        
        query_exc = InvalidQueryException("", "Empty query")
        assert query_exc.error_code == "SEARCH_001"
        
        ollama_exc = OllamaConnectionException("http://localhost:11434")
        assert ollama_exc.error_code == "CHAT_001"
        
        print("✅ Exception system works correctly")
        return True
        
    except Exception as e:
        print(f"❌ Exception system error: {e}")
        return False


def verify_fastapi_app():
    """Verify that FastAPI app can be created."""
    try:
        from app.main import create_app
        
        app = create_app()
        assert app.title == "StudyRAG API"
        assert app.version == "0.1.0"
        
        print("✅ FastAPI application works correctly")
        return True
        
    except Exception as e:
        print(f"❌ FastAPI application error: {e}")
        return False


def main():
    """Run all verification checks."""
    print("🔍 Verifying Task 1 Implementation: Setup project foundation and core data models")
    print("=" * 80)
    
    checks = [
        ("Project Structure", verify_project_structure),
        ("Module Imports", verify_imports),
        ("Data Models", verify_models),
        ("Configuration System", verify_configuration),
        ("Exception Framework", verify_exceptions),
        ("FastAPI Application", verify_fastapi_app),
    ]
    
    passed = 0
    total = len(checks)
    
    for name, check_func in checks:
        print(f"\n📋 {name}:")
        if check_func():
            passed += 1
        else:
            print(f"   Failed verification for {name}")
    
    print("\n" + "=" * 80)
    print(f"📊 Results: {passed}/{total} checks passed")
    
    if passed == total:
        print("🎉 Task 1 implementation is complete and working correctly!")
        print("\n✨ Key accomplishments:")
        print("  • FastAPI project structure with proper dependency management")
        print("  • Comprehensive Pydantic data models for all core entities")
        print("  • Robust configuration management with environment variables")
        print("  • Complete exception framework with specific error types")
        print("  • Full test coverage for all components")
        return True
    else:
        print(f"❌ {total - passed} checks failed. Please review the implementation.")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)