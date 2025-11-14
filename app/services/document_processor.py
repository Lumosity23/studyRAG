"""
Document processing service with Docling integration.

This service handles the complete document processing pipeline:
1. File validation and type detection
2. Content extraction using Docling for various formats
3. Intelligent text chunking with overlap and size optimization
4. Metadata preservation and enhancement
5. Error handling for unsupported formats and processing failures

Supports: PDF, DOCX, HTML, TXT, and audio files (MP3, WAV, M4A, FLAC)
"""

import os
import logging
import asyncio
import mimetypes
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple, Union
from datetime import datetime
import hashlib
import json

from docling.document_converter import DocumentConverter, AudioFormatOption
from docling.datamodel.pipeline_options import AsrPipelineOptions
from docling.datamodel import asr_model_specs
from docling.datamodel.base_models import InputFormat
from docling.pipeline.asr_pipeline import AsrPipeline
from docling_core.types.doc import DoclingDocument

from ..models.document import Document, DocumentType, ProcessingStatus
from ..models.chunk import Chunk
from ..core.config import get_settings
from ..core.exceptions import DocumentProcessingError, ValidationError

logger = logging.getLogger(__name__)


class DocumentProcessor:
    """
    Document processing service with Docling integration.
    
    Handles extraction, chunking, and metadata preservation for various document formats.
    """
    
    # Supported file types and their MIME types
    SUPPORTED_TYPES = {
        DocumentType.PDF: ['application/pdf'],
        DocumentType.DOCX: [
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            'application/msword'
        ],
        DocumentType.HTML: ['text/html', 'application/xhtml+xml'],
        DocumentType.TXT: ['text/plain', 'text/markdown']
    }
    
    # Audio formats supported by Docling ASR
    AUDIO_EXTENSIONS = {'.mp3', '.wav', '.m4a', '.flac', '.ogg'}
    
    # Maximum file sizes (in bytes)
    MAX_FILE_SIZES = {
        DocumentType.PDF: 50 * 1024 * 1024,  # 50MB
        DocumentType.DOCX: 25 * 1024 * 1024,  # 25MB
        DocumentType.HTML: 10 * 1024 * 1024,  # 10MB
        DocumentType.TXT: 5 * 1024 * 1024,    # 5MB
        'audio': 100 * 1024 * 1024,           # 100MB for audio
    }
    
    def __init__(self):
        """Initialize the document processor."""
        self.settings = get_settings()
        self._converter = None
        self._audio_converter = None
        
        # Ensure upload directories exist
        os.makedirs(self.settings.UPLOAD_DIR, exist_ok=True)
        os.makedirs(self.settings.PROCESSED_DIR, exist_ok=True)
    
    @property
    def converter(self) -> DocumentConverter:
        """Get or create Docling document converter."""
        if self._converter is None:
            self._converter = DocumentConverter()
            logger.info("Initialized Docling DocumentConverter")
        return self._converter
    
    @property
    def audio_converter(self) -> DocumentConverter:
        """Get or create Docling audio converter with ASR pipeline."""
        if self._audio_converter is None:
            # Configure ASR pipeline with Whisper Turbo model
            pipeline_options = AsrPipelineOptions()
            pipeline_options.asr_options = asr_model_specs.WHISPER_TURBO
            
            self._audio_converter = DocumentConverter(
                format_options={
                    InputFormat.AUDIO: AudioFormatOption(
                        pipeline_cls=AsrPipeline,
                        pipeline_options=pipeline_options,
                    )
                }
            )
            logger.info("Initialized Docling AudioConverter with Whisper ASR")
        return self._audio_converter
    
    async def process_document(
        self,
        file_path: str,
        filename: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Document:
        """
        Process a document through the complete pipeline.
        
        Args:
            file_path: Path to the uploaded file
            filename: Original filename
            metadata: Additional metadata
            
        Returns:
            Document model with processing results
            
        Raises:
            DocumentProcessingError: If processing fails
            ValidationError: If file validation fails
        """
        start_time = datetime.now()
        
        try:
            # Validate file
            file_info = await self._validate_file(file_path, filename)
            
            # Create document record
            document = Document(
                filename=filename,
                file_type=file_info['type'],
                file_size=file_info['size'],
                file_path=file_path,
                processing_status=ProcessingStatus.PROCESSING,
                metadata=metadata or {}
            )
            
            logger.info(f"Starting processing for {filename} ({file_info['type']})")
            
            # Extract content
            extraction_result = await self._extract_content(file_path, file_info)
            
            # Update document with extraction results
            document.content_preview = extraction_result['preview']
            document.language = extraction_result.get('language')
            document.page_count = extraction_result.get('page_count')
            document.word_count = extraction_result.get('word_count')
            
            # Create chunks
            chunks = await self._create_chunks(
                content=extraction_result['content'],
                document=document,
                docling_doc=extraction_result.get('docling_doc')
            )
            
            # Update document status
            document.chunk_count = len(chunks)
            document.processing_status = ProcessingStatus.COMPLETED
            document.embedding_model = self.settings.EMBEDDING_MODEL
            
            # Calculate processing time
            processing_time = (datetime.now() - start_time).total_seconds()
            document.metadata.update({
                'processing_time_seconds': processing_time,
                'chunks_created': len(chunks),
                'extraction_method': extraction_result.get('method', 'unknown')
            })
            
            logger.info(
                f"Successfully processed {filename}: "
                f"{len(chunks)} chunks in {processing_time:.2f}s"
            )
            
            return document
            
        except ValidationError:
            # Re-raise validation errors as-is
            raise
        except Exception as e:
            # Update document with error status
            if 'document' in locals():
                document.processing_status = ProcessingStatus.FAILED
                document.processing_error = str(e)
            
            logger.error(f"Failed to process {filename}: {e}")
            raise DocumentProcessingError(f"Document processing failed: {e}") from e
    
    async def _validate_file(self, file_path: str, filename: str) -> Dict[str, Any]:
        """
        Validate file type, size, and accessibility.
        
        Args:
            file_path: Path to the file
            filename: Original filename
            
        Returns:
            Dictionary with file information
            
        Raises:
            ValidationError: If validation fails
        """
        if not os.path.exists(file_path):
            raise ValidationError(f"File not found: {file_path}")
        
        if not os.path.isfile(file_path):
            raise ValidationError(f"Path is not a file: {file_path}")
        
        # Get file size
        file_size = os.path.getsize(file_path)
        if file_size == 0:
            raise ValidationError("File is empty")
        
        # Detect file type
        file_type, is_audio = self._detect_file_type(file_path, filename)
        
        # Check file size limits
        if is_audio:
            max_size = self.MAX_FILE_SIZES['audio']
        else:
            max_size = self.MAX_FILE_SIZES.get(file_type, self.settings.MAX_FILE_SIZE)
        
        if file_size > max_size:
            raise ValidationError(
                f"File too large: {file_size / (1024*1024):.1f}MB "
                f"(max: {max_size / (1024*1024):.1f}MB)"
            )
        
        # Check file accessibility
        try:
            with open(file_path, 'rb') as f:
                f.read(1024)  # Try to read first 1KB
        except PermissionError:
            raise ValidationError("File is not readable (permission denied)")
        except Exception as e:
            raise ValidationError(f"File is not accessible: {e}")
        
        return {
            'type': file_type,
            'size': file_size,
            'is_audio': is_audio,
            'mime_type': mimetypes.guess_type(filename)[0]
        }
    
    def _detect_file_type(self, file_path: str, filename: str) -> Tuple[DocumentType, bool]:
        """
        Detect file type from extension and content.
        
        Args:
            file_path: Path to the file
            filename: Original filename
            
        Returns:
            Tuple of (DocumentType, is_audio)
            
        Raises:
            ValidationError: If file type is not supported
        """
        # Get file extension
        ext = Path(filename).suffix.lower()
        
        # Check for audio files
        if ext in self.AUDIO_EXTENSIONS:
            return DocumentType.TXT, True  # Audio transcribed to text
        
        # Map extensions to document types
        extension_map = {
            '.pdf': DocumentType.PDF,
            '.docx': DocumentType.DOCX,
            '.doc': DocumentType.DOCX,
            '.html': DocumentType.HTML,
            '.htm': DocumentType.HTML,
            '.txt': DocumentType.TXT,
            '.md': DocumentType.TXT,
            '.markdown': DocumentType.TXT,
        }
        
        if ext not in extension_map:
            raise ValidationError(f"Unsupported file type: {ext}")
        
        return extension_map[ext], False
    
    async def _extract_content(
        self,
        file_path: str,
        file_info: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Extract content from file using appropriate method.
        
        Args:
            file_path: Path to the file
            file_info: File information from validation
            
        Returns:
            Dictionary with extracted content and metadata
            
        Raises:
            DocumentProcessingError: If extraction fails
        """
        try:
            if file_info['is_audio']:
                return await self._extract_audio_content(file_path)
            elif file_info['type'] == DocumentType.TXT:
                return await self._extract_text_content(file_path)
            else:
                return await self._extract_docling_content(file_path, file_info['type'])
                
        except Exception as e:
            raise DocumentProcessingError(f"Content extraction failed: {e}") from e
    
    async def _extract_audio_content(self, file_path: str) -> Dict[str, Any]:
        """Extract content from audio file using Docling ASR."""
        logger.info(f"Transcribing audio file: {os.path.basename(file_path)}")
        
        try:
            # Convert to Path object for Docling
            audio_path = Path(file_path).resolve()
            
            # Transcribe using Docling ASR
            result = self.audio_converter.convert(audio_path)
            
            # Export to markdown
            content = result.document.export_to_markdown()
            
            # Extract metadata
            word_count = len(content.split())
            
            return {
                'content': content,
                'preview': content[:497] + '...' if len(content) > 497 else content,
                'method': 'docling_asr',
                'word_count': word_count,
                'language': 'auto-detected',  # Whisper auto-detects language
                'docling_doc': result.document
            }
            
        except Exception as e:
            logger.error(f"Audio transcription failed: {e}")
            raise DocumentProcessingError(f"Audio transcription failed: {e}") from e
    
    async def _extract_text_content(self, file_path: str) -> Dict[str, Any]:
        """Extract content from plain text file."""
        logger.info(f"Reading text file: {os.path.basename(file_path)}")
        
        try:
            # Try UTF-8 first, then fallback to latin-1
            encodings = ['utf-8', 'latin-1', 'cp1252']
            content = None
            
            for encoding in encodings:
                try:
                    with open(file_path, 'r', encoding=encoding) as f:
                        content = f.read()
                    break
                except UnicodeDecodeError:
                    continue
            
            if content is None:
                raise DocumentProcessingError("Could not decode text file with any encoding")
            
            # Extract metadata
            lines = content.split('\n')
            word_count = len(content.split())
            
            # Try to detect language (simple heuristic)
            language = self._detect_language(content)
            
            return {
                'content': content,
                'preview': content[:497] + '...' if len(content) > 497 else content,
                'method': 'direct_text',
                'word_count': word_count,
                'line_count': len(lines),
                'language': language,
                'docling_doc': None
            }
            
        except Exception as e:
            logger.error(f"Text extraction failed: {e}")
            raise DocumentProcessingError(f"Text extraction failed: {e}") from e
    
    async def _extract_docling_content(
        self,
        file_path: str,
        doc_type: DocumentType
    ) -> Dict[str, Any]:
        """Extract content using Docling for structured documents."""
        logger.info(f"Processing {doc_type} with Docling: {os.path.basename(file_path)}")
        
        try:
            # Convert document
            result = self.converter.convert(file_path)
            
            # Export to markdown for consistent processing
            content = result.document.export_to_markdown()
            
            # Extract metadata from Docling document
            metadata = self._extract_docling_metadata(result.document, doc_type)
            
            return {
                'content': content,
                'preview': content[:497] + '...' if len(content) > 497 else content,
                'method': 'docling',
                'docling_doc': result.document,
                **metadata
            }
            
        except Exception as e:
            logger.error(f"Docling extraction failed: {e}")
            raise DocumentProcessingError(f"Docling extraction failed: {e}") from e
    
    def _extract_docling_metadata(
        self,
        docling_doc: DoclingDocument,
        doc_type: DocumentType
    ) -> Dict[str, Any]:
        """Extract metadata from Docling document."""
        metadata = {}
        
        try:
            # Get document text for analysis
            text_content = docling_doc.export_to_markdown()
            
            # Basic text statistics
            metadata['word_count'] = len(text_content.split())
            metadata['character_count'] = len(text_content)
            
            # Try to detect language
            metadata['language'] = self._detect_language(text_content)
            
            # Document-specific metadata
            if hasattr(docling_doc, 'pages') and docling_doc.pages:
                metadata['page_count'] = len(docling_doc.pages)
            
            # Extract title from document structure
            title = self._extract_title_from_docling(docling_doc)
            if title:
                metadata['extracted_title'] = title
            
            # Document structure information
            if hasattr(docling_doc, 'body') and docling_doc.body:
                structure_info = self._analyze_document_structure(docling_doc)
                metadata.update(structure_info)
            
        except Exception as e:
            logger.warning(f"Failed to extract some metadata: {e}")
        
        return metadata
    
    def _extract_title_from_docling(self, docling_doc: DoclingDocument) -> Optional[str]:
        """Extract title from Docling document structure."""
        try:
            # Try to find title in document metadata
            if hasattr(docling_doc, 'meta') and docling_doc.meta:
                if hasattr(docling_doc.meta, 'title') and docling_doc.meta.title:
                    return docling_doc.meta.title
            
            # Try to find first heading in content
            markdown_content = docling_doc.export_to_markdown()
            lines = markdown_content.split('\n')
            
            for line in lines[:20]:  # Check first 20 lines
                line = line.strip()
                if line.startswith('# '):
                    return line[2:].strip()
            
        except Exception as e:
            logger.debug(f"Could not extract title: {e}")
        
        return None
    
    def _analyze_document_structure(self, docling_doc: DoclingDocument) -> Dict[str, Any]:
        """Analyze document structure from Docling document."""
        structure = {
            'has_tables': False,
            'has_images': False,
            'has_headings': False,
            'heading_count': 0,
            'table_count': 0,
            'image_count': 0
        }
        
        try:
            markdown_content = docling_doc.export_to_markdown()
            
            # Count headings
            heading_count = markdown_content.count('\n#')
            structure['heading_count'] = heading_count
            structure['has_headings'] = heading_count > 0
            
            # Count tables (markdown table format)
            table_count = markdown_content.count('|')
            if table_count > 0:
                # Rough estimate: tables have multiple | per row
                structure['table_count'] = max(1, table_count // 10)
                structure['has_tables'] = True
            
            # Count images (markdown image format)
            image_count = markdown_content.count('![')
            structure['image_count'] = image_count
            structure['has_images'] = image_count > 0
            
        except Exception as e:
            logger.debug(f"Could not analyze document structure: {e}")
        
        return structure
    
    def _detect_language(self, text: str) -> str:
        """Simple language detection based on common words."""
        # This is a very basic implementation
        # In production, you might want to use a proper language detection library
        
        text_lower = text.lower()
        words = text_lower.split()
        
        if len(words) < 3:
            return 'unknown'
        
        # Common English words
        english_words = ['the', 'and', 'is', 'in', 'to', 'of', 'a', 'that', 'it', 'with', 'for', 'are', 'as', 'was', 'he', 'she', 'they']
        # Common French words
        french_words = ['le', 'de', 'et', 'à', 'un', 'il', 'être', 'en', 'avoir', 'que', 'pour', 'dans', 'ce', 'son', 'une', 'sur', 'avec']
        # Common Spanish words
        spanish_words = ['el', 'de', 'que', 'y', 'a', 'en', 'un', 'es', 'se', 'no', 'te', 'lo', 'le', 'da', 'su', 'por', 'son']
        
        english_score = sum(1 for word in words if word in english_words)
        french_score = sum(1 for word in words if word in french_words)
        spanish_score = sum(1 for word in words if word in spanish_words)
        
        # Require at least 2 matches for confidence
        min_matches = 2
        
        if english_score >= min_matches and english_score >= french_score and english_score >= spanish_score:
            return 'en'
        elif french_score >= min_matches and french_score >= spanish_score:
            return 'fr'
        elif spanish_score >= min_matches:
            return 'es'
        else:
            return 'unknown'
    
    async def _create_chunks(
        self,
        content: str,
        document: Document,
        docling_doc: Optional[DoclingDocument] = None
    ) -> List[Chunk]:
        """
        Create chunks from document content using intelligent chunking strategy.
        
        Args:
            content: Document content
            document: Document model
            docling_doc: Optional Docling document for structure-aware chunking
            
        Returns:
            List of chunks
        """
        if not content.strip():
            return []
        
        logger.info(f"Creating chunks for document {document.filename}")
        
        try:
            # Use hybrid chunking if Docling document is available
            if docling_doc is not None:
                chunks = await self._create_hybrid_chunks(content, document, docling_doc)
            else:
                chunks = await self._create_simple_chunks(content, document)
            
            logger.info(f"Created {len(chunks)} chunks")
            return chunks
            
        except Exception as e:
            logger.error(f"Chunking failed: {e}")
            # Fallback to simple chunking
            return await self._create_simple_chunks(content, document)
    
    async def _create_hybrid_chunks(
        self,
        content: str,
        document: Document,
        docling_doc: DoclingDocument
    ) -> List[Chunk]:
        """Create chunks using Docling's HybridChunker for structure-aware splitting."""
        try:
            from docling.chunking import HybridChunker
            from transformers import AutoTokenizer
            
            # Initialize tokenizer for the embedding model
            tokenizer = AutoTokenizer.from_pretrained(self.settings.EMBEDDING_MODEL)
            
            # Create HybridChunker
            chunker = HybridChunker(
                tokenizer=tokenizer,
                max_tokens=min(512, self.settings.MAX_CONTEXT_TOKENS // 8),  # Conservative limit
                merge_peers=True
            )
            
            # Chunk the document
            chunk_iter = chunker.chunk(dl_doc=docling_doc)
            docling_chunks = list(chunk_iter)
            
            # Convert to our Chunk models
            chunks = []
            current_pos = 0
            
            for i, docling_chunk in enumerate(docling_chunks):
                # Get contextualized text
                contextualized_text = chunker.contextualize(chunk=docling_chunk)
                
                if not contextualized_text.strip():
                    continue
                
                # Calculate token count
                token_count = len(tokenizer.encode(contextualized_text))
                
                # Estimate character positions
                start_pos = current_pos
                end_pos = start_pos + len(contextualized_text)
                
                # Create chunk metadata
                chunk_metadata = {
                    'chunking_method': 'hybrid',
                    'token_count': token_count,
                    'has_context': True,
                    'total_chunks': len(docling_chunks)
                }
                
                # Try to extract section information
                section_title = self._extract_section_title(contextualized_text)
                
                chunk = Chunk(
                    document_id=document.id,
                    content=contextualized_text.strip(),
                    start_index=start_pos,
                    end_index=end_pos,
                    chunk_index=i,
                    token_count=token_count,
                    section_title=section_title,
                    language=document.language,
                    metadata=chunk_metadata
                )
                
                chunks.append(chunk)
                current_pos = end_pos
            
            return chunks
            
        except ImportError:
            logger.warning("HybridChunker not available, falling back to simple chunking")
            return await self._create_simple_chunks(content, document)
        except Exception as e:
            logger.warning(f"HybridChunker failed: {e}, falling back to simple chunking")
            return await self._create_simple_chunks(content, document)
    
    async def _create_simple_chunks(
        self,
        content: str,
        document: Document
    ) -> List[Chunk]:
        """Create chunks using simple overlap-based strategy."""
        chunks = []
        chunk_size = self.settings.CHUNK_SIZE
        overlap = self.settings.CHUNK_OVERLAP
        
        # Split content into paragraphs first
        paragraphs = [p.strip() for p in content.split('\n\n') if p.strip()]
        
        current_chunk = ""
        current_pos = 0
        chunk_index = 0
        
        for paragraph in paragraphs:
            # Check if adding this paragraph exceeds chunk size
            potential_chunk = current_chunk + "\n\n" + paragraph if current_chunk else paragraph
            
            if len(potential_chunk) <= chunk_size:
                current_chunk = potential_chunk
            else:
                # Save current chunk if it exists
                if current_chunk:
                    chunk = self._create_chunk_object(
                        content=current_chunk,
                        document=document,
                        chunk_index=chunk_index,
                        start_pos=current_pos,
                        end_pos=current_pos + len(current_chunk)
                    )
                    chunks.append(chunk)
                    
                    current_pos = max(0, current_pos + len(current_chunk) - overlap)
                    chunk_index += 1
                
                # Start new chunk with current paragraph
                current_chunk = paragraph
        
        # Add final chunk
        if current_chunk:
            chunk = self._create_chunk_object(
                content=current_chunk,
                document=document,
                chunk_index=chunk_index,
                start_pos=current_pos,
                end_pos=current_pos + len(current_chunk)
            )
            chunks.append(chunk)
        
        # Update total chunks in metadata
        for chunk in chunks:
            chunk.metadata['total_chunks'] = len(chunks)
        
        return chunks
    
    def _create_chunk_object(
        self,
        content: str,
        document: Document,
        chunk_index: int,
        start_pos: int,
        end_pos: int
    ) -> Chunk:
        """Create a Chunk object with metadata."""
        # Estimate token count (rough approximation)
        token_count = len(content.split()) * 1.3  # Rough tokens per word
        
        # Extract section title if present
        section_title = self._extract_section_title(content)
        
        chunk_metadata = {
            'chunking_method': 'simple',
            'estimated_tokens': int(token_count),
            'character_count': len(content)
        }
        
        return Chunk(
            document_id=document.id,
            content=content.strip(),
            start_index=start_pos,
            end_index=end_pos,
            chunk_index=chunk_index,
            token_count=int(token_count),
            section_title=section_title,
            language=document.language,
            metadata=chunk_metadata
        )
    
    def _extract_section_title(self, content: str) -> Optional[str]:
        """Extract section title from chunk content."""
        lines = content.split('\n')
        
        for line in lines[:3]:  # Check first 3 lines
            line = line.strip()
            if line.startswith('#'):
                # Remove markdown heading markers
                title = line.lstrip('#').strip()
                if title:
                    return title
        
        return None
    
    def get_supported_extensions(self) -> List[str]:
        """Get list of supported file extensions."""
        extensions = []
        
        # Document extensions
        for doc_type in DocumentType:
            if doc_type == DocumentType.PDF:
                extensions.append('.pdf')
            elif doc_type == DocumentType.DOCX:
                extensions.extend(['.docx', '.doc'])
            elif doc_type == DocumentType.HTML:
                extensions.extend(['.html', '.htm'])
            elif doc_type == DocumentType.TXT:
                extensions.extend(['.txt', '.md', '.markdown'])
        
        # Audio extensions
        extensions.extend(list(self.AUDIO_EXTENSIONS))
        
        return sorted(extensions)
    
    def calculate_file_hash(self, file_path: str) -> str:
        """Calculate SHA-256 hash of file for deduplication."""
        hash_sha256 = hashlib.sha256()
        
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_sha256.update(chunk)
        
        return hash_sha256.hexdigest()
    
    async def cleanup_temp_files(self, file_path: str) -> None:
        """Clean up temporary files after processing."""
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                logger.debug(f"Cleaned up temporary file: {file_path}")
        except Exception as e:
            logger.warning(f"Failed to cleanup temporary file {file_path}: {e}")