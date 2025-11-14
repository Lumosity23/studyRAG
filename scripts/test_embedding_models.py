#!/usr/bin/env python3
"""
Test de différents modèles d'embedding pour améliorer la qualité RAG
"""

import asyncio
import time
from typing import List, Dict, Any
from rich.console import Console
from rich.table import Table
from rich.progress import track
from sentence_transformers import SentenceTransformer
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

console = Console()

class EmbeddingModelTester:
    """Teste différents modèles d'embedding"""
    
    def __init__(self):
        # Modèles à tester (du plus léger au plus performant)
        self.models_to_test = {
            # Modèles légers et rapides
            "all-MiniLM-L6-v2": {
                "description": "Léger, rapide (384 dim)",
                "size": "80MB",
                "languages": "Multilingue"
            },
            "all-MiniLM-L12-v2": {
                "description": "Équilibré (384 dim)", 
                "size": "120MB",
                "languages": "Multilingue"
            },
            
            # Modèles français spécialisés
            "dangvantuan/sentence-camembert-large": {
                "description": "Spécialisé français (1024 dim)",
                "size": "440MB", 
                "languages": "Français"
            },
            
            # Modèles multilingues performants
            "paraphrase-multilingual-MiniLM-L12-v2": {
                "description": "Multilingue performant (384 dim)",
                "size": "120MB",
                "languages": "50+ langues"
            },
            
            # Modèles de dernière génération
            "sentence-transformers/all-mpnet-base-v2": {
                "description": "Très performant anglais (768 dim)",
                "size": "420MB",
                "languages": "Anglais"
            },
            
            # Modèles Gemma/Google (si disponibles)
            "google/gemma-2b": {
                "description": "Gemma 2B (si compatible)",
                "size": "5GB",
                "languages": "Multilingue",
                "note": "Nécessite adaptation"
            }
        }
        
        # Queries de test en français (domaine étudiant)
        self.test_queries = [
            "Quelles sont les caractéristiques techniques de l'ESP32?",
            "Comment programmer un microcontrôleur?", 
            "Qu'est-ce que le machine learning?",
            "Expliquer les algorithmes de classification",
            "Architecture des réseaux de neurones",
            "Développement web avec JavaScript",
            "Bases de données relationnelles",
            "Sécurité informatique et cryptographie"
        ]
        
        # Documents de test (extraits de notre base)
        self.test_documents = [
            "L'ESP32 est un microcontrôleur développé par Espressif Systems. Il intègre WiFi et Bluetooth dans un seul chip.",
            "Le Machine Learning (ML) est une branche de l'intelligence artificielle qui permet aux machines d'apprendre automatiquement.",
            "JavaScript est utilisé pour le développement web côté client et serveur avec Node.js.",
            "Les réseaux de neurones sont composés de couches de neurones artificiels connectés entre eux.",
            "La classification consiste à prédire des catégories ou classes discrètes à partir de données.",
            "Les bases de données relationnelles organisent les données en tables avec des relations entre elles.",
            "La cryptographie protège les informations en les transformant en code secret.",
            "Arduino IDE est un environnement de développement pour programmer les microcontrôleurs."
        ]
    
    def load_model_safe(self, model_name: str) -> tuple:
        """Charge un modèle de manière sécurisée"""
        try:
            console.print(f"[cyan]Chargement de {model_name}...[/cyan]")
            start_time = time.time()
            
            model = SentenceTransformer(model_name)
            load_time = time.time() - start_time
            
            # Test rapide pour obtenir les dimensions
            test_embedding = model.encode("test")
            dimensions = len(test_embedding)
            
            console.print(f"[green]✓ {model_name} chargé ({dimensions}D, {load_time:.1f}s)[/green]")
            return model, dimensions, load_time, None
            
        except Exception as e:
            console.print(f"[red]✗ Erreur avec {model_name}: {e}[/red]")
            return None, 0, 0, str(e)
    
    def evaluate_model_performance(self, model, model_name: str) -> Dict[str, Any]:
        """Évalue les performances d'un modèle"""
        console.print(f"[blue]Évaluation de {model_name}...[/blue]")
        
        # Encode les documents et queries
        start_time = time.time()
        doc_embeddings = model.encode(self.test_documents)
        query_embeddings = model.encode(self.test_queries)
        encoding_time = time.time() - start_time
        
        # Calcule les similarités
        similarities = cosine_similarity(query_embeddings, doc_embeddings)
        
        # Métriques de qualité
        results = {
            "encoding_time": encoding_time,
            "avg_similarity": np.mean(similarities),
            "max_similarity": np.max(similarities),
            "min_similarity": np.min(similarities),
            "std_similarity": np.std(similarities)
        }
        
        # Trouve les meilleures correspondances pour chaque query
        best_matches = []
        for i, query in enumerate(self.test_queries):
            best_doc_idx = np.argmax(similarities[i])
            best_similarity = similarities[i][best_doc_idx]
            best_matches.append({
                "query": query[:50] + "...",
                "best_doc": self.test_documents[best_doc_idx][:50] + "...",
                "similarity": best_similarity
            })
        
        results["best_matches"] = best_matches
        return results
    
    async def run_comparison(self):
        """Lance la comparaison des modèles"""
        console.print("[bold blue]🧪 COMPARAISON DES MODÈLES D'EMBEDDING[/bold blue]")
        console.print()
        
        results = {}
        
        # Teste chaque modèle
        for model_name, info in self.models_to_test.items():
            console.print(f"[yellow]📊 Test: {model_name}[/yellow]")
            console.print(f"   Description: {info['description']}")
            console.print(f"   Taille: {info['size']}")
            console.print()
            
            # Charge le modèle
            model, dimensions, load_time, error = self.load_model_safe(model_name)
            
            if model is None:
                results[model_name] = {
                    "error": error,
                    "status": "failed"
                }
                console.print()
                continue
            
            # Évalue les performances
            try:
                performance = self.evaluate_model_performance(model, model_name)
                
                results[model_name] = {
                    "status": "success",
                    "dimensions": dimensions,
                    "load_time": load_time,
                    "info": info,
                    "performance": performance
                }
                
                console.print(f"[green]✓ Évaluation terminée[/green]")
                
            except Exception as e:
                console.print(f"[red]✗ Erreur d'évaluation: {e}[/red]")
                results[model_name] = {
                    "error": str(e),
                    "status": "eval_failed"
                }
            
            console.print()
        
        # Affiche les résultats
        self.display_results(results)
        
        return results
    
    def display_results(self, results: Dict[str, Any]):
        """Affiche les résultats de comparaison"""
        console.print("[bold green]📊 RÉSULTATS DE LA COMPARAISON[/bold green]")
        console.print()
        
        # Tableau de comparaison
        table = Table(title="Comparaison des modèles d'embedding")
        table.add_column("Modèle", style="cyan")
        table.add_column("Status", style="green")
        table.add_column("Dimensions", style="yellow")
        table.add_column("Temps chargement", style="blue")
        table.add_column("Temps encoding", style="blue")
        table.add_column("Similarité moy.", style="magenta")
        table.add_column("Recommandation", style="bold")
        
        successful_models = []
        
        for model_name, result in results.items():
            if result["status"] == "success":
                perf = result["performance"]
                
                # Calcule un score global
                score = (
                    perf["avg_similarity"] * 0.4 +  # Qualité des embeddings
                    (1 / (perf["encoding_time"] + 1)) * 0.3 +  # Vitesse
                    (1 / (result["load_time"] + 1)) * 0.3  # Temps de chargement
                )
                
                successful_models.append((model_name, score, result))
                
                # Recommandation basée sur le score
                if score > 0.7:
                    recommendation = "🏆 Excellent"
                elif score > 0.5:
                    recommendation = "✅ Bon"
                elif score > 0.3:
                    recommendation = "⚠️ Moyen"
                else:
                    recommendation = "❌ Faible"
                
                table.add_row(
                    model_name.split("/")[-1],
                    "✅ OK",
                    str(result["dimensions"]),
                    f"{result['load_time']:.1f}s",
                    f"{perf['encoding_time']:.2f}s",
                    f"{perf['avg_similarity']:.3f}",
                    recommendation
                )
            else:
                table.add_row(
                    model_name.split("/")[-1],
                    "❌ Échec",
                    "-",
                    "-",
                    "-",
                    "-",
                    "Non testé"
                )
        
        console.print(table)
        console.print()
        
        # Recommandations
        if successful_models:
            # Trie par score
            successful_models.sort(key=lambda x: x[1], reverse=True)
            best_model = successful_models[0]
            
            console.print("[bold green]🎯 RECOMMANDATIONS:[/bold green]")
            console.print(f"🏆 **Meilleur modèle**: {best_model[0]}")
            console.print(f"   Score: {best_model[1]:.3f}")
            console.print(f"   Dimensions: {best_model[2]['dimensions']}")
            console.print(f"   Similarité moyenne: {best_model[2]['performance']['avg_similarity']:.3f}")
            console.print()
            
            console.print("📋 **Pour votre usage**:")
            console.print("• **Léger et rapide**: all-MiniLM-L6-v2 (actuel)")
            console.print("• **Équilibré**: paraphrase-multilingual-MiniLM-L12-v2")
            console.print("• **Français spécialisé**: sentence-camembert-large")
            console.print("• **Maximum performance**: all-mpnet-base-v2")


async def main():
    """Fonction principale"""
    tester = EmbeddingModelTester()
    await tester.run_comparison()
    
    console.print()
    console.print("[bold blue]💡 CONSEILS POUR AMÉLIORER VOTRE RAG:[/bold blue]")
    console.print()
    console.print("1. **Plus de données = meilleurs résultats**")
    console.print("   • Ajoutez plus de documents dans votre domaine")
    console.print("   • Diversifiez les sources (cours, articles, docs techniques)")
    console.print()
    console.print("2. **Fine-tuning** (avancé)")
    console.print("   • Créez des paires question-réponse de votre domaine")
    console.print("   • Utilisez sentence-transformers pour fine-tuner")
    console.print()
    console.print("3. **Chunking intelligent**")
    console.print("   • Testez différentes tailles de chunks (200-500 chars)")
    console.print("   • Ajoutez plus d'overlap entre chunks")
    console.print()
    console.print("4. **Recherche hybride**")
    console.print("   • Combinez recherche sémantique + recherche par mots-clés")
    console.print("   • Utilisez le re-ranking des résultats")


if __name__ == "__main__":
    asyncio.run(main())