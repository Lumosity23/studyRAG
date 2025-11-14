#!/usr/bin/env python3
"""
Chat RAG Terminal pour StudyRAG
Utilise Ollama + ChromaDB + SentenceTransformers
"""

import asyncio
import os
import logging
from typing import List, Dict, Any
from datetime import datetime

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.markdown import Markdown
from dotenv import load_dotenv

from utils.chroma_db import create_chroma_db
from utils.providers import get_ollama_client, get_llm_model, get_embedding_model
from ingestion.embedder import create_embedder

# Load environment variables
load_dotenv()

console = Console()
logger = logging.getLogger(__name__)

class StudyRAGChat:
    """Chat RAG avec Ollama et ChromaDB"""
    
    def __init__(self):
        """Initialize RAG chat system"""
        self.db = create_chroma_db()
        self.embedder = create_embedder()
        self.ollama_client = get_ollama_client()
        self.model_name = get_llm_model()
        self.conversation_history = []
        
        console.print("[blue]🤖 Initialisation du système RAG...[/blue]")
    
    async def search_knowledge_base(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Search the knowledge base using semantic similarity
        
        Args:
            query: Search query
            limit: Maximum number of results
            
        Returns:
            List of relevant chunks with metadata
        """
        try:
            # Use ChromaDB's built-in text search (simpler and more reliable)
            results = await self.db.search_chunks_by_text(query, limit=limit)
            
            return results
            
        except Exception as e:
            logger.error(f"Error searching knowledge base: {e}")
            return []
    
    def format_search_results(self, results: List[Dict[str, Any]]) -> str:
        """Format search results for the LLM context"""
        if not results:
            return "Aucun document pertinent trouvé dans la base de connaissances."
        
        context_parts = []
        for i, result in enumerate(results, 1):
            metadata = result.get('metadata', {})
            source = metadata.get('document_title', 'Document inconnu')
            similarity = result.get('similarity', 0)
            
            context_parts.append(
                f"[Document {i}: {source} (pertinence: {similarity:.2f})]\n"
                f"{result['content']}\n"
            )
        
        return "\n".join(context_parts)
    
    async def generate_response(self, user_query: str, context: str) -> str:
        """
        Generate response using Ollama with RAG context
        
        Args:
            user_query: User's question
            context: Retrieved context from knowledge base
            
        Returns:
            Generated response
        """
        # Construct the prompt with context
        system_prompt = """Tu es un assistant intelligent qui aide les étudiants en répondant à leurs questions basées sur une base de connaissances.

Instructions:
- Utilise UNIQUEMENT les informations fournies dans le contexte ci-dessous pour répondre
- Si l'information n'est pas dans le contexte, dis-le clairement
- Sois précis et cite les sources quand c'est pertinent
- Réponds en français de manière claire et pédagogique
- Si plusieurs documents contiennent des informations pertinentes, synthétise-les

Contexte de la base de connaissances:
{context}

Question de l'étudiant: {query}

Réponse:"""

        prompt = system_prompt.format(context=context, query=user_query)
        
        try:
            # Call Ollama
            response = await self.ollama_client.chat(
                model=self.model_name,
                messages=[
                    {"role": "user", "content": prompt}
                ],
                options={
                    "temperature": 0.7,
                    "top_p": 0.9,
                    "max_tokens": 1000
                }
            )
            
            return response['message']['content']
            
        except Exception as e:
            logger.error(f"Error generating response: {e}")
            return f"Désolé, j'ai rencontré une erreur lors de la génération de la réponse: {e}"
    
    async def process_query(self, user_query: str) -> Dict[str, Any]:
        """
        Process a user query through the RAG pipeline
        
        Args:
            user_query: User's question
            
        Returns:
            Dictionary with response and metadata
        """
        console.print(f"[cyan]🔍 Recherche dans la base de connaissances...[/cyan]")
        
        # Search knowledge base
        search_results = await self.search_knowledge_base(user_query, limit=5)
        
        if not search_results:
            return {
                "response": "Je n'ai pas trouvé d'informations pertinentes dans la base de connaissances pour répondre à votre question.",
                "sources": [],
                "search_results_count": 0
            }
        
        console.print(f"[green]✓ {len(search_results)} documents trouvés[/green]")
        
        # Format context
        context = self.format_search_results(search_results)
        
        console.print(f"[cyan]🤖 Génération de la réponse...[/cyan]")
        
        # Generate response
        response = await self.generate_response(user_query, context)
        
        # Extract sources
        sources = []
        for result in search_results:
            metadata = result.get('metadata', {})
            sources.append({
                "title": metadata.get('document_title', 'Document inconnu'),
                "source": metadata.get('document_source', ''),
                "similarity": result.get('similarity', 0)
            })
        
        return {
            "response": response,
            "sources": sources,
            "search_results_count": len(search_results)
        }
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get database statistics"""
        return await self.db.get_stats()
    
    def display_welcome(self):
        """Display welcome message"""
        welcome_text = """
# 🎓 StudyRAG - Assistant d'Étude Intelligent

Bienvenue dans votre assistant d'étude personnel ! Je peux répondre à vos questions en me basant sur les documents de votre base de connaissances.

## Commandes disponibles:
- **Posez une question** : Tapez simplement votre question
- **stats** : Afficher les statistiques de la base de données
- **help** : Afficher cette aide
- **quit** ou **exit** : Quitter le chat

## Comment ça marche:
1. Je recherche dans vos documents les informations pertinentes
2. J'utilise ces informations pour générer une réponse précise
3. Je cite mes sources pour que vous puissiez vérifier

Commencez par poser une question !
        """
        
        console.print(Panel(
            Markdown(welcome_text),
            title="🤖 StudyRAG Chat",
            border_style="blue"
        ))
    
    def display_response(self, result: Dict[str, Any]):
        """Display the response with sources"""
        # Main response
        console.print(Panel(
            Markdown(result["response"]),
            title="🤖 Réponse",
            border_style="green"
        ))
        
        # Sources
        if result["sources"]:
            sources_text = "## 📚 Sources consultées:\n\n"
            for i, source in enumerate(result["sources"], 1):
                sources_text += f"{i}. **{source['title']}** (pertinence: {source['similarity']:.2f})\n"
            
            console.print(Panel(
                Markdown(sources_text),
                title="Sources",
                border_style="dim"
            ))
    
    async def run_chat(self):
        """Run the interactive chat loop"""
        self.display_welcome()
        
        # Check database stats
        stats = await self.get_stats()
        console.print(f"[dim]📊 Base de données: {stats.get('total_chunks', 0)} chunks disponibles[/dim]")
        
        if stats.get('total_chunks', 0) == 0:
            console.print("[red]⚠️ Aucun document dans la base de données. Lancez d'abord l'ingestion avec:[/red]")
            console.print("[red]python ingest_simple.py[/red]")
            return
        
        console.print()
        
        while True:
            try:
                # Get user input
                user_input = Prompt.ask("[bold blue]Vous[/bold blue]").strip()
                
                if not user_input:
                    continue
                
                # Handle commands
                if user_input.lower() in ['quit', 'exit', 'q']:
                    console.print("[yellow]👋 Au revoir ! Bon apprentissage ![/yellow]")
                    break
                
                elif user_input.lower() == 'help':
                    self.display_welcome()
                    continue
                
                elif user_input.lower() == 'stats':
                    stats = await self.get_stats()
                    console.print(f"[cyan]📊 Statistiques:[/cyan]")
                    console.print(f"  • Total chunks: {stats.get('total_chunks', 0)}")
                    console.print(f"  • Collection: {stats.get('collection_name', 'N/A')}")
                    continue
                
                # Process the query
                console.print()
                result = await self.process_query(user_input)
                
                # Display response
                console.print()
                self.display_response(result)
                console.print()
                
            except KeyboardInterrupt:
                console.print("\n[yellow]👋 Au revoir ! Bon apprentissage ![/yellow]")
                break
            except Exception as e:
                console.print(f"[red]❌ Erreur: {e}[/red]")
                logger.error(f"Chat error: {e}")
    
    async def close(self):
        """Close connections"""
        await self.db.close()


async def main():
    """Main function"""
    # Setup logging
    logging.basicConfig(level=logging.INFO)
    
    # Create and run chat
    chat = StudyRAGChat()
    
    try:
        await chat.run_chat()
    finally:
        await chat.close()


if __name__ == "__main__":
    asyncio.run(main())