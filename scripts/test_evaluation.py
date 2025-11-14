#!/usr/bin/env python3
"""
Script d'évaluation pour tester la qualité du parsing et chunking
"""

import json
from pathlib import Path
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

console = Console()

class TestEvaluator:
    def __init__(self):
        self.expected_elements = {
            "titles": [
                "Cours de Machine Learning - Chapitre 1",
                "Introduction au Machine Learning", 
                "Définitions importantes",
                "Types d'algorithmes",
                "Régression linéaire",
                "Classification", 
                "Clustering",
                "Évaluation des modèles",
                "Processus de développement ML",
                "Défis courants",
                "Conclusion"
            ],
            "key_terms": [
                "Machine Learning",
                "apprentissage supervisé",
                "apprentissage non supervisé", 
                "apprentissage par renforcement",
                "régression linéaire",
                "classification",
                "clustering",
                "overfitting",
                "underfitting",
                "K-means",
                "SVM",
                "Random Forest"
            ],
            "formulas": [
                "y = mx + b"
            ],
            "algorithms": [
                "K-Nearest Neighbors",
                "Support Vector Machine", 
                "Random Forest",
                "K-means",
                "DBSCAN"
            ],
            "metrics": [
                "MSE",
                "RMSE", 
                "MAE",
                "R-squared",
                "Accuracy",
                "Precision",
                "Recall",
                "F1-Score"
            ]
        }
    
    def evaluate_processed_document(self, json_file: str):
        """Évalue la qualité du parsing d'un document traité"""
        
        if not Path(json_file).exists():
            console.print(f"[red]Fichier non trouvé: {json_file}[/red]")
            return
        
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        chunks = data.get('chunks', [])
        all_content = ' '.join(chunks)
        
        console.print(Panel.fit("📊 ÉVALUATION DU PARSING", style="bold blue"))
        
        # Statistiques de base
        stats_table = Table(title="Statistiques générales")
        stats_table.add_column("Métrique", style="cyan")
        stats_table.add_column("Valeur", style="green")
        
        stats_table.add_row("Nombre de chunks", str(len(chunks)))
        stats_table.add_row("Taille moyenne chunk", f"{sum(len(c) for c in chunks) // len(chunks)} chars")
        stats_table.add_row("Chunk le plus long", f"{max(len(c) for c in chunks)} chars")
        stats_table.add_row("Chunk le plus court", f"{min(len(c) for c in chunks)} chars")
        
        console.print(stats_table)
        console.print()
        
        # Évaluation du contenu
        content_table = Table(title="Détection du contenu attendu")
        content_table.add_column("Catégorie", style="cyan")
        content_table.add_column("Trouvés/Total", style="green")
        content_table.add_column("Pourcentage", style="yellow")
        content_table.add_column("Détails", style="dim")
        
        for category, expected_items in self.expected_elements.items():
            found_items = []
            for item in expected_items:
                if item.lower() in all_content.lower():
                    found_items.append(item)
            
            percentage = (len(found_items) / len(expected_items)) * 100
            status = "✓" if percentage > 80 else "⚠️" if percentage > 50 else "❌"
            
            content_table.add_row(
                category.title(),
                f"{len(found_items)}/{len(expected_items)}",
                f"{percentage:.1f}% {status}",
                ", ".join(found_items[:3]) + ("..." if len(found_items) > 3 else "")
            )
        
        console.print(content_table)
        console.print()
        
        # Analyse des chunks
        console.print(Panel.fit("🔍 ANALYSE DES CHUNKS", style="bold green"))
        
        chunk_analysis = Table(title="Aperçu des chunks")
        chunk_analysis.add_column("Chunk #", style="cyan")
        chunk_analysis.add_column("Taille", style="green")
        chunk_analysis.add_column("Début du contenu", style="dim")
        
        for i, chunk in enumerate(chunks[:5]):  # Affiche les 5 premiers chunks
            preview = chunk[:100].replace('\n', ' ').strip()
            chunk_analysis.add_row(
                str(i+1),
                f"{len(chunk)} chars",
                preview + "..." if len(chunk) > 100 else preview
            )
        
        if len(chunks) > 5:
            chunk_analysis.add_row("...", "...", f"... et {len(chunks)-5} autres chunks")
        
        console.print(chunk_analysis)
        
        # Score global
        total_found = sum(len([item for item in items if item.lower() in all_content.lower()]) 
                         for items in self.expected_elements.values())
        total_expected = sum(len(items) for items in self.expected_elements.values())
        global_score = (total_found / total_expected) * 100
        
        score_color = "green" if global_score > 80 else "yellow" if global_score > 60 else "red"
        console.print(f"\n[bold {score_color}]Score global: {global_score:.1f}%[/bold {score_color}]")
        
        return {
            "chunks_count": len(chunks),
            "global_score": global_score,
            "content_detection": {cat: len([item for item in items if item.lower() in all_content.lower()]) 
                                for cat, items in self.expected_elements.items()}
        }

def main():
    evaluator = TestEvaluator()
    
    # Cherche le fichier de test traité
    processed_file = Path("./processed_docs/test_document_processed.json")
    
    if not processed_file.exists():
        console.print("[yellow]Fichier de test non trouvé. Lancez d'abord:[/yellow]")
        console.print("[cyan]python main.py parse test_document.md[/cyan]")
        return
    
    evaluator.evaluate_processed_document(str(processed_file))

if __name__ == "__main__":
    main()