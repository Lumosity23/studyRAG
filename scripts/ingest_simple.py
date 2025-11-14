#!/usr/bin/env python3
"""
Script d'ingestion simplifié pour StudyRAG avec ChromaDB
"""

import asyncio
import os
import logging
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime
import uuid

from rich.console import Console
from rich.progress import track
from dotenv import load_dotenv

from docling.document_converter import DocumentConverter
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.chroma_db import create_chroma_db
from ingestion.embedder import create_embedder

# Load environment variables
load_dotenv()

console = Console()
logger = logging.getLogger(__name__)

class StudyRAGIngestion:
    """Pipeline d'ingestion pour StudyRAG"""
    
    def __init__(self, documents_folder: str = "documents", chunk_size: int = 300):
        """
        Initialize ingestion pipeline
        
        Args:
            documents_folder: Folder containing documents to ingest
            chunk_size: Size of text chunks
        """
        self.documents_folder = Path(documents_folder)
        self.chunk_size = chunk_size
        
        # Initialize components
        self.converter = DocumentConverter()
        self.embedder = create_embedder()
        self.db = create_chroma_db()
        
        console.print(f"[blue]📁 Documents folder: {self.documents_folder}[/blue]")
        console.print(f"[blue]📏 Chunk size: {chunk_size}[/blue]")
    
    def get_supported_files(self) -> List[Path]:
        """Get list of supported files in documents folder"""
        supported_extensions = {'.md', '.html', '.txt', '.pdf', '.docx', '.pptx'}
        
        files = []
        for ext in supported_extensions:
            files.extend(self.documents_folder.glob(f"*{ext}"))
        
        return sorted(files)
    
    def chunk_with_docling_structure(self, document, chunk_size: int = 300) -> List[Dict[str, Any]]:
        """
        Utilise la structure native de Docling pour créer des chunks intelligents
        Adapté de notre main.py
        """
        chunks = []
        current_chunk = ""
        current_context = ""
        
        for item_tuple in document.iterate_items():
            item = item_tuple[0]
            item_type = type(item).__name__
            
            # Récupère le contenu textuel de l'item
            if hasattr(item, 'text'):
                content = item.text
            elif hasattr(item, 'content_layer') and hasattr(item.content_layer, 'text'):
                content = item.content_layer.text
            else:
                content = str(item)
            
            content = content.strip()
            if not content:
                continue
            
            # Gestion selon le type d'élément
            if item_type == "TitleItem":
                if current_chunk:
                    chunks.append(current_chunk.strip())
                current_context = content
                current_chunk = content
                
            elif item_type == "SectionHeaderItem":
                if len(current_chunk) > chunk_size // 2:
                    chunks.append(current_chunk.strip())
                    current_chunk = f"{current_context}\n\n{content}" if current_context else content
                else:
                    current_chunk += f"\n\n{content}"
                
            elif item_type == "TextItem":
                test_chunk = current_chunk + f"\n\n{content}"
                
                if len(test_chunk) > chunk_size:
                    if current_chunk:
                        chunks.append(current_chunk.strip())
                    
                    if current_context and len(content) > 50:
                        current_chunk = f"{current_context}\n\n{content}"
                    else:
                        current_chunk = content
                else:
                    current_chunk = test_chunk
            
            else:
                # Autres types d'éléments
                test_chunk = current_chunk + f"\n\n{content}"
                
                if len(test_chunk) > chunk_size:
                    if current_chunk:
                        chunks.append(current_chunk.strip())
                    current_chunk = content
                else:
                    current_chunk = test_chunk
        
        # Ajoute le dernier chunk
        if current_chunk.strip():
            chunks.append(current_chunk.strip())
        
        # Filtre les chunks trop petits
        chunks = [chunk for chunk in chunks if len(chunk) >= 50]
        
        return [{"content": chunk, "index": i} for i, chunk in enumerate(chunks)]
    
    async def process_document(self, file_path: Path) -> Dict[str, Any]:
        """Process a single document"""
        console.print(f"[cyan]Processing: {file_path.name}[/cyan]")
        
        try:
            # Convert with Docling
            result = self.converter.convert(str(file_path))
            
            # Create chunks using Docling structure
            raw_chunks = self.chunk_with_docling_structure(result.document, self.chunk_size)
            
            if not raw_chunks:
                console.print(f"[yellow]No chunks created for {file_path.name}[/yellow]")
                return {"success": False, "error": "No chunks created"}
            
            # Generate embeddings
            console.print(f"  Generating embeddings for {len(raw_chunks)} chunks...")
            
            processed_chunks = []
            document_id = str(uuid.uuid4())
            
            for chunk_data in raw_chunks:
                # Generate embedding
                embedding = await self.embedder.generate_embedding(chunk_data["content"])
                
                # Prepare chunk for database
                chunk = {
                    "content": chunk_data["content"],
                    "embedding": embedding,
                    "document_id": document_id,
                    "document_title": file_path.stem,
                    "document_source": str(file_path),
                    "chunk_index": chunk_data["index"],
                    "token_count": len(chunk_data["content"].split()),
                    "metadata": {
                        "file_extension": file_path.suffix,
                        "file_size": file_path.stat().st_size,
                        "processed_at": datetime.now().isoformat(),
                        "chunk_size_setting": self.chunk_size
                    }
                }
                
                processed_chunks.append(chunk)
            
            # Add to database
            success = await self.db.add_chunks(processed_chunks)
            
            if success:
                console.print(f"[green]✓ {file_path.name}: {len(processed_chunks)} chunks added[/green]")
                return {
                    "success": True,
                    "file": str(file_path),
                    "chunks_count": len(processed_chunks),
                    "document_id": document_id
                }
            else:
                console.print(f"[red]✗ Failed to add chunks for {file_path.name}[/red]")
                return {"success": False, "error": "Database insertion failed"}
                
        except Exception as e:
            console.print(f"[red]✗ Error processing {file_path.name}: {e}[/red]")
            return {"success": False, "error": str(e)}
    
    async def ingest_all(self, clear_existing: bool = True) -> Dict[str, Any]:
        """Ingest all supported documents"""
        console.print("[bold blue]🚀 Starting StudyRAG Ingestion[/bold blue]")
        
        # Clear existing data if requested
        if clear_existing:
            console.print("[yellow]Clearing existing data...[/yellow]")
            await self.db.clear_collection()
        
        # Get files to process
        files = self.get_supported_files()
        
        if not files:
            console.print("[yellow]No supported files found[/yellow]")
            return {"success": False, "error": "No files found"}
        
        console.print(f"[blue]Found {len(files)} files to process[/blue]")
        
        # Process files
        results = []
        successful = 0
        failed = 0
        
        for file_path in track(files, description="Processing documents..."):
            result = await self.process_document(file_path)
            results.append(result)
            
            if result["success"]:
                successful += 1
            else:
                failed += 1
        
        # Final stats
        stats = await self.db.get_stats()
        
        console.print(f"\n[bold green]📊 Ingestion Complete![/bold green]")
        console.print(f"  • Successful: {successful}")
        console.print(f"  • Failed: {failed}")
        console.print(f"  • Total chunks in DB: {stats.get('total_chunks', 0)}")
        
        return {
            "success": True,
            "files_processed": len(files),
            "successful": successful,
            "failed": failed,
            "total_chunks": stats.get('total_chunks', 0),
            "results": results
        }
    
    async def close(self):
        """Close connections"""
        await self.db.close()


async def main():
    """Main ingestion function"""
    import argparse
    
    parser = argparse.ArgumentParser(description="StudyRAG Document Ingestion")
    parser.add_argument("--documents", default="documents", help="Documents folder")
    parser.add_argument("--chunk-size", type=int, default=300, help="Chunk size")
    parser.add_argument("--no-clear", action="store_true", help="Don't clear existing data")
    
    args = parser.parse_args()
    
    # Create ingestion pipeline
    ingestion = StudyRAGIngestion(
        documents_folder=args.documents,
        chunk_size=args.chunk_size
    )
    
    try:
        # Run ingestion
        result = await ingestion.ingest_all(clear_existing=not args.no_clear)
        
        if result["success"]:
            console.print("\n[bold green]🎉 Ingestion successful![/bold green]")
        else:
            console.print(f"\n[bold red]❌ Ingestion failed: {result.get('error')}[/bold red]")
            
    except KeyboardInterrupt:
        console.print("\n[yellow]Ingestion interrupted by user[/yellow]")
    except Exception as e:
        console.print(f"\n[red]Unexpected error: {e}[/red]")
    finally:
        await ingestion.close()


if __name__ == "__main__":
    asyncio.run(main())