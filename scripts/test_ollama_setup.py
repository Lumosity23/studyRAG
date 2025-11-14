#!/usr/bin/env python3
"""
Test simple pour vérifier que notre setup Ollama + SentenceTransformers fonctionne
"""

import asyncio
import os
from rich.console import Console
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.providers import get_ollama_client, get_llm_model, get_embedding_model, validate_configuration, get_model_info

console = Console()

async def test_ollama():
    """Test de connexion Ollama"""
    console.print("[blue]🤖 Test Ollama[/blue]")
    
    try:
        client = get_ollama_client()
        model = get_llm_model()
        
        # Test simple
        response = await client.chat(
            model=model,
            messages=[
                {"role": "user", "content": "Dis bonjour en français"}
            ]
        )
        
        console.print(f"✅ Ollama fonctionne!")
        console.print(f"Réponse: {response['message']['content']}")
        return True
        
    except Exception as e:
        console.print(f"❌ Erreur Ollama: {e}")
        return False

def test_embeddings():
    """Test des embeddings SentenceTransformers"""
    console.print("\n[blue]🔤 Test Embeddings[/blue]")
    
    try:
        model = get_embedding_model()
        
        # Test simple
        text = "Ceci est un test d'embedding"
        embedding = model.encode(text)
        
        console.print(f"✅ Embeddings fonctionnent!")
        console.print(f"Dimension: {len(embedding)}")
        console.print(f"Premiers valeurs: {embedding[:5]}")
        return True
        
    except Exception as e:
        console.print(f"❌ Erreur Embeddings: {e}")
        return False

async def main():
    """Test complet"""
    console.print("[bold green]🧪 TEST SETUP STUDYRAG[/bold green]")
    
    # Validation config
    console.print("\n[blue]⚙️ Validation Configuration[/blue]")
    if validate_configuration():
        console.print("✅ Configuration valide")
    else:
        console.print("❌ Configuration invalide")
        return
    
    # Info modèles
    info = get_model_info()
    console.print(f"\n[cyan]📋 Configuration:[/cyan]")
    for key, value in info.items():
        console.print(f"  • {key}: {value}")
    
    # Tests
    ollama_ok = await test_ollama()
    embeddings_ok = test_embeddings()
    
    # Résultat
    console.print(f"\n[bold]📊 RÉSULTATS:[/bold]")
    console.print(f"  • Ollama: {'✅' if ollama_ok else '❌'}")
    console.print(f"  • Embeddings: {'✅' if embeddings_ok else '❌'}")
    
    if ollama_ok and embeddings_ok:
        console.print("\n[bold green]🎉 Tout fonctionne ! Prêt pour StudyRAG[/bold green]")
    else:
        console.print("\n[bold red]❌ Des problèmes détectés[/bold red]")

if __name__ == "__main__":
    asyncio.run(main())