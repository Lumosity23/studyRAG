#!/usr/bin/env python3
"""
Script pour tester différentes stratégies de chunking
"""

import subprocess
import sys
from pathlib import Path
from rich.console import Console
from rich.table import Table
import json

console = Console()

def test_chunk_sizes():
    """Teste différentes tailles de chunks"""
    
    console.print("[bold blue]🔬 TEST DES STRATÉGIES DE CHUNKING[/bold blue]")
    console.print()
    
    # Différentes configurations à tester
    configs = [
        {"chunk_size": 200, "overlap": 30, "name": "Petit (200/30)"},
        {"chunk_size": 300, "overlap": 50, "name": "Moyen (300/50)"},
        {"chunk_size": 400, "overlap": 60, "name": "Grand (400/60)"},
        {"chunk_size": 500, "overlap": 80, "name": "Très grand (500/80)"}
    ]
    
    results = []
    
    for config in configs:
        console.print(f"[cyan]Test: {config['name']}[/cyan]")
        
        try:
            # Lance le parsing avec cette config
            result = subprocess.run([
                sys.executable, "main.py", "parse", "test_document.md",
                "--chunk-size", str(config["chunk_size"]),
                "--overlap", str(config["overlap"])
            ], capture_output=True, text=True, check=True)
            
            # Lit les résultats
            json_file = Path("./processed_docs/test_document_processed.json")
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            chunks = data['chunks']
            chunk_lengths = [len(c) for c in chunks]
            
            results.append({
                "config": config['name'],
                "chunk_count": len(chunks),
                "avg_length": sum(chunk_lengths) // len(chunk_lengths),
                "min_length": min(chunk_lengths),
                "max_length": max(chunk_lengths),
                "total_chars": sum(chunk_lengths)
            })
            
            console.print(f"  ✓ {len(chunks)} chunks créés")
            
        except Exception as e:
            console.print(f"  ❌ Erreur: {e}")
            continue
    
    # Affiche le tableau comparatif
    console.print()
    table = Table(title="Comparaison des stratégies de chunking")
    table.add_column("Configuration", style="cyan")
    table.add_column("Nb chunks", style="green")
    table.add_column("Taille moy.", style="yellow")
    table.add_column("Min/Max", style="dim")
    table.add_column("Total chars", style="blue")
    table.add_column("Recommandation", style="bold")
    
    for result in results:
        # Évalue la qualité
        avg_len = result['avg_length']
        if 200 <= avg_len <= 350:
            recommendation = "✅ Optimal"
        elif 150 <= avg_len <= 450:
            recommendation = "⚠️ Acceptable"
        else:
            recommendation = "❌ Problématique"
        
        table.add_row(
            result['config'],
            str(result['chunk_count']),
            f"{result['avg_length']} chars",
            f"{result['min_length']}-{result['max_length']}",
            str(result['total_chars']),
            recommendation
        )
    
    console.print(table)
    
    # Recommandation finale
    console.print()
    console.print("[bold green]💡 RECOMMANDATIONS:[/bold green]")
    console.print("• Pour RAG optimal: chunks de 200-350 caractères")
    console.print("• Overlap de 15-20% de la taille du chunk")
    console.print("• Plus de chunks = meilleure précision de recherche")
    console.print("• Éviter les chunks > 400 chars pour la vectorisation")

def show_chunk_examples():
    """Montre des exemples de chunks avec la meilleure config"""
    console.print()
    console.print("[bold blue]📝 EXEMPLES DE CHUNKS (config optimale)[/bold blue]")
    
    # Utilise la config recommandée
    subprocess.run([
        sys.executable, "main.py", "parse", "test_document.md",
        "--chunk-size", "300", "--overlap", "50"
    ], capture_output=True, text=True)
    
    json_file = Path("./processed_docs/test_document_processed.json")
    with open(json_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    chunks = data['chunks']
    
    for i, chunk in enumerate(chunks[:3]):  # Montre les 3 premiers
        console.print(f"\n[cyan]Chunk {i+1} ({len(chunk)} chars):[/cyan]")
        console.print(f"[dim]{chunk}[/dim]")
        console.print("-" * 50)

if __name__ == "__main__":
    test_chunk_sizes()
    show_chunk_examples()