#!/usr/bin/env python3
"""
StudyRAG - Outil de parsing et vectorisation de documents pour étudiants
Utilise Docling pour le parsing et Ollama pour le RAG local
"""

import click
from pathlib import Path
from rich.console import Console
from rich.progress import track
import json

from docling.document_converter import DocumentConverter
from docling.datamodel.base_models import InputFormat

console = Console()

class StudyRAG:
    def __init__(self):
        self.converter = DocumentConverter()
        self.output_dir = Path("./processed_docs")
        self.output_dir.mkdir(exist_ok=True)
        self.chunk_size = 300
        self.overlap = 50
    
    def process_document(self, file_path: str) -> dict:
        """Parse un document avec Docling et retourne les chunks"""
        console.print(f"[blue]Processing: {file_path}[/blue]")
        
        try:
            result = self.converter.convert(file_path)
            
            # Utilise la structure native de Docling pour le chunking
            chunks = self._chunk_with_docling_structure(result.document)
            
            # Sauvegarde
            doc_name = Path(file_path).stem
            output_file = self.output_dir / f"{doc_name}_processed.json"
            
            processed_data = {
                "source": file_path,
                "chunks": chunks,
                "metadata": {
                    "total_chunks": len(chunks),
                    "original_format": str(result.input.format),
                    "chunking_method": "docling_native_structure"
                }
            }
            
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(processed_data, f, indent=2, ensure_ascii=False)
            
            console.print(f"[green]✓ Processed: {len(chunks)} chunks saved to {output_file}[/green]")
            return processed_data
            
        except Exception as e:
            console.print(f"[red]Error processing {file_path}: {e}[/red]")
            return None
    
    def _chunk_with_docling_structure(self, document) -> list:
        """Utilise la structure native de Docling pour créer des chunks intelligents"""
        chunks = []
        current_chunk = ""
        current_context = ""  # Pour garder le contexte (titre de section, etc.)
        
        for item_tuple in document.iterate_items():
            item = item_tuple[0]  # Le premier élément du tuple est l'item
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
                # Nouveau document/chapitre - commence un nouveau chunk
                if current_chunk:
                    chunks.append(current_chunk.strip())
                current_context = content
                current_chunk = content
                
            elif item_type == "SectionHeaderItem":
                # Nouveau header - peut commencer un nouveau chunk si le current est assez long
                if len(current_chunk) > self.chunk_size // 2:
                    chunks.append(current_chunk.strip())
                    current_chunk = f"{current_context}\n\n{content}" if current_context else content
                else:
                    current_chunk += f"\n\n{content}"
                
            elif item_type == "TextItem":
                # Contenu textuel - ajoute au chunk actuel
                test_chunk = current_chunk + f"\n\n{content}"
                
                if len(test_chunk) > self.chunk_size:
                    # Le chunk devient trop grand, on le sauve et commence un nouveau
                    if current_chunk:
                        chunks.append(current_chunk.strip())
                    
                    # Commence le nouveau chunk avec le contexte si nécessaire
                    if current_context and len(content) > 50:  # Seulement si le contenu est substantiel
                        current_chunk = f"{current_context}\n\n{content}"
                    else:
                        current_chunk = content
                else:
                    current_chunk = test_chunk
            
            else:
                # Autres types d'éléments (tables, listes, etc.)
                test_chunk = current_chunk + f"\n\n{content}"
                
                if len(test_chunk) > self.chunk_size:
                    if current_chunk:
                        chunks.append(current_chunk.strip())
                    current_chunk = content
                else:
                    current_chunk = test_chunk
        
        # Ajoute le dernier chunk
        if current_chunk.strip():
            chunks.append(current_chunk.strip())
        
        # Filtre les chunks trop petits (moins de 50 caractères)
        chunks = [chunk for chunk in chunks if len(chunk) >= 50]
        
        return chunks

@click.group()
def cli():
    """StudyRAG - Outil de parsing de documents pour étudiants"""
    pass

@cli.command()
@click.argument('file_path')
@click.option('--chunk-size', default=300, help='Taille max des chunks en caractères')
@click.option('--overlap', default=50, help='Overlap entre chunks en caractères')
def parse(file_path, chunk_size, overlap):
    """Parse un document avec Docling"""
    rag = StudyRAG()
    rag.chunk_size = chunk_size
    rag.overlap = overlap
    result = rag.process_document(file_path)
    
    if result:
        console.print(f"[green]Document traité avec succès![/green]")
        console.print(f"Chunks créés: {result['metadata']['total_chunks']}")
        console.print(f"Taille moyenne: {sum(len(c) for c in result['chunks']) // len(result['chunks'])} chars")

@cli.command()
@click.argument('directory')
def batch_parse(directory):
    """Parse tous les documents d'un dossier"""
    rag = StudyRAG()
    dir_path = Path(directory)
    
    if not dir_path.exists():
        console.print(f"[red]Dossier non trouvé: {directory}[/red]")
        return
    
    # Extensions supportées par Docling
    supported_extensions = {'.pdf', '.docx', '.pptx', '.xlsx', '.html', '.png', '.jpg', '.jpeg', '.tiff'}
    files = [f for f in dir_path.rglob('*') if f.suffix.lower() in supported_extensions]
    
    console.print(f"[blue]Trouvé {len(files)} fichiers à traiter[/blue]")
    
    for file_path in track(files, description="Processing files..."):
        rag.process_document(str(file_path))

@cli.command()
def list_processed():
    """Liste les documents traités"""
    output_dir = Path("./processed_docs")
    if not output_dir.exists():
        console.print("[yellow]Aucun document traité trouvé[/yellow]")
        return
    
    files = list(output_dir.glob("*.json"))
    console.print(f"[blue]Documents traités ({len(files)}):[/blue]")
    
    for file in files:
        with open(file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        console.print(f"  • {file.stem}: {data['metadata']['total_chunks']} chunks")

if __name__ == "__main__":
    cli()