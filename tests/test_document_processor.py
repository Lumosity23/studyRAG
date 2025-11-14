"""
Tests for document processing service.

Tests cover:
1. File validation and type detection
2. Content extraction for different formats
3. Chunking strategies (simple and hybrid)
4. Error handling for unsupported formats
5. Metadata preservation and enhancement
6. Integration with Docling
"""

import os
import pytest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock
from typing import Dict, Any

from app.services.document_processor import DocumentProcessor
from app.models.document import Document, DocumentType, ProcessingStatus
from app.models.chunk import Chunk
from app.core.exceptions import DocumentProcessingError, ValidationError


class TestDocumentProcessor:
    """Test suite for DocumentProcessor."""
    
    @pytest.fixture
    def processor(self):
        """Create DocumentProcessor instance for testing."""
        return DocumentProcessor()
    
    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for test files."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)
    
    @pytest.fixture
    def sample_text_file(self, temp_dir):
        """Create sample text file for testing."""
        content = """# Test Document

This is a test document for validating text processing.

## Section 1
This section contains some sample text with multiple paragraphs.

The second paragraph has more content to test chunking strategies.

## Section 2
Another section with different content to ensure proper processing.

This document should be split into multiple chunks based on the configured chunk size.
"""
        file_path = os.path.join(temp_dir, "test_document.txt")
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        return file_path
    
    @pytest.fixture
    def sample_html_file(self, temp_dir):
        """Create sample HTML file for testing."""
        content = """<!DOCTYPE html>
<html>
<head>
    <title>Test HTML Document</title>
</head>
<body>
    <h1>Main Title</h1>
    <p>This is a test HTML document for validation.</p>
    
    <h2>Section 1</h2>
    <p>First section content with <strong>formatting</strong>.</p>
    
    <h2>Section 2</h2>
    <p>Second section with <em>different</em> content.</p>
    
    <table>
        <tr><th>Column 1</th><th>Column 2</th></tr>
        <tr><td>Data 1</td><td>Data 2</td></tr>
    </table>
</body>
</html>"""
        file_path = os.path.join(temp_dir, "test_document.html")
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        return file_path
    
    @pytest.fixture
    def large_file(self, temp_dir):
        """Create large file for size validation testing."""
        content = "Large file content. " * 1000000  # ~20MB
        file_path = os.path.join(temp_dir, "large_file.txt")
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        return file_path
    
    @pytest.fixture
    def empty_file(self, temp_dir):
        """Create empty file for validation testing."""
        file_path = os.path.join(temp_dir, "empty_file.txt")
        with open(file_path, 'w', encoding='utf-8') as f:
            pass  # Create empty file
        return file_path

    # File Validation Tests
    
    def test_detect_file_type_txt(self, processor):
        """Test file type detection for text files."""
        doc_type, is_audio = processor._detect_file_type("/path/file.txt", "file.txt")
        assert doc_type == DocumentType.TXT
        assert is_audio is False
    
    def test_detect_file_type_pdf(self, processor):
        """Test file type detection for PDF files."""
        doc_type, is_audio = processor._detect_file_type("/path/file.pdf", "file.pdf")
        assert doc_type == DocumentType.PDF
        assert is_audio is False
    
    def test_detect_file_type_docx(self, processor):
        """Test file type detection for DOCX files."""
        doc_type, is_audio = processor._detect_file_type("/path/file.docx", "file.docx")
        assert doc_type == DocumentType.DOCX
        assert is_audio is False
    
    def test_detect_file_type_html(self, processor):
        """Test file type detection for HTML files."""
        doc_type, is_audio = processor._detect_file_type("/path/file.html", "file.html")
        assert doc_type == DocumentType.HTML
        assert is_audio is False
    
    def test_detect_file_type_audio(self, processor):
        """Test file type detection for audio files."""
        doc_type, is_audio = processor._detect_file_type("/path/file.mp3", "file.mp3")
        assert doc_type == DocumentType.TXT  # Audio transcribed to text
        assert is_audio is True
    
    def test_detect_file_type_unsupported(self, processor):
        """Test file type detection for unsupported files."""
        with pytest.raises(ValidationError, match="Unsupported file type"):
            processor._detect_file_type("/path/file.xyz", "file.xyz")
    
    @pytest.mark.asyncio
    async def test_validate_file_success(self, processor, sample_text_file):
        """Test successful file validation."""
        file_info = await processor._validate_file(sample_text_file, "test_document.txt")
        
        assert file_info['type'] == DocumentType.TXT
        assert file_info['size'] > 0
        assert file_info['is_audio'] is False
        assert 'mime_type' in file_info
    
    @pytest.mark.asyncio
    async def test_validate_file_not_found(self, processor):
        """Test validation of non-existent file."""
        with pytest.raises(ValidationError, match="File not found"):
            await processor._validate_file("/nonexistent/file.txt", "file.txt")
    
    @pytest.mark.asyncio
    async def test_validate_file_empty(self, processor, empty_file):
        """Test validation of empty file."""
        with pytest.raises(ValidationError, match="File is empty"):
            await processor._validate_file(empty_file, "empty_file.txt")
    
    @pytest.mark.asyncio
    async def test_validate_file_too_large(self, processor, large_file):
        """Test validation of file that's too large."""
        with pytest.raises(ValidationError, match="File too large"):
            await processor._validate_file(large_file, "large_file.txt")

    # Content Extraction Tests
    
    @pytest.mark.asyncio
    async def test_extract_text_content(self, processor, sample_text_file):
        """Test text content extraction."""
        file_info = {'type': DocumentType.TXT, 'is_audio': False}
        result = await processor._extract_text_content(sample_text_file)
        
        assert 'content' in result
        assert 'preview' in result
        assert result['method'] == 'direct_text'
        assert result['word_count'] > 0
        assert result['language'] in ['en', 'fr', 'es', 'unknown']
        assert result['docling_doc'] is None
    
    @pytest.mark.asyncio
    @patch('app.services.document_processor.DocumentConverter')
    async def test_extract_docling_content(self, mock_converter_class, processor, sample_html_file):
        """Test Docling content extraction."""
        # Mock Docling converter
        mock_converter = Mock()
        mock_result = Mock()
        mock_doc = Mock()
        
        mock_doc.export_to_markdown.return_value = "# Test\nContent from Docling"
        mock_result.document = mock_doc
        mock_converter.convert.return_value = mock_result
        mock_converter_class.return_value = mock_converter
        
        # Mock processor converter property
        processor._converter = mock_converter
        
        result = await processor._extract_docling_content(sample_html_file, DocumentType.HTML)
        
        assert result['content'] == "# Test\nContent from Docling"
        assert result['method'] == 'docling'
        assert result['docling_doc'] == mock_doc
        assert 'word_count' in result
    
    @pytest.mark.asyncio
    @patch('app.services.document_processor.DocumentConverter')
    async def test_extract_audio_content(self, mock_converter_class, processor, temp_dir):
        """Test audio content extraction."""
        # Create mock audio file
        audio_file = os.path.join(temp_dir, "test_audio.mp3")
        with open(audio_file, 'wb') as f:
            f.write(b"fake audio data")
        
        # Mock audio converter
        mock_converter = Mock()
        mock_result = Mock()
        mock_doc = Mock()
        
        mock_doc.export_to_markdown.return_value = "Transcribed audio content"
        mock_result.document = mock_doc
        mock_converter.convert.return_value = mock_result
        
        # Mock processor audio converter property
        processor._audio_converter = mock_converter
        
        result = await processor._extract_audio_content(audio_file)
        
        assert result['content'] == "Transcribed audio content"
        assert result['method'] == 'docling_asr'
        assert result['language'] == 'auto-detected'
        assert result['docling_doc'] == mock_doc

    # Chunking Tests
    
    @pytest.mark.asyncio
    async def test_create_simple_chunks(self, processor):
        """Test simple chunking strategy."""
        content = """# Test Document

This is the first paragraph with some content.

This is the second paragraph with more content to test chunking.

## Section 1

This is content in section 1 with multiple sentences. It should be long enough to create multiple chunks when the chunk size is small.

## Section 2

This is content in section 2 with different text to ensure proper chunk boundaries."""
        
        # Create mock document
        document = Document(
            filename="test.txt",
            file_type=DocumentType.TXT,
            file_size=len(content),
            processing_status=ProcessingStatus.PROCESSING
        )
        
        # Override chunk size for testing
        original_chunk_size = processor.settings.CHUNK_SIZE
        processor.settings.CHUNK_SIZE = 200  # Small size to force multiple chunks
        
        try:
            chunks = await processor._create_simple_chunks(content, document)
            
            assert len(chunks) > 1  # Should create multiple chunks
            
            for i, chunk in enumerate(chunks):
                assert isinstance(chunk, Chunk)
                assert chunk.document_id == document.id
                assert chunk.chunk_index == i
                assert chunk.content.strip()  # Non-empty content
                assert chunk.start_index >= 0
                assert chunk.end_index > chunk.start_index
                assert chunk.token_count > 0
                assert chunk.metadata['chunking_method'] == 'simple'
                assert chunk.metadata['total_chunks'] == len(chunks)
        
        finally:
            processor.settings.CHUNK_SIZE = original_chunk_size
    
    @pytest.mark.asyncio
    async def test_create_hybrid_chunks(self, processor):
        """Test hybrid chunking strategy with Docling."""
        content = "Test content for hybrid chunking"
        
        # Create mock document
        document = Document(
            filename="test.txt",
            file_type=DocumentType.TXT,
            file_size=len(content),
            processing_status=ProcessingStatus.PROCESSING
        )
        
        # Mock Docling document
        mock_docling_doc = Mock()
        
        # Mock the imports within the method using the actual module paths
        with patch('docling.chunking.HybridChunker') as mock_chunker_class, \
             patch('transformers.AutoTokenizer') as mock_tokenizer_class:
            
            # Mock tokenizer
            mock_tokenizer = Mock()
            mock_tokenizer.encode.return_value = [1, 2, 3, 4, 5]  # 5 tokens
            mock_tokenizer_class.from_pretrained.return_value = mock_tokenizer
            
            # Mock chunker
            mock_chunker = Mock()
            mock_chunk = Mock()
            mock_chunker.chunk.return_value = [mock_chunk]
            mock_chunker.contextualize.return_value = "Contextualized chunk content"
            mock_chunker_class.return_value = mock_chunker
            
            chunks = await processor._create_hybrid_chunks(content, document, mock_docling_doc)
        
            assert len(chunks) == 1
            chunk = chunks[0]
            assert chunk.content == "Contextualized chunk content"
            assert chunk.token_count == 5
            assert chunk.metadata['chunking_method'] == 'hybrid'
            assert chunk.metadata['has_context'] is True
    
    def test_extract_section_title(self, processor):
        """Test section title extraction from content."""
        # Test with markdown heading
        content_with_heading = "# Main Title\nSome content here"
        title = processor._extract_section_title(content_with_heading)
        assert title == "Main Title"
        
        # Test with multiple heading levels
        content_with_h2 = "## Section Title\nContent here"
        title = processor._extract_section_title(content_with_h2)
        assert title == "Section Title"
        
        # Test without heading
        content_no_heading = "Just regular content without headings"
        title = processor._extract_section_title(content_no_heading)
        assert title is None
    
    def test_detect_language(self, processor):
        """Test language detection."""
        # English text
        english_text = "The quick brown fox jumps over the lazy dog and runs to the house"
        lang = processor._detect_language(english_text)
        assert lang == 'en'
        
        # French text
        french_text = "Le chat est sur le tapis et il mange de la nourriture"
        lang = processor._detect_language(french_text)
        assert lang == 'fr'
        
        # Unknown language (short text with no common words)
        unknown_text = "xyz abc def"
        lang = processor._detect_language(unknown_text)
        assert lang == 'unknown'

    # Integration Tests
    
    @pytest.mark.asyncio
    @patch('app.services.document_processor.DocumentConverter')
    async def test_process_document_success(self, mock_converter_class, processor, sample_text_file):
        """Test complete document processing pipeline."""
        # Mock Docling converter (not used for text files, but needed for initialization)
        mock_converter = Mock()
        mock_converter_class.return_value = mock_converter
        
        result = await processor.process_document(
            file_path=sample_text_file,
            filename="test_document.txt",
            metadata={"test": "metadata"}
        )
        
        assert isinstance(result, Document)
        assert result.filename == "test_document.txt"
        assert result.file_type == DocumentType.TXT
        assert result.processing_status == ProcessingStatus.COMPLETED
        assert result.chunk_count > 0
        assert result.content_preview is not None
        assert result.word_count > 0
        assert "test" in result.metadata
        assert "processing_time_seconds" in result.metadata
    
    @pytest.mark.asyncio
    async def test_process_document_validation_error(self, processor):
        """Test document processing with validation error."""
        with pytest.raises(ValidationError):
            await processor.process_document(
                file_path="/nonexistent/file.txt",
                filename="nonexistent.txt"
            )
    
    @pytest.mark.asyncio
    @patch('app.services.document_processor.DocumentConverter')
    async def test_process_document_extraction_error(self, mock_converter_class, processor, sample_text_file):
        """Test document processing with extraction error."""
        # Mock converter to raise exception
        mock_converter = Mock()
        mock_converter.convert.side_effect = Exception("Extraction failed")
        mock_converter_class.return_value = mock_converter
        
        # This should still succeed because text files don't use Docling
        result = await processor.process_document(
            file_path=sample_text_file,
            filename="test_document.txt"
        )
        
        assert result.processing_status == ProcessingStatus.COMPLETED

    # Utility Tests
    
    def test_get_supported_extensions(self, processor):
        """Test getting supported file extensions."""
        extensions = processor.get_supported_extensions()
        
        assert '.txt' in extensions
        assert '.pdf' in extensions
        assert '.docx' in extensions
        assert '.html' in extensions
        assert '.mp3' in extensions
        assert '.wav' in extensions
        assert len(extensions) > 5
    
    def test_calculate_file_hash(self, processor, sample_text_file):
        """Test file hash calculation."""
        hash1 = processor.calculate_file_hash(sample_text_file)
        hash2 = processor.calculate_file_hash(sample_text_file)
        
        assert hash1 == hash2  # Same file should have same hash
        assert len(hash1) == 64  # SHA-256 hash length
        assert all(c in '0123456789abcdef' for c in hash1)  # Valid hex
    
    @pytest.mark.asyncio
    async def test_cleanup_temp_files(self, processor, temp_dir):
        """Test temporary file cleanup."""
        # Create temporary file
        temp_file = os.path.join(temp_dir, "temp_file.txt")
        with open(temp_file, 'w') as f:
            f.write("temporary content")
        
        assert os.path.exists(temp_file)
        
        await processor.cleanup_temp_files(temp_file)
        
        assert not os.path.exists(temp_file)

    # Error Handling Tests
    
    @pytest.mark.asyncio
    async def test_extract_content_with_docling_error(self, processor, sample_html_file):
        """Test content extraction when Docling fails."""
        # Mock Docling to raise exception by setting the private attribute
        original_converter = processor._converter
        mock_converter = Mock()
        mock_converter.convert.side_effect = Exception("Docling failed")
        processor._converter = mock_converter
        
        try:
            file_info = {'type': DocumentType.HTML, 'is_audio': False}
            
            with pytest.raises(DocumentProcessingError, match="Content extraction failed"):
                await processor._extract_content(sample_html_file, file_info)
        finally:
            processor._converter = original_converter
    
    def test_extract_docling_metadata_error_handling(self, processor):
        """Test Docling metadata extraction with errors."""
        # Mock document that raises exceptions
        mock_doc = Mock()
        mock_doc.export_to_markdown.side_effect = Exception("Export failed")
        
        # Should not raise exception, just return empty metadata
        metadata = processor._extract_docling_metadata(mock_doc, DocumentType.PDF)
        
        assert isinstance(metadata, dict)
        # Should have some basic structure even with errors
    
    @pytest.mark.asyncio
    async def test_create_chunks_empty_content(self, processor):
        """Test chunk creation with empty content."""
        document = Document(
            filename="empty.txt",
            file_type=DocumentType.TXT,
            file_size=0,
            processing_status=ProcessingStatus.PROCESSING
        )
        
        chunks = await processor._create_chunks("", document, None)
        assert chunks == []
        
        chunks = await processor._create_chunks("   \n\n  ", document, None)
        assert chunks == []

    # Performance Tests
    
    @pytest.mark.asyncio
    async def test_large_document_chunking(self, processor):
        """Test chunking of large documents."""
        # Create large content with paragraph breaks to force chunking
        large_content = ("This is a test paragraph with enough content to exceed chunk size limits.\n\n" * 100)  # ~7KB with breaks
        
        document = Document(
            filename="large.txt",
            file_type=DocumentType.TXT,
            file_size=len(large_content),
            processing_status=ProcessingStatus.PROCESSING
        )
        
        # Temporarily reduce chunk size to force multiple chunks
        original_chunk_size = processor.settings.CHUNK_SIZE
        processor.settings.CHUNK_SIZE = 500  # Small size to force multiple chunks
        
        try:
            chunks = await processor._create_simple_chunks(large_content, document)
            assert len(chunks) > 1
        finally:
            processor.settings.CHUNK_SIZE = original_chunk_size
        
        # Verify chunk sizes are reasonable
        for chunk in chunks:
            assert len(chunk.content) <= processor.settings.CHUNK_SIZE * 1.5  # Allow some flexibility
            assert chunk.token_count > 0
    
    @pytest.mark.asyncio
    async def test_concurrent_processing(self, processor, sample_text_file):
        """Test concurrent document processing."""
        import asyncio
        
        # Process same file multiple times concurrently
        tasks = []
        for i in range(3):
            task = processor.process_document(
                file_path=sample_text_file,
                filename=f"test_document_{i}.txt"
            )
            tasks.append(task)
        
        results = await asyncio.gather(*tasks)
        
        assert len(results) == 3
        for result in results:
            assert result.processing_status == ProcessingStatus.COMPLETED
            assert result.chunk_count > 0


# Fixtures for integration testing

@pytest.fixture
def mock_settings():
    """Mock settings for testing."""
    from unittest.mock import Mock
    
    settings = Mock()
    settings.UPLOAD_DIR = "/tmp/uploads"
    settings.PROCESSED_DIR = "/tmp/processed"
    settings.MAX_FILE_SIZE = 50 * 1024 * 1024
    settings.CHUNK_SIZE = 1000
    settings.CHUNK_OVERLAP = 200
    settings.EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
    settings.MAX_CONTEXT_TOKENS = 4000
    
    return settings


@pytest.fixture
def processor_with_mock_settings(mock_settings):
    """Create processor with mocked settings."""
    with patch('app.services.document_processor.get_settings', return_value=mock_settings):
        processor = DocumentProcessor()
        return processor


class TestDocumentProcessorIntegration:
    """Integration tests for DocumentProcessor with real files."""
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_real_text_file_processing(self, processor_with_mock_settings, tmp_path):
        """Test processing a real text file."""
        # Create a real markdown file
        content = """# Integration Test Document

This is a real test document for integration testing.

## Introduction

This document contains multiple sections and paragraphs to test the complete processing pipeline.

## Features

- Document validation
- Content extraction
- Intelligent chunking
- Metadata preservation

## Conclusion

The document processor should handle this file correctly and create appropriate chunks.
"""
        
        file_path = tmp_path / "integration_test.md"
        file_path.write_text(content, encoding='utf-8')
        
        result = await processor_with_mock_settings.process_document(
            file_path=str(file_path),
            filename="integration_test.md",
            metadata={"test_type": "integration"}
        )
        
        assert result.processing_status == ProcessingStatus.COMPLETED
        assert result.file_type == DocumentType.TXT
        assert result.chunk_count > 0
        assert result.word_count > 0
        assert result.content_preview is not None
        assert "test_type" in result.metadata
        assert "processing_time_seconds" in result.metadata