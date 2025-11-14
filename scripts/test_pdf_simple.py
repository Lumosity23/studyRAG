#!/usr/bin/env python3
"""
Test simple pour PDF avec gestion d'erreurs
"""

from docling.document_converter import DocumentConverter
from rich.console import Console
import sys

console = Console()

def test_simple_pdf():
    """Test basique d'un PDF"""
    
    console.print("[blue]🔍 Test simple PDF avec Docling[/blue]")
    
    try:
        converter = DocumentConverter()
        console.print("✓ DocumentConverter initialisé")
        
        # Test avec le PDF
        pdf_path = "pdf_exemple/esp32-c3-mini-1_datasheet_en.pdf"
        console.print(f"[cyan]Tentative de conversion: {pdf_path}[/cyan]")
        
        result = converter.convert(pdf_path)
        console.print(f"✓ Conversion réussie! Status: {result.status}")
        
        # Affiche quelques infos de base
        doc = result.document
        console.print(f"📄 Pages: {doc.num_pages}")
        
        # Essaie d'exporter en markdown
        markdown = doc.export_to_markdown()
        console.print(f"📝 Markdown généré: {len(markdown)} caractères")
        console.print(f"Aperçu: {markdown[:200]}...")
        
        return True
        
    except Exception as e:
        console.print(f"[red]❌ Erreur: {e}[/red]")
        console.print(f"[red]Type d'erreur: {type(e).__name__}[/red]")
        return False

def test_with_different_options():
    """Test avec différentes options de conversion"""
    
    console.print("\n[blue]🔧 Test avec options de conversion[/blue]")
    
    try:
        from docling.document_converter import DocumentConverter, PdfFormatOption
        from docling.datamodel.base_models import InputFormat
        
        # Options plus robustes pour PDF
        pdf_options = PdfFormatOption(
            do_ocr=True,  # Active l'OCR si nécessaire
            do_table_structure=True,  # Structure des tableaux
            table_structure_options={"do_cell_matching": True}
        )
        
        converter = DocumentConverter(
            format_options={
                InputFormat.PDF: pdf_options
            }
        )
        
        pdf_path = "pdf_exemple/esp32-c3-mini-1_datasheet_en.pdf"
        console.print(f"[cyan]Test avec options OCR: {pdf_path}[/cyan]")
        
        result = converter.convert(pdf_path)
        console.print(f"✓ Conversion avec options réussie! Status: {result.status}")
        
        return True
        
    except Exception as e:
        console.print(f"[red]❌ Erreur avec options: {e}[/red]")
        return False

if __name__ == "__main__":
    success1 = test_simple_pdf()
    success2 = test_with_different_options()
    
    if success1 or success2:
        console.print("\n[green]🎉 Au moins un test a réussi![/green]")
        sys.exit(0)
    else:
        console.print("\n[red]❌ Tous les tests ont échoué[/red]")
        sys.exit(1)