#!/usr/bin/env python3
"""
Upgrade du système d'embeddings pour améliorer la qualité RAG
"""

import asyncio
import os
from pathlib import Path
from rich.console import Console
from rich.prompt import Confirm, Prompt
from dotenv import load_dotenv

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.chroma_db import create_chroma_db
from ingest_simple import StudyRAGIngestion

load_dotenv()
console = Console()

class EmbeddingUpgrader:
    """Upgrade le système d'embeddings"""
    
    def __init__(self):
        self.available_models = {
            "1": {
                "name": "all-MiniLM-L6-v2",
                "description": "Léger et rapide (384D) - ACTUEL",
                "pros": ["Très rapide", "Faible mémoire", "Bon pour débuter"],
                "cons": ["Qualité moyenne"]
            },
            "2": {
                "name": "all-MiniLM-L12-v2", 
                "description": "Équilibré (384D)",
                "pros": ["Bon compromis vitesse/qualité", "Même dimension"],
                "cons": ["Plus lent au chargement"]
            },
            "3": {
                "name": "paraphrase-multilingual-MiniLM-L12-v2",
                "description": "Multilingue performant (384D)",
                "pros": ["Excellent pour le français", "50+ langues", "Même dimension"],
                "cons": ["Plus lent", "Plus gros"]
            },
            "4": {
                "name": "sentence-transformers/all-mpnet-base-v2",
                "description": "Maximum performance (768D)",
                "pros": ["Meilleure qualité", "État de l'art"],
                "cons": ["Plus lent", "Plus de mémoire", "Dimensions différentes"]
            }
        }
    
    def display_model_options(self):
        """Affiche les options de modèles"""
        console.print("[bold blue]🚀 UPGRADE DU SYSTÈME D'EMBEDDINGS[/bold blue]")
        console.print()
        console.print("Modèles disponibles :")
        console.print()
        
        for key, model in self.available_models.items():
            console.print(f"[cyan]{key}. {model['name']}[/cyan]")
            console.print(f"   {model['description']}")
            console.print(f"   ✅ Avantages: {', '.join(model['pros'])}")
            console.print(f"   ⚠️  Inconvénients: {', '.join(model['cons'])}")
            console.print()
    
    def update_env_file(self, new_model: str):
        """Met à jour le fichier .env avec le nouveau modèle"""
        env_path = Path(".env")
        
        if env_path.exists():
            # Lit le fichier actuel
            with open(env_path, 'r') as f:
                lines = f.readlines()
            
            # Met à jour la ligne EMBEDDING_MODEL
            updated = False
            for i, line in enumerate(lines):
                if line.startswith("EMBEDDING_MODEL="):
                    lines[i] = f"EMBEDDING_MODEL={new_model}\n"
                    updated = True
                    break
            
            # Ajoute la ligne si elle n'existe pas
            if not updated:
                lines.append(f"EMBEDDING_MODEL={new_model}\n")
            
            # Écrit le fichier mis à jour
            with open(env_path, 'w') as f:
                f.writelines(lines)
            
            console.print(f"[green]✓ Fichier .env mis à jour avec {new_model}[/green]")
        else:
            console.print("[red]❌ Fichier .env non trouvé[/red]")
    
    async def re_ingest_with_new_model(self, documents_folder: str = "documents"):
        """Re-ingère les documents avec le nouveau modèle"""
        console.print("[yellow]🔄 Re-ingestion des documents avec le nouveau modèle...[/yellow]")
        
        # Crée une nouvelle instance d'ingestion
        ingestion = StudyRAGIngestion(documents_folder=documents_folder)
        
        try:
            # Lance l'ingestion (qui va vider et re-remplir la base)
            result = await ingestion.ingest_all(clear_existing=True)
            
            if result["success"]:
                console.print(f"[green]✅ Re-ingestion réussie![/green]")
                console.print(f"   • {result['successful']} documents traités")
                console.print(f"   • {result['total_chunks']} chunks créés")
                return True
            else:
                console.print(f"[red]❌ Échec de la re-ingestion[/red]")
                return False
                
        except Exception as e:
            console.print(f"[red]❌ Erreur lors de la re-ingestion: {e}[/red]")
            return False
        finally:
            await ingestion.close()
    
    async def test_new_model(self):
        """Teste le nouveau modèle avec quelques requêtes"""
        console.print("[cyan]🧪 Test du nouveau modèle...[/cyan]")
        
        try:
            from chat_rag import StudyRAGChat
            
            chat = StudyRAGChat()
            
            test_queries = [
                "Quelles sont les caractéristiques de l'ESP32?",
                "Comment fonctionne le machine learning?",
                "Qu'est-ce qu'un microcontrôleur?"
            ]
            
            console.print("Tests de recherche :")
            for query in test_queries:
                console.print(f"[dim]Query: {query}[/dim]")
                
                results = await chat.search_knowledge_base(query, limit=3)
                
                if results:
                    best_similarity = max(r['similarity'] for r in results)
                    console.print(f"[green]✓ {len(results)} résultats, meilleure similarité: {best_similarity:.3f}[/green]")
                else:
                    console.print("[red]✗ Aucun résultat[/red]")
            
            await chat.close()
            console.print("[green]✅ Test terminé[/green]")
            
        except Exception as e:
            console.print(f"[red]❌ Erreur lors du test: {e}[/red]")
    
    async def run_upgrade(self):
        """Lance le processus d'upgrade"""
        self.display_model_options()
        
        # Choix du modèle
        choice = Prompt.ask(
            "Choisissez un modèle",
            choices=list(self.available_models.keys()),
            default="3"
        )
        
        selected_model = self.available_models[choice]
        console.print(f"\n[green]Modèle sélectionné: {selected_model['name']}[/green]")
        
        # Confirmation
        if not Confirm.ask(f"Voulez-vous upgrader vers {selected_model['name']} ?"):
            console.print("[yellow]Upgrade annulé[/yellow]")
            return
        
        # Avertissement pour les modèles avec dimensions différentes
        if choice == "4":  # all-mpnet-base-v2
            console.print("[yellow]⚠️ Ce modèle utilise 768 dimensions au lieu de 384.[/yellow]")
            console.print("[yellow]   Tous les documents devront être re-ingérés.[/yellow]")
            
            if not Confirm.ask("Continuer ?"):
                console.print("[yellow]Upgrade annulé[/yellow]")
                return
        
        # Met à jour le fichier .env
        self.update_env_file(selected_model["name"])
        
        # Re-ingestion nécessaire
        console.print()
        if Confirm.ask("Voulez-vous re-ingérer les documents maintenant ?", default=True):
            success = await self.re_ingest_with_new_model()
            
            if success:
                # Test du nouveau modèle
                console.print()
                if Confirm.ask("Voulez-vous tester le nouveau modèle ?", default=True):
                    await self.test_new_model()
                
                console.print()
                console.print("[bold green]🎉 Upgrade terminé avec succès ![/bold green]")
                console.print(f"[green]Nouveau modèle: {selected_model['name']}[/green]")
                console.print("[green]Vous pouvez maintenant utiliser le chat RAG amélioré[/green]")
            else:
                console.print("[red]❌ Échec de l'upgrade[/red]")
        else:
            console.print("[yellow]⚠️ N'oubliez pas de re-ingérer vos documents :[/yellow]")
            console.print("[yellow]python ingest_simple.py[/yellow]")


async def main():
    """Fonction principale"""
    upgrader = EmbeddingUpgrader()
    await upgrader.run_upgrade()


if __name__ == "__main__":
    asyncio.run(main())