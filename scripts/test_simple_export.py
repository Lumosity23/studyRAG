"""Simple test to debug the export endpoint."""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from fastapi.testclient import TestClient
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.main import app

def test_simple_export():
    """Simple test to check if mocking works."""
    client = TestClient(app)
    
    # Create mock
    mock_vector_db = Mock()
    mock_vector_db.export_database = AsyncMock(return_value={
        "documents": [
            {
                "id": "doc1",
                "filename": "test.pdf",
                "chunks": [
                    {
                        "id": "chunk1",
                        "content": "Test content"
                    }
                ]
            }
        ]
    })
    mock_vector_db.get_database_stats = AsyncMock(return_value={
        "total_documents": 1,
        "total_chunks": 1,
        "total_size_mb": 1.0
    })
    
    # Patch the VectorDatabase class as imported in database.py
    with patch('app.api.endpoints.database.VectorDatabase', return_value=mock_vector_db):
        response = client.get("/api/v1/database/export?format=json&compress=false")
        
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"Documents count: {len(data.get('documents', []))}")
            print(f"Export info: {data.get('export_info', {})}")
        else:
            print(f"Error: {response.content}")

if __name__ == "__main__":
    test_simple_export()